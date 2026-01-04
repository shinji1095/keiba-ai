from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import time
from pathlib import Path
from typing import Optional
import json

from scraper_service.config import Settings
from scraper_service.http.client import HttpClient
from scraper_service.keiba import constants as C
from scraper_service.keiba.models import RaceKey
from scraper_service.keiba.soft_errors import SOFT_NO_ODDS_PATTERNS, SOFT_TEMP_UNAVAILABLE_PATTERNS
from scraper_service.keiba.urls import ODDS_FLG_FIXED, build_url
from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.deba_table_normalized import parse_deba_table_normalized
from scraper_service.parsers.odds import (
    parse_generic_odds_table,
    parse_odds_tanfuku,
    parse_odds_waku,
)
from scraper_service.parsers.race_mark_table import parse_race_mark_table
from scraper_service.parsers.race_list import parse_race_list
from scraper_service.parsers.refund_money_list import parse_refund_money_list
from scraper_service.parsers.today_top import parse_today_race_info_top
from scraper_service.ingest.store import IngestStore
from scraper_service.utils.time import JST, combine_date_time_jst, iso_now_jst

SCHEDULED_ODDS_WINDOWS = [
    ("t_minus_60m", 60, 2),
    ("t_minus_30m", 30, 2),
    ("t_minus_20m", 20, 2),
    ("t_minus_10m", 10, 1),
    ("t_minus_5m", 5, 1),
]

MANUAL_ODDS_TARGETS = [
    ("t_minus_60m", 60),
    ("t_minus_30m", 30),
    ("t_minus_20m", 20),
    ("t_minus_10m", 10),
    ("t_minus_5m", 5),
    ("t_minus_1m", 1),
]

DEFAULT_SCHEDULED_SNAPSHOT_KINDS = ["final"]
SCHEDULED_SNAPSHOT_KIND_TO_OFFSET_MIN: dict[str, int] = {
    "t_minus_60m": 60,
    "t_minus_30m": 30,
    "t_minus_20m": 20,
    "t_minus_10m": 10,
    "t_minus_5m": 5,
    "t_minus_1m": 1,
    "final": 0,
}
SCHEDULED_SNAPSHOT_KIND_WINDOWS_MIN: dict[str, int] = {
    "t_minus_60m": 2,
    "t_minus_30m": 2,
    "t_minus_20m": 2,
    "t_minus_10m": 1,
    "t_minus_5m": 1,
    # t_minus_1m / final are handled with a seconds window to avoid overlap.
}


def _normalize_snapshot_kinds(kinds: Optional[list[str]]) -> list[str]:
    if not kinds:
        return DEFAULT_SCHEDULED_SNAPSHOT_KINDS.copy()
    out: list[str] = []
    seen: set[str] = set()
    for k in kinds:
        kk = str(k).strip()
        if not kk or kk in seen:
            continue
        if kk not in SCHEDULED_SNAPSHOT_KIND_TO_OFFSET_MIN:
            continue
        out.append(kk)
        seen.add(kk)
    return out or DEFAULT_SCHEDULED_SNAPSHOT_KINDS.copy()


def _scheduled_due_kinds(
    *,
    start_dt: Optional[datetime],
    now: datetime,
    snapshot_kinds: list[str],
) -> list[tuple[str, bool]]:
    """Return due snapshot kinds for scheduled mode.

    The scheduler is typically invoked periodically (e.g. cron). We treat a kind
    as due if current time is within a small window around (start_time - offset).
    """
    if start_dt is None:
        return []
    delta_sec = (start_dt - now).total_seconds()
    if delta_sec < 0:
        return []

    due: list[tuple[str, bool]] = []
    for kind in snapshot_kinds:
        if kind == "final":
            if 0 <= delta_sec <= 60:
                due.append(("final", True))
            continue
        if kind == "t_minus_1m":
            # Avoid overlap with "final".
            if 60 <= delta_sec <= 120:
                due.append(("t_minus_1m", False))
            continue

        offset_min = SCHEDULED_SNAPSHOT_KIND_TO_OFFSET_MIN.get(kind)
        if offset_min is None:
            continue
        window_min = SCHEDULED_SNAPSHOT_KIND_WINDOWS_MIN.get(kind, 1)
        delta_min = delta_sec / 60.0
        if abs(delta_min - offset_min) <= window_min:
            due.append((kind, False))

    return due


