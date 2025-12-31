from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from scraper_service.api.client import ApiClient
from scraper_service.config import Settings
from scraper_service.keiba import constants as C
from scraper_service.keiba.models import OddsSnapshotUpsertRequest, RaceKey, RawFetchLogInsert
from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.odds import parse_generic_odds_table, parse_odds_tanfuku, parse_odds_waku
from scraper_service.parsers.race_list import parse_race_list
from scraper_service.parsers.race_mark_table import parse_race_mark_table
from scraper_service.parsers.refund_money_list import parse_refund_money_list
from scraper_service.sync.diff import build_diff_key, should_sync_by_fingerprint
from scraper_service.sync.policy import should_sync_interval
from scraper_service.utils.time import iso_now_jst


ODDS_PAGES = {
    C.PAGE_ODDS_TANFUKU,
    C.PAGE_ODDS_WAKU,
    C.PAGE_ODDS_UMAREN,
    C.PAGE_ODDS_UMATAN,
    C.PAGE_ODDS_WIDE,
    C.PAGE_ODDS_3LENFUKU,
    C.PAGE_ODDS_3LENTAN,
}


@dataclass
class RawFetchLogRecord:
    fetched_at: str
    page_type: str
    race_date: Optional[str]
    baba_code: Optional[int]
    race_no: Optional[int]
    url: str
    final_url: str
    http_status: int
    sha256: Optional[str]
    storage_path: Optional[str]
    note: Optional[str]
    fetched_at_dt: datetime

    @property
    def source_url(self) -> str:
        return self.final_url or self.url

    def to_insert(self) -> RawFetchLogInsert:
        race_key = None
        if self.race_date and self.baba_code is not None and self.race_no is not None:
            race_key = RaceKey(race_date=self.race_date, baba_code=self.baba_code, race_no=self.race_no)
        return RawFetchLogInsert(
            race_key=race_key,
            page_type=self.page_type,
            url=self.source_url,
            http_status=self.http_status,
            sha256=self.sha256,
            storage_path=self.storage_path,
            fetched_at=self.fetched_at,
            note=self.note or None,
        )


@dataclass
class SyncState:
    last_synced_at: Optional[str]
    fingerprints: dict[str, str]


@dataclass
class SyncSummary:
    total: int
    synced: int
    skipped: int
    errors: int
    due: bool


