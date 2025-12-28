from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from scraper_service.api.client import ApiClient
from scraper_service.config import Settings
from scraper_service.http.client import HttpClient
from scraper_service.keiba import constants as C
from scraper_service.keiba.models import OddsSnapshotUpsertRequest, RaceKey
from scraper_service.keiba.soft_errors import SOFT_NO_ODDS_PATTERNS, SOFT_TEMP_UNAVAILABLE_PATTERNS
from scraper_service.keiba.urls import ODDS_FLG_FIXED, build_url
from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.odds import (
    parse_generic_odds_table,
    parse_odds_tanfuku,
    parse_odds_waku,
)
from scraper_service.parsers.race_list import parse_race_list
from scraper_service.parsers.race_mark_table import parse_race_mark_table
from scraper_service.parsers.refund_money_list import parse_refund_money_list
from scraper_service.parsers.today_top import parse_today_race_info_top
from scraper_service.scheduler.plan import Plan, Task
from scraper_service.utils.raw_fetch_logger import RawFetchLogger
from scraper_service.utils.time import JST, combine_date_time_jst, iso_now_jst, parse_iso, to_iso

from datetime import datetime, timedelta
import time


def _save_dir_for(settings: Settings, *, race_date: str, baba_code: int | None, race_no: int | None, device: str, page_name: str) -> Path:
    """Return the directory for storing raw HTML.

    The project requirement uses a date-based partition:
      raw_html/YYYY/MM/DD/{page_type}/{sha256}.html

    We keep the directory layout aligned with that contract.
    """

    y, m, d = race_date.split("-")
    return settings.raw_html_dir / f"{int(y):04d}" / f"{int(m):02d}" / f"{int(d):02d}" / page_name


def _detect_note(body_text: str) -> str:
    if any(p in body_text for p in SOFT_NO_ODDS_PATTERNS):
        return "soft_no_odds"
    if any(p in body_text for p in SOFT_TEMP_UNAVAILABLE_PATTERNS):
        return "soft_temp_unavailable"
    return ""