def _prefetch_state_path(settings: Settings) -> Path:
    return settings.control_dir / "prefetch_state.json"


def _load_last_prefetch_date(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        v = data.get("last_prefetch_race_date")
        return str(v) if v else None
    except Exception:
        return None


def _save_last_prefetch_date(path: Path, race_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_prefetch_race_date": race_date, "updated_at": iso_now_jst()}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _iter_future_dates(base: str, days: int) -> list[str]:
    y, m, d = [int(x) for x in base.split("-")]
    start = date(y, m, d)
    return [(start + timedelta(days=i)).isoformat() for i in range(1, days + 1)]


def _build_daily_odds_plan(
    *,
    race_date: str,
    races: list[object],
    snapshot_kinds: list[str],
) -> list[dict[str, object]]:
    """Build a simple odds plan from RaceList results.

    This plan is primarily for observability/debugging (what should be scraped when).
    """

    tasks: list[dict[str, object]] = []
    for r in races:
        # RaceUpsert has: race_key + start_time
        rk = getattr(r, "race_key", None)
        start_time = getattr(r, "start_time", None)
        start_dt = _race_start_dt(race_date, start_time)
        if rk is None or start_dt is None:
            continue
        for kind in snapshot_kinds:
            offset_min = SCHEDULED_SNAPSHOT_KIND_TO_OFFSET_MIN.get(kind)
            if offset_min is None:
                continue
            scheduled_at = start_dt - timedelta(minutes=offset_min)
            tasks.append(
                {
                    "race_key": {
                        "race_date": rk.race_date,
                        "baba_code": rk.baba_code,
                        "race_no": rk.race_no,
                    },
                    "start_time": start_time,
                    "snapshot_kind": kind,
                    "scheduled_at": scheduled_at.isoformat(timespec="seconds"),
                }
            )
    tasks.sort(key=lambda x: (x["scheduled_at"], x["race_key"]["baba_code"], x["race_key"]["race_no"]))  # type: ignore[index]
    return tasks


def _save_dir_for(
    settings: Settings,
    *,
    race_date: str,
    baba_code: int | None,
    race_no: int | None,
    device: str,
    page_name: str,
) -> Path:
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


def _race_start_dt(race_date: str, start_time: Optional[str]) -> Optional[datetime]:
    if not start_time:
        return None
    try:
        return combine_date_time_jst(race_date, start_time)
    except ValueError:
        return None


def _select_manual_snapshot_kind(
    *, start_dt: Optional[datetime], now: datetime
) -> tuple[str, bool]:
    if start_dt is None:
        return ("manual", False)
    if now >= start_dt:
        return ("final", True)

    delta_min = (start_dt - now).total_seconds() / 60.0
    nearest = min(
        MANUAL_ODDS_TARGETS,
        key=lambda x: abs(delta_min - x[1]),
    )
    return (nearest[0], False)


def _scheduled_snapshot_kind(
    *, start_dt: Optional[datetime], now: datetime
) -> Optional[tuple[str, bool]]:
    if start_dt is None:
        return None
    delta_sec = (start_dt - now).total_seconds()
    if delta_sec < 0:
        return None
    if delta_sec <= 60:
        return ("final", True)
    if 60 <= delta_sec <= 120:
        return ("t_minus_1m", False)

    delta_min = delta_sec / 60.0
    for kind, target, window in SCHEDULED_ODDS_WINDOWS:
        if abs(delta_min - target) <= window:
            return (kind, False)
    return None


def _should_fetch_deba(*, start_dt: Optional[datetime], now: datetime) -> bool:
    if start_dt is None:
        return False
    delta_min = (start_dt - now).total_seconds() / 60.0
    return 20 <= delta_min <= 60 or 8 <= delta_min <= 12


def _should_fetch_race_mark(*, start_dt: Optional[datetime], now: datetime) -> bool:
    if start_dt is None:
        return False
    delta_min = (now - start_dt).total_seconds() / 60.0
    return 10 <= delta_min <= 60


def _should_fetch_refund(
    *, last_start_dt: Optional[datetime], now: datetime
) -> bool:
    if last_start_dt is None:
        return False
    delta_min = (now - last_start_dt).total_seconds() / 60.0
    return delta_min >= 90


@dataclass
class ScrapeRunner:
    settings: Settings
    http: HttpClient
    sync_store: Optional[IngestStore] = None
    # in-memory state (not persisted)
    _recent_url_ts: dict[str, datetime] = field(default_factory=dict, init=False)

    def _fetch(
        self,
        page_name: str,
        *,
        race_date: str,
        baba_code: int | None,
        race_no: int | None,
        odds_flg: int | None,
    ) -> tuple[bytes, str, str]:
        rk = None
        if baba_code is not None and race_no is not None:
            rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)

        url = build_url(
            page_name,
            device=self.settings.keiba_device,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=odds_flg,
        )
        cooldown_sec = self.settings.same_url_cooldown_sec
        if cooldown_sec > 0:
            last_ts = self._recent_url_ts.get(url)
            if last_ts is not None:
                elapsed = (datetime.now(JST) - last_ts).total_seconds()
                if elapsed < cooldown_sec:
                    time.sleep(cooldown_sec - elapsed)
        save_dir = _save_dir_for(
            self.settings,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            device=self.settings.keiba_device,
            page_name=page_name,
        )
        res = self.http.get_html(url, page_type=page_name, save_dir=save_dir)
        # Record the timestamp for URL cooldown control.
        self._recent_url_ts[url] = datetime.now(JST)

        body_text = res.content.decode("utf-8", errors="ignore")
        note = _detect_note(body_text)
        return res.content, res.final_url, note

    def _append_sync(self, kind: str, payloads: list[dict[str, object]]) -> None:
        if not self.sync_store or not payloads:
            return
        self.sync_store.append(kind=kind, payloads=payloads)

    def run_once(
        self,
        *,
        race_date: str,
        baba_codes: Optional[list[int]] = None,
        race_no: Optional[int] = None,
    ) -> None:
        now = datetime.now(JST)
        if race_no is not None and not baba_codes:
            raise RuntimeError("race_no requires baba_code")

        if baba_codes is None:
            html, _, _ = self._fetch(
                C.PAGE_TODAY_TOP,
                race_date=race_date,
                baba_code=None,
                race_no=None,
                odds_flg=None,
            )
            baba_codes = parse_today_race_info_top(html)
        if not baba_codes:
            raise RuntimeError("failed to determine baba_codes; specify --baba-code")
        if race_no is not None and len(baba_codes) != 1:
            raise RuntimeError("race_no requires a single baba_code")

        # for each venue
        for baba_code in baba_codes:
            # RaceList
            html, _, _ = self._fetch(
                C.PAGE_RACE_LIST,
                race_date=race_date,
                baba_code=baba_code,
                race_no=None,
                odds_flg=None,
            )
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)
            self._append_sync(
                "races", [r.model_dump(mode="json") for r in races]
            )

            if race_no is not None:
                races = [r for r in races if r.race_key.race_no == race_no]
                if not races:
                    raise RuntimeError("race_no not found in RaceList")

            last_start_dt = None
            # per race: entries and odds
            for r in races:
                rn = r.race_key.race_no
                start_dt = _race_start_dt(race_date, r.start_time)
                if start_dt and (last_start_dt is None or start_dt > last_start_dt):
                    last_start_dt = start_dt
                html_deba, final_url, _ = self._fetch(
                    C.PAGE_DEBA_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=rn,
                    odds_flg=None,
                )
                entries = parse_deba_table(
                    html_deba,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=rn,
                )
                self._append_sync(
                    "race_entries",
                    [e.model_dump(mode="json") for e in entries],
                )
                card = parse_deba_table_normalized(
                    html_deba,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=rn,
                )
                card_payload = card.model_dump(mode="json")
                card_payload["captured_at"] = iso_now_jst()
                card_payload["source_url"] = final_url
                self._append_sync("race_cards", [card_payload])

                snapshot_kind, is_final = _select_manual_snapshot_kind(
                    start_dt=start_dt, now=now
                )
                self._scrape_odds_for_race(
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=rn,
                    snapshot_kind=snapshot_kind,
                    is_final=is_final,
                )

                # NOTE (manual scrape):
                # - The scheduler window (10..60 min after post time) is useful for live operation,
                #   but for manual scrapes of past races it causes permanent "results missing".
                # - For run_once, fetch RaceMarkTable whenever it's plausibly available:
                #   10 minutes after post time with NO upper bound.
                should_fetch_race_mark_manual = False
                if start_dt is not None:
                    delta_min = (now - start_dt).total_seconds() / 60.0
                    should_fetch_race_mark_manual = delta_min >= 10

                if should_fetch_race_mark_manual:
                    html_result, _, _ = self._fetch(
                        C.PAGE_RACE_MARK_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    results = parse_race_mark_table(
                        html_result,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )
                    self._append_sync(
                        "race_results",
                        [r.model_dump(mode="json") for r in results],
                    )

            # payouts (RefundMoneyList)
            # NOTE:
            # - Previously, run_once with race_no specified never fetched payouts.
            # - For manual scrapes, fetching payouts for the venue/day is cheap and makes the UI complete.
            if _should_fetch_refund(last_start_dt=last_start_dt, now=now):
                html_refund, _, _ = self._fetch(
                    C.PAGE_REFUND_MONEY_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                    odds_flg=None,
                )
                payouts = parse_refund_money_list(
                    html_refund,
                    race_date=race_date,
                    baba_code=baba_code,
                )
                self._append_sync(
                    "payouts",
                    [p.model_dump(mode="json") for p in payouts],
                )

    def run_scheduled(
        self,
        *,
        race_date: str,
        baba_codes: Optional[list[int]] = None,
        race_no: Optional[int] = None,
        snapshot_kinds: Optional[list[str]] = None,
        prefetch_days: int = 7,
    ) -> None:
        now = datetime.now(JST)
        scheduled_kinds = _normalize_snapshot_kinds(snapshot_kinds)
        if race_no is not None and not baba_codes:
            raise RuntimeError("race_no requires baba_code")

        if baba_codes is None:
            html, _, _ = self._fetch(
                C.PAGE_TODAY_TOP,
                race_date=race_date,
                baba_code=None,
                race_no=None,
                odds_flg=None,
            )
            baba_codes = parse_today_race_info_top(html)
        if not baba_codes:
            raise RuntimeError("failed to determine baba_codes; specify --baba-code")
        if race_no is not None and len(baba_codes) != 1:
            raise RuntimeError("race_no requires a single baba_code")

        # Prefetch future RaceList once per day (best-effort).
        if prefetch_days > 0 and race_no is None:
            state_path = _prefetch_state_path(self.settings)
            last_prefetched = _load_last_prefetch_date(state_path)
            if last_prefetched != race_date:
                for d in _iter_future_dates(race_date, prefetch_days):
                    for baba_code in baba_codes:
                        html, _, _ = self._fetch(
                            C.PAGE_RACE_LIST,
                            race_date=d,
                            baba_code=baba_code,
                            race_no=None,
                            odds_flg=None,
                        )
                        races_f = parse_race_list(
                            html, race_date=d, baba_code=baba_code
                        )
                        self._append_sync(
                            "races", [r.model_dump(mode="json") for r in races_f]
                        )
                _save_last_prefetch_date(state_path, race_date)

        daily_races_for_plan: list[object] = []
        for baba_code in baba_codes:
            html, _, _ = self._fetch(
                C.PAGE_RACE_LIST,
                race_date=race_date,
                baba_code=baba_code,
                race_no=None,
                odds_flg=None,
            )
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)
            self._append_sync(
                "races", [r.model_dump(mode="json") for r in races]
            )
            daily_races_for_plan.extend(races)

            if race_no is not None:
                races = [r for r in races if r.race_key.race_no == race_no]
                if not races:
                    raise RuntimeError("race_no not found in RaceList")

            last_start_dt = None
            for r in races:
                rn = r.race_key.race_no
                start_dt = _race_start_dt(race_date, r.start_time)
                if start_dt and (last_start_dt is None or start_dt > last_start_dt):
                    last_start_dt = start_dt

                if _should_fetch_deba(start_dt=start_dt, now=now):
                    html_deba, final_url, _ = self._fetch(
                        C.PAGE_DEBA_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    entries = parse_deba_table(
                        html_deba,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )
                    self._append_sync(
                        "race_entries",
                        [e.model_dump(mode="json") for e in entries],
                    )
                    card = parse_deba_table_normalized(
                        html_deba,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )
                    card_payload = card.model_dump(mode="json")
                    card_payload["captured_at"] = iso_now_jst()
                    card_payload["source_url"] = final_url
                    self._append_sync("race_cards", [card_payload])

                for snapshot_kind, is_final in _scheduled_due_kinds(
                    start_dt=start_dt, now=now, snapshot_kinds=scheduled_kinds
                ):
                    self._scrape_odds_for_race(
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        snapshot_kind=snapshot_kind,
                        is_final=is_final,
                    )

                if _should_fetch_race_mark(start_dt=start_dt, now=now):
                    html_result, _, _ = self._fetch(
                        C.PAGE_RACE_MARK_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    results = parse_race_mark_table(
                        html_result,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )
                    self._append_sync(
                        "race_results",
                        [r.model_dump(mode="json") for r in results],
                    )

            if race_no is None:
                if _should_fetch_refund(last_start_dt=last_start_dt, now=now):
                    html_refund, _, _ = self._fetch(
                        C.PAGE_REFUND_MONEY_LIST,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=None,
                        odds_flg=None,
                    )
                    payouts = parse_refund_money_list(
                        html_refund,
                        race_date=race_date,
                        baba_code=baba_code,
                    )
                    self._append_sync(
                        "payouts",
                        [p.model_dump(mode="json") for p in payouts],
                    )

        # Save daily plan (for observability/debugging).
        if race_no is None:
            plan_path = self.settings.control_dir / f"odds_plan_{race_date}.json"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan = {
                "race_date": race_date,
                "snapshot_kinds": scheduled_kinds,
                "generated_at": iso_now_jst(),
                "items": _build_daily_odds_plan(
                    race_date=race_date,
                    races=daily_races_for_plan,
                    snapshot_kinds=scheduled_kinds,
                ),
            }
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=True, indent=2), encoding="utf-8"
            )

    def _scrape_odds_for_race(
        self,
        *,
        race_date: str,
        baba_code: int,
        race_no: int,
        snapshot_kind: str,
        is_final: bool,
    ) -> None:
        captured_at = iso_now_jst()

        def post_snapshot(source_url: str, bet_type: str, odds_flg: int | None, items):
            if not items:
                return
            payload = {
                "race_key": {
                    "race_date": race_date,
                    "baba_code": baba_code,
                    "race_no": race_no,
                },
                "bet_type": bet_type,
                "snapshot_kind": snapshot_kind,
                "captured_at": captured_at,
                "source_url": source_url,
                "odds_flg": odds_flg,
                "is_final": is_final,
                "items": [it.model_dump(mode="json") for it in items],
            }
            self._append_sync("odds_snapshots", [payload])

        # OddsTanFuku (two modes)
        for flg in ODDS_FLG_FIXED.get(C.PAGE_ODDS_TANFUKU, [None]):
            html, final_url, note = self._fetch(
                C.PAGE_ODDS_TANFUKU,
                race_date=race_date,
                baba_code=baba_code,
                race_no=race_no,
                odds_flg=flg,
            )
            if note == "soft_no_odds":
                continue
            parsed = parse_odds_tanfuku(html)
            post_snapshot(final_url, "tansho", flg, parsed.get("tansho", []))
            post_snapshot(final_url, "fukusho", flg, parsed.get("fukusho", []))

        # OddsWakuLenFukuTan (two modes)
        for flg in ODDS_FLG_FIXED.get(C.PAGE_ODDS_WAKU, [None]):
            html, final_url, note = self._fetch(
                C.PAGE_ODDS_WAKU,
                race_date=race_date,
                baba_code=baba_code,
                race_no=race_no,
                odds_flg=flg,
            )
            if note == "soft_no_odds":
                continue
            parsed = parse_odds_waku(html)
            post_snapshot(final_url, "wakuren", flg, parsed.get("wakuren", []))
            post_snapshot(final_url, "wakutan", flg, parsed.get("wakutan", []))

        # Umaren (OddsUmLenFuku)
        html, final_url, note = self._fetch(
            C.PAGE_ODDS_UMAREN,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="umaren")
            post_snapshot(final_url, "umaren", None, items)

        # Umatan (OddsUmLenTan)
        html, final_url, note = self._fetch(
            C.PAGE_ODDS_UMATAN,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="umatan")
            post_snapshot(final_url, "umatan", None, items)

        # Wide
        html, final_url, note = self._fetch(
            C.PAGE_ODDS_WIDE,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="wide")
            post_snapshot(final_url, "wide", None, items)

        # Sanrenpuku
        html, final_url, note = self._fetch(
            C.PAGE_ODDS_3LENFUKU,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="sanrenpuku")
            post_snapshot(final_url, "sanrenpuku", None, items)

        # Sanrentan
        html, final_url, note = self._fetch(
            C.PAGE_ODDS_3LENTAN,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="sanrentan")
            post_snapshot(final_url, "sanrentan", None, items)