class SyncRunner:
    def __init__(self, *, settings: Settings, api: ApiClient):
        self._settings = settings
        self._api = api
        self._log_path = settings.local_log_dir / "raw_fetch_logs.csv"
        self._state_path = settings.sync_state_path

    def run(self, *, force: bool = False) -> SyncSummary:
        state = self._load_state()
        if not force:
            if not should_sync_interval(
                last_synced_at=self._parse_datetime(state.last_synced_at),
                interval_days=self._settings.sync_interval_days,
            ):
                return SyncSummary(total=0, synced=0, skipped=0, errors=0, due=False)

        records = self._read_logs(self._log_path)
        latest = self._latest_by_key(records)
        summary = SyncSummary(total=len(latest), synced=0, skipped=0, errors=0, due=True)

        for key, record in latest.items():
            if not record.sha256:
                summary.skipped += 1
                continue
            prev = state.fingerprints.get(key)
            if not should_sync_by_fingerprint(prev, record.sha256):
                summary.skipped += 1
                continue

            try:
                self._sync_record(record)
            except Exception:
                summary.errors += 1
                continue

            state.fingerprints[key] = record.sha256
            summary.synced += 1

        if summary.synced > 0:
            state.last_synced_at = iso_now_jst()
        self._save_state(state)
        return summary

    def _sync_record(self, record: RawFetchLogRecord) -> None:
        self._api.post_raw_fetch_logs([record.to_insert()])

        if record.http_status >= 400:
            return
        if not record.storage_path:
            raise RuntimeError("storage_path is missing")
        html_path = Path(record.storage_path)
        if not html_path.exists():
            raise FileNotFoundError(html_path)

        html = html_path.read_bytes()
        page_type = record.page_type

        if page_type == C.PAGE_RACE_LIST:
            if not record.race_date or record.baba_code is None:
                raise RuntimeError("race_date/baba_code required for RaceList")
            races = parse_race_list(html, race_date=record.race_date, baba_code=record.baba_code)
            self._api.post_races(races)
            return

        if page_type == C.PAGE_DEBA_TABLE:
            if not record.race_date or record.baba_code is None or record.race_no is None:
                raise RuntimeError("race_date/baba_code/race_no required for DebaTable")
            entries = parse_deba_table(
                html,
                race_date=record.race_date,
                baba_code=record.baba_code,
                race_no=record.race_no,
            )
            self._api.post_race_entries(entries)
            return

        if page_type == C.PAGE_RACE_MARK_TABLE:
            if not record.race_date or record.baba_code is None or record.race_no is None:
                raise RuntimeError("race_date/baba_code/race_no required for RaceMarkTable")
            results = parse_race_mark_table(
                html,
                race_date=record.race_date,
                baba_code=record.baba_code,
                race_no=record.race_no,
            )
            self._api.post_race_results(results)
            return

        if page_type == C.PAGE_REFUND_MONEY_LIST:
            if not record.race_date or record.baba_code is None:
                raise RuntimeError("race_date/baba_code required for RefundMoneyList")
            payouts = parse_refund_money_list(
                html,
                race_date=record.race_date,
                baba_code=record.baba_code,
                captured_at_iso=record.fetched_at,
            )
            self._api.post_payouts(payouts)
            return

        if page_type in ODDS_PAGES:
            if not record.race_date or record.baba_code is None or record.race_no is None:
                raise RuntimeError("race_date/baba_code/race_no required for Odds pages")
            odds_flg = _extract_odds_flg(record.source_url)
            race_key = RaceKey(
                race_date=record.race_date,
                baba_code=record.baba_code,
                race_no=record.race_no,
            )
            self._sync_odds(
                page_type=page_type,
                race_key=race_key,
                html=html,
                source_url=record.source_url,
                captured_at=record.fetched_at,
                odds_flg=odds_flg,
            )
            return

    def _sync_odds(
        self,
        *,
        page_type: str,
        race_key: RaceKey,
        html: bytes,
        source_url: str,
        captured_at: str,
        odds_flg: Optional[int],
    ) -> None:
        def post_snapshot(bet_type: str, items, snapshot_kind: str = "manual", is_final: bool = False) -> None:
            req = OddsSnapshotUpsertRequest(
                race_key=race_key,
                bet_type=bet_type,  # type: ignore[arg-type]
                snapshot_kind=snapshot_kind,  # type: ignore[arg-type]
                captured_at=captured_at,
                source_url=source_url,
                odds_flg=odds_flg,
                is_final=is_final,
                items=items,
            )
            self._api.post_odds_snapshot(req)

        if page_type == C.PAGE_ODDS_TANFUKU:
            parsed = parse_odds_tanfuku(html)
            post_snapshot("tansho", parsed.get("tansho", []))
            post_snapshot("fukusho", parsed.get("fukusho", []))
            return

        if page_type == C.PAGE_ODDS_WAKU:
            parsed = parse_odds_waku(html)
            post_snapshot("wakuren", parsed.get("wakuren", []))
            post_snapshot("wakutan", parsed.get("wakutan", []))
            return

        if page_type == C.PAGE_ODDS_UMAREN:
            items = parse_generic_odds_table(html, bet_type="umaren")
            post_snapshot("umaren", items)
            return

        if page_type == C.PAGE_ODDS_UMATAN:
            items = parse_generic_odds_table(html, bet_type="umatan")
            post_snapshot("umatan", items)
            return

        if page_type == C.PAGE_ODDS_WIDE:
            items = parse_generic_odds_table(html, bet_type="wide")
            post_snapshot("wide", items)
            return

        if page_type == C.PAGE_ODDS_3LENFUKU:
            items = parse_generic_odds_table(html, bet_type="sanrenpuku")
            post_snapshot("sanrenpuku", items)
            return

        if page_type == C.PAGE_ODDS_3LENTAN:
            items = parse_generic_odds_table(html, bet_type="sanrentan")
            post_snapshot("sanrentan", items)
            return

    def _latest_by_key(self, records: list[RawFetchLogRecord]) -> dict[str, RawFetchLogRecord]:
        latest: dict[str, RawFetchLogRecord] = {}
        for record in records:
            key = self._diff_key(record)
            if key is None:
                continue
            current = latest.get(key)
            if current is None or record.fetched_at_dt > current.fetched_at_dt:
                latest[key] = record
        return latest

    def _diff_key(self, record: RawFetchLogRecord) -> Optional[str]:
        if not record.race_date:
            return None
        if record.page_type in ODDS_PAGES:
            snapshot_kind = "manual"
            odds_flg = _extract_odds_flg(record.source_url)
        else:
            snapshot_kind = None
            odds_flg = None

        try:
            key = build_diff_key(
                page_type=record.page_type,
                race_date=record.race_date,
                baba_code=record.baba_code,
                race_no=record.race_no,
                snapshot_kind=snapshot_kind,
                odds_flg=odds_flg,
            )
        except Exception:
            return None
        return _serialize_diff_key(key)

    def _load_state(self) -> SyncState:
        if not self._state_path.exists():
            return SyncState(last_synced_at=None, fingerprints={})
        data = json.loads(self._state_path.read_text(encoding="utf-8"))
        return SyncState(
            last_synced_at=data.get("last_synced_at"),
            fingerprints=data.get("fingerprints", {}),
        )

    def _save_state(self, state: SyncState) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_synced_at": state.last_synced_at,
            "fingerprints": state.fingerprints,
        }
        self._state_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _read_logs(self, path: Path) -> list[RawFetchLogRecord]:
        if not path.exists():
            return []
        out: list[RawFetchLogRecord] = []
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fetched_at = (row.get("fetched_at") or "").strip()
                if not fetched_at:
                    continue
                fetched_at_dt = self._parse_datetime(fetched_at)
                if fetched_at_dt is None:
                    continue

                race_date = (row.get("race_date") or "").strip() or None
                baba_code = _parse_int(row.get("baba_code"))
                race_no = _parse_int(row.get("race_no"))
                http_status = _parse_int(row.get("http_status")) or 0
                record = RawFetchLogRecord(
                    fetched_at=fetched_at,
                    page_type=(row.get("page_type") or "").strip(),
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                    url=(row.get("url") or "").strip(),
                    final_url=(row.get("final_url") or "").strip(),
                    http_status=http_status,
                    sha256=(row.get("sha256") or "").strip() or None,
                    storage_path=(row.get("storage_path") or "").strip() or None,
                    note=(row.get("note") or "").strip() or None,
                    fetched_at_dt=fetched_at_dt,
                )
                out.append(record)
        return out

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


def _serialize_diff_key(key: tuple[str, str, Optional[str], Optional[int]]) -> str:
    scope_key, page_type, snapshot_kind, odds_flg = key
    return "|".join(
        [
            scope_key,
            page_type,
            snapshot_kind or "",
            "" if odds_flg is None else str(odds_flg),
        ]
    )


def _extract_odds_flg(url: str) -> Optional[int]:
    if not url:
        return None
    try:
        q = parse_qs(urlparse(url).query)
        raw = q.get("odds_flg", [None])[0]
        return int(raw) if raw else None
    except (ValueError, TypeError):
        return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None
