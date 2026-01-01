from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import time
from pathlib import Path
from typing import Optional

from scraper_service.config import Settings
from scraper_service.http.client import HttpClient
from scraper_service.keiba import constants as C
from scraper_service.keiba.models import RaceKey
from scraper_service.keiba.soft_errors import SOFT_NO_ODDS_PATTERNS, SOFT_TEMP_UNAVAILABLE_PATTERNS
from scraper_service.keiba.urls import ODDS_FLG_FIXED, build_url
from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.odds import (
    parse_generic_odds_table,
    parse_odds_tanfuku,
    parse_odds_waku,
)
from scraper_service.parsers.race_mark_table import parse_race_mark_table
from scraper_service.parsers.race_list import parse_race_list
from scraper_service.parsers.refund_money_list import parse_refund_money_list
from scraper_service.parsers.today_top import parse_today_race_info_top
from scraper_service.utils.raw_fetch_logger import RawFetchLogger
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
    raw_logger: RawFetchLogger

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
    ) -> tuple[bytes, str, str, list]:
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
        log_item = self.raw_logger.record(
            res,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            note=note,
        )

        return res.content, res.final_url, note, [log_item]

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
            html, _, _, _ = self._fetch(
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
            html, _, _, _ = self._fetch(
                C.PAGE_RACE_LIST,
                race_date=race_date,
                baba_code=baba_code,
                race_no=None,
                odds_flg=None,
            )
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)

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
                html_deba, _, _, _ = self._fetch(
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

                if _should_fetch_race_mark(start_dt=start_dt, now=now):
                    html_result, _, _, _ = self._fetch(
                        C.PAGE_RACE_MARK_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    _ = parse_race_mark_table(
                        html_result,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )

            if race_no is None:
                if _should_fetch_refund(last_start_dt=last_start_dt, now=now):
                    # payouts (for venues with completed races)
                    html_refund, _, _, _ = self._fetch(
                        C.PAGE_REFUND_MONEY_LIST,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=None,
                        odds_flg=None,
                    )
                    _ = parse_refund_money_list(
                        html_refund,
                        race_date=race_date,
                        baba_code=baba_code,
                    )

    def run_scheduled(
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
            html, _, _, _ = self._fetch(
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

        for baba_code in baba_codes:
            html, _, _, _ = self._fetch(
                C.PAGE_RACE_LIST,
                race_date=race_date,
                baba_code=baba_code,
                race_no=None,
                odds_flg=None,
            )
            races = parse_race_list(html, race_date=race_date, baba_code=baba_code)

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
                    html_deba, _, _, _ = self._fetch(
                        C.PAGE_DEBA_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    _ = parse_deba_table(
                        html_deba,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )

                snapshot = _scheduled_snapshot_kind(start_dt=start_dt, now=now)
                if snapshot is not None:
                    snapshot_kind, is_final = snapshot
                    self._scrape_odds_for_race(
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        snapshot_kind=snapshot_kind,
                        is_final=is_final,
                    )

                if _should_fetch_race_mark(start_dt=start_dt, now=now):
                    html_result, _, _, _ = self._fetch(
                        C.PAGE_RACE_MARK_TABLE,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                        odds_flg=None,
                    )
                    _ = parse_race_mark_table(
                        html_result,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=rn,
                    )

            if race_no is None:
                if _should_fetch_refund(last_start_dt=last_start_dt, now=now):
                    html_refund, _, _, _ = self._fetch(
                        C.PAGE_REFUND_MONEY_LIST,
                        race_date=race_date,
                        baba_code=baba_code,
                        race_no=None,
                        odds_flg=None,
                    )
                    _ = parse_refund_money_list(
                        html_refund,
                        race_date=race_date,
                        baba_code=baba_code,
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
            _ = (source_url, bet_type, odds_flg, items, captured_at, is_final)

        # OddsTanFuku (two modes)
        for flg in ODDS_FLG_FIXED.get(C.PAGE_ODDS_TANFUKU, [None]):
            html, final_url, note, _ = self._fetch(
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
            html, final_url, note, _ = self._fetch(
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
        html, final_url, note, _ = self._fetch(
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
        html, final_url, note, _ = self._fetch(
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
        html, final_url, note, _ = self._fetch(
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
        html, final_url, note, _ = self._fetch(
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
        html, final_url, note, _ = self._fetch(
            C.PAGE_ODDS_3LENTAN,
            race_date=race_date,
            baba_code=baba_code,
            race_no=race_no,
            odds_flg=None,
        )
        if note != "soft_no_odds":
            items = parse_generic_odds_table(html, bet_type="sanrentan")
            post_snapshot(final_url, "sanrentan", None, items)