@dataclass
class ScrapeRunner:
    settings: Settings
    http: HttpClient
    api: Optional[ApiClient]
    raw_logger: RawFetchLogger

    # in-memory state (not persisted)
    _recent_url_ts: dict[str, datetime] = field(default_factory=dict, init=False)

    def _fetch(self, page_name: str, *, race_date: str, baba_code: int | None, race_no: int | None, odds_flg: int | None) -> tuple[bytes, str, str, list]:
        rk = None
        if baba_code is not None and race_no is not None:
            rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)

        url = build_url(page_name, device=self.settings.keiba_device, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=odds_flg)
        save_dir = _save_dir_for(self.settings, race_date=race_date, baba_code=baba_code, race_no=race_no, device=self.settings.keiba_device, page_name=page_name)
        res = self.http.get_html(url, page_type=page_name, save_dir=save_dir)
        # Record the timestamp for URL cooldown control.
        self._recent_url_ts[url] = datetime.now(JST)

        body_text = res.content.decode("utf-8", errors="ignore")
        note = _detect_note(body_text)
        log_item = self.raw_logger.record(res, race_key=rk, note=note)
        if self.api is not None:
            # push one-by-one is OK (small). batch would be better but keep simple.
            self.api.post_raw_fetch_logs([log_item])

        return res.content, res.final_url, note, [log_item]

    def run_once(self, *, race_date: str, baba_codes: Optional[list[int]] = None) -> None:
        if baba_codes is None:
            html, _, _, _ = self._fetch(C.PAGE_TODAY_TOP, race_date=race_date, baba_code=None, race_no=None, odds_flg=None)
            baba_codes = parse_today_race_info_top(html)
        if not baba_codes:
            raise RuntimeError("failed to determine baba_codes; specify --baba-code")

        # for each venue
        for baba_code in baba_codes:
            # RaceList
            html, _, _, _ = self._fetch(C.PAGE_RACE_LIST, race_date=race_date, baba_code=baba_code, race_no=None, odds_flg=None)
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)
            if self.api is not None:
                self.api.post_races(races)

            # per race: entries and odds
            for r in races:
                rn = r.race_key.race_no
                html_deba, _, _, _ = self._fetch(C.PAGE_DEBA_TABLE, race_date=race_date, baba_code=baba_code, race_no=rn, odds_flg=None)
                entries = parse_deba_table(html_deba, race_date=race_date, baba_code=baba_code, race_no=rn)
                if self.api is not None:
                    self.api.post_race_entries(entries)

                self._scrape_odds_for_race(race_date=race_date, baba_code=baba_code, race_no=rn, snapshot_kind="manual", is_final=False)

            # payouts (for venues with completed races)
            html_refund, _, _, _ = self._fetch(C.PAGE_REFUND_MONEY_LIST, race_date=race_date, baba_code=baba_code, race_no=None, odds_flg=None)
            payouts = parse_refund_money_list(html_refund, race_date=race_date, baba_code=baba_code)
            if self.api is not None:
                self.api.post_payouts(payouts)

    def _scrape_odds_for_race(self, *, race_date: str, baba_code: int, race_no: int, snapshot_kind: str, is_final: bool) -> None:
        captured_at = iso_now_jst()

        def post_snapshot(source_url: str, bet_type: str, odds_flg: int | None, items):
            if self.api is None:
                return
            req = OddsSnapshotUpsertRequest(
                race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no),
                bet_type=bet_type,  # type: ignore[arg-type]
                snapshot_kind=snapshot_kind,  # type: ignore[arg-type]
                captured_at=captured_at,
                source_url=source_url,
                odds_flg=odds_flg,
                is_final=is_final,
                items=items,
            )
            self.api.post_odds_snapshot(req)

        # OddsTanFuku (two modes)
        for flg in ODDS_FLG_FIXED.get(C.PAGE_ODDS_TANFUKU, [None]):
            html, final_url, note, _ = self._fetch(C.PAGE_ODDS_TANFUKU, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=flg)
            if note == "soft_no_odds":
                continue
            parsed = parse_odds_tanfuku(html)
            post_snapshot(final_url, "tansho", flg, parsed.get("tansho", []))
            post_snapshot(final_url, "fukusho", flg, parsed.get("fukusho", []))

        # OddsWakuLenFukuTan (two modes)
        for flg in ODDS_FLG_FIXED.get(C.PAGE_ODDS_WAKU, [None]):
            html, final_url, note, _ = self._fetch(C.PAGE_ODDS_WAKU, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=flg)
            if note == "soft_no_odds":
                continue
            parsed = parse_odds_waku(html)
            post_snapshot(final_url, "wakuren", flg, parsed.get("wakuren", []))
            post_snapshot(final_url, "wakutan", flg, parsed.get("wakutan", []))

        # Umaren (OddsUmLenFuku)
        html, final_url, note, _ = self._fetch(C.PAGE_ODDS_UMAREN, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=None)
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="umaren")
            post_snapshot(final_url, "umaren", None, items)

        # Umatan (OddsUmLenTan)
        html, final_url, note, _ = self._fetch(C.PAGE_ODDS_UMATAN, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=None)
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="umatan")
            post_snapshot(final_url, "umatan", None, items)

        # Wide
        html, final_url, note, _ = self._fetch(C.PAGE_ODDS_WIDE, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=None)
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="wide")
            post_snapshot(final_url, "wide", None, items)

        # Sanrenpuku
        html, final_url, note, _ = self._fetch(C.PAGE_ODDS_3LENFUKU, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=None)
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="sanrenpuku")
            post_snapshot(final_url, "sanrenpuku", None, items)

        # Sanrentan
        html, final_url, note, _ = self._fetch(C.PAGE_ODDS_3LENTAN, race_date=race_date, baba_code=baba_code, race_no=race_no, odds_flg=None)
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="sanrentan")
            post_snapshot(final_url, "sanrentan", None, items)

    def build_plan(self, *, race_date: str, baba_codes: Optional[list[int]] = None) -> Plan:
        if baba_codes is None:
            html, _, _, _ = self._fetch(C.PAGE_TODAY_TOP, race_date=race_date, baba_code=None, race_no=None, odds_flg=None)
            baba_codes = parse_today_race_info_top(html)

        if not baba_codes:
            raise RuntimeError("failed to determine baba_codes; specify --baba-code")

        tasks: list[Task] = []

        for baba_code in baba_codes:
            html, _, _, _ = self._fetch(C.PAGE_RACE_LIST, race_date=race_date, baba_code=baba_code, race_no=None, odds_flg=None)
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)
            if self.api is not None:
                self.api.post_races(races)

            # RefundMoneyList is venue-level and high-efficiency. Schedule minimal fetches.
            # NOTE: we currently approximate "last race" as the max(start_time) among RaceList.
            last_start: Optional[datetime] = None

            for r in races:
                if not r.start_time:
                    continue
                st = combine_date_time_jst(race_date, r.start_time)
                rk = r.race_key

                if last_start is None or st > last_start:
                    last_start = st

                def add(task_type: str, due: datetime, **kwargs):
                    task_id = f"{task_type}:{rk.baba_code}:{rk.race_no}:{to_iso(due)}:{kwargs.get('page_name','')}{kwargs.get('bet_type','')}"
                    tasks.append(Task(task_id=task_id, task_type=task_type, due_at=to_iso(due), race_key=rk, **kwargs))

                add("fetch_deba_table", st - timedelta(minutes=60))
                add("fetch_odds", st - timedelta(minutes=5), snapshot_kind="t_minus_5m", is_final=False)
                add("fetch_odds", st - timedelta(minutes=1), snapshot_kind="t_minus_1m", is_final=False)
                add("fetch_odds", st + timedelta(minutes=1), snapshot_kind="final", is_final=True)
                # RaceMarkTable: fixed delay + small number of retries (requirements recommend 2-4 retries).
                add("fetch_race_mark_table", st + timedelta(minutes=20))
                add("fetch_race_mark_table", st + timedelta(minutes=25))
                add("fetch_race_mark_table", st + timedelta(minutes=30))

            # RefundMoneyList: schedule once per venue after the last race (plus retries).
            # If last_start is unknown (missing start_time), we fall back to a conservative time.
            base = last_start or combine_date_time_jst(race_date, "23:59:59")
            due0 = base + timedelta(minutes=90)
            for i, delta_min in enumerate([0, 10, 20]):
                task_id = f"fetch_refund_money_list:{baba_code}:{to_iso(due0 + timedelta(minutes=delta_min))}:try{i+1}"
                tasks.append(
                    Task(
                        task_id=task_id,
                        task_type="fetch_refund_money_list",
                        due_at=to_iso(due0 + timedelta(minutes=delta_min)),
                        race_date=race_date,
                        baba_code=baba_code,
                    )
                )

        created = iso_now_jst()
        return Plan(race_date=race_date, baba_codes=baba_codes, tasks=tasks, created_at=created, updated_at=created)

    def run_daemon(self, *, race_date: str, baba_codes: Optional[list[int]] = None, plan_path: Path = Path("./data/plan.json")) -> None:
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        if plan_path.exists():
            plan = Plan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        else:
            plan = self.build_plan(race_date=race_date, baba_codes=baba_codes)
            plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

        def scope_key(t: Task) -> tuple:
            if t.race_key is not None:
                rk = t.race_key
                return ("race", rk.race_date, rk.baba_code, rk.race_no)
            if t.race_date is not None and t.baba_code is not None:
                return ("venue", t.race_date, t.baba_code)
            return ("unknown",)

        def dedupe_key(t: Task) -> tuple:
            # fetch_odds tasks are keyed by snapshot kind, otherwise retries would be squashed.
            if t.task_type == "fetch_odds":
                return (t.task_type, scope_key(t), t.snapshot_kind or "", bool(t.is_final), t.odds_flg)
            return (t.task_type, scope_key(t))

        def single_url_if_applicable(t: Task) -> Optional[str]:
            # Only for tasks that map to a single URL.
            if t.task_type == "fetch_deba_table" and t.race_key is not None:
                rk = t.race_key
                return build_url(C.PAGE_DEBA_TABLE, device=self.settings.keiba_device, race_date=rk.race_date, baba_code=rk.baba_code, race_no=rk.race_no, odds_flg=None)
            if t.task_type == "fetch_race_mark_table" and t.race_key is not None:
                rk = t.race_key
                return build_url(C.PAGE_RACE_MARK_TABLE, device=self.settings.keiba_device, race_date=rk.race_date, baba_code=rk.baba_code, race_no=rk.race_no, odds_flg=None)
            if t.task_type == "fetch_refund_money_list":
                rd = t.race_key.race_date if t.race_key is not None else t.race_date
                bc = t.race_key.baba_code if t.race_key is not None else t.baba_code
                if rd is None or bc is None:
                    return None
                return build_url(C.PAGE_REFUND_MONEY_LIST, device=self.settings.keiba_device, race_date=rd, baba_code=bc, race_no=None, odds_flg=None)
            if t.task_type == "fetch_race_list":
                rd = t.race_key.race_date if t.race_key is not None else t.race_date
                bc = t.race_key.baba_code if t.race_key is not None else t.baba_code
                if rd is None or bc is None:
                    return None
                return build_url(C.PAGE_RACE_LIST, device=self.settings.keiba_device, race_date=rd, baba_code=bc, race_no=None, odds_flg=None)
            return None

        while True:
            now = datetime.now(JST)
            changed = False
            ok_keys = {dedupe_key(x) for x in plan.tasks if x.status == "ok"}

            for t in plan.tasks:
                if t.done_at is not None:
                    continue
                due = parse_iso(t.due_at)
                if now < due:
                    continue

                # Retry suppression: if an earlier attempt succeeded, skip the remaining attempts.
                if dedupe_key(t) in ok_keys:
                    t.status = "skipped"
                    t.note = "skipped: already succeeded"
                    t.done_at = iso_now_jst()
                    changed = True
                    plan.updated_at = iso_now_jst()
                    plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
                    continue

                # Same-URL cooldown: defer this task until the URL is outside the cooldown window.
                url = single_url_if_applicable(t)
                if url is not None:
                    last = self._recent_url_ts.get(url)
                    if last is not None:
                        if (now - last).total_seconds() < float(self.settings.same_url_cooldown_sec):
                            continue

                try:
                    self._execute_task(t)
                    t.status = "ok"
                    t.done_at = iso_now_jst()
                    ok_keys.add(dedupe_key(t))
                except Exception as e:
                    # mark as done with error to avoid infinite loops; change later if needed
                    t.status = "error"
                    t.note = str(e)
                    t.done_at = iso_now_jst()

                changed = True
                plan.updated_at = iso_now_jst()
                plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

            if changed:
                plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

            time.sleep(self.settings.tick_sec)

    def _execute_task(self, t: Task) -> None:
        if t.task_type == "fetch_deba_table":
            assert t.race_key is not None
            html, _, _, _ = self._fetch(C.PAGE_DEBA_TABLE, race_date=t.race_key.race_date, baba_code=t.race_key.baba_code, race_no=t.race_key.race_no, odds_flg=None)
            entries = parse_deba_table(html, race_date=t.race_key.race_date, baba_code=t.race_key.baba_code, race_no=t.race_key.race_no)
            if self.api is not None:
                self.api.post_race_entries(entries)
            return

        if t.task_type == "fetch_odds":
            assert t.race_key is not None
            sk = t.snapshot_kind or "manual"
            self._scrape_odds_for_race(
                race_date=t.race_key.race_date,
                baba_code=t.race_key.baba_code,
                race_no=t.race_key.race_no,
                snapshot_kind=sk,
                is_final=t.is_final,
            )
            return

        if t.task_type == "fetch_race_mark_table":
            assert t.race_key is not None
            html, _, _, _ = self._fetch(C.PAGE_RACE_MARK_TABLE, race_date=t.race_key.race_date, baba_code=t.race_key.baba_code, race_no=t.race_key.race_no, odds_flg=None)
            results = parse_race_mark_table(html, race_date=t.race_key.race_date, baba_code=t.race_key.baba_code, race_no=t.race_key.race_no)
            if self.api is not None:
                self.api.post_race_results(results)
            return

        if t.task_type == "fetch_refund_money_list":
            race_date = t.race_key.race_date if t.race_key is not None else t.race_date
            baba_code = t.race_key.baba_code if t.race_key is not None else t.baba_code
            assert race_date is not None and baba_code is not None
            html, _, _, _ = self._fetch(C.PAGE_REFUND_MONEY_LIST, race_date=race_date, baba_code=baba_code, race_no=None, odds_flg=None)
            payouts = parse_refund_money_list(html, race_date=race_date, baba_code=baba_code)
            if self.api is not None:
                self.api.post_payouts(payouts)
            return

        if t.task_type == "fetch_race_list":
            race_date = t.race_key.race_date if t.race_key is not None else t.race_date
            baba_code = t.race_key.baba_code if t.race_key is not None else t.baba_code
            assert race_date is not None and baba_code is not None
            html, _, _, _ = self._fetch(C.PAGE_RACE_LIST, race_date=race_date, baba_code=baba_code, race_no=None, odds_flg=None)
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)
            if self.api is not None:
                self.api.post_races(races)
            return

        raise RuntimeError(f"unknown task_type: {t.task_type}")
