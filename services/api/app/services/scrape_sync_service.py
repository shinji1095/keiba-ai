from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.schemas.scrape import (
    OddsSnapshotUpsertRequest,
    PayoutUpsert,
    PayoutUpsertBatchRequest,
    RaceChangeInsert,
    RaceChangeInsertBatchRequest,
    RaceEntryUpsert,
    RaceEntryUpsertBatchRequest,
    RaceResultUpsert,
    RaceResultUpsertBatchRequest,
    RaceUpsert,
    RaceUpsertBatchRequest,
)
from app.services.scrape_service import ScrapeService
from app.services.scrape_sync_state import SyncEntry, SyncState, SyncStateStore
from app.services.scraper_control_client import ScraperControlClient

PAGE_RACE_LIST = "RaceList"
PAGE_DEBA_TABLE = "DebaTable"
PAGE_RACE_MARK_TABLE = "RaceMarkTable"
PAGE_REFUND_MONEY_LIST = "RefundMoneyList"

ODDS_PAGE_BY_BET_TYPE = {
    "tansho": "OddsTanFuku",
    "fukusho": "OddsTanFuku",
    "wakuren": "OddsWakuLenFukuTan",
    "wakutan": "OddsWakuLenFukuTan",
    "umaren": "OddsUmLenFuku",
    "umatan": "OddsUmLenTan",
    "wide": "OddsWide",
    "sanrenpuku": "Odds3LenFuku",
    "sanrentan": "Odds3LenTan",
}


@dataclass
class SyncResult:
    sync_id: str
    started_at: datetime
    last_fingerprint: Optional[str]


def _build_scope_key(
    *,
    page_type: str,
    race_date: Optional[str],
    baba_code: Optional[int],
    race_no: Optional[int],
) -> str:
    if not race_date:
        raise ValueError("race_date is required for scope key")

    if page_type == PAGE_RACE_LIST or page_type == PAGE_REFUND_MONEY_LIST:
        if baba_code is None:
            raise ValueError("baba_code is required for venue scope")
        return f"{race_date}:{baba_code}"

    if (
        page_type == PAGE_DEBA_TABLE
        or page_type == PAGE_RACE_MARK_TABLE
        or page_type in set(ODDS_PAGE_BY_BET_TYPE.values())
    ):
        if baba_code is None or race_no is None:
            raise ValueError("baba_code and race_no are required for race scope")
        return f"{race_date}:{baba_code}:{race_no}"

    raise ValueError(f"unsupported page_type: {page_type}")


def _diff_key(
    *,
    page_type: str,
    race_date: Optional[str],
    baba_code: Optional[int],
    race_no: Optional[int],
    snapshot_kind: Optional[str] = None,
    odds_flg: Optional[int] = None,
) -> str:
    scope_key = _build_scope_key(
        page_type=page_type,
        race_date=race_date,
        baba_code=baba_code,
        race_no=race_no,
    )
    return f"{scope_key}|{page_type}|{snapshot_kind or ''}|{odds_flg or ''}"


def _fingerprint_payload(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _race_key_tuple(payload: dict) -> Optional[tuple[str, int, int]]:
    race_key = payload.get("race_key")
    if not isinstance(race_key, dict):
        return None
    race_date = race_key.get("race_date")
    baba_code = race_key.get("baba_code")
    race_no = race_key.get("race_no")
    if not isinstance(race_date, str) or not race_date:
        return None
    try:
        baba_code = int(baba_code)
        race_no = int(race_no)
    except (TypeError, ValueError):
        return None
    return (race_date, baba_code, race_no)


def _export_items(client: ScraperControlClient, path: str) -> list[dict]:
    payload = client.post_json(path, {})
    items = payload.get("items")
    if not isinstance(items, list):
        raise AppError.bad_gateway(
            "invalid export response",
            details={"path": path},
        )
    return [item for item in items if isinstance(item, dict)]


def _should_sync(state: SyncState, key: str, fingerprint: str, diff_enabled: bool) -> bool:
    if not diff_enabled:
        return True
    entry = state.items.get(key)
    if entry is None:
        return True
    return entry.fingerprint != fingerprint


class ScrapeSyncService:
    def __init__(
        self,
        db: Session,
        state_store: SyncStateStore,
        *,
        diff_enabled: bool = True,
    ) -> None:
        self.db = db
        self.state_store = state_store
        self.diff_enabled = diff_enabled

    def run_sync(self, *, trigger: str = "manual") -> SyncResult:
        state = self.state_store.load()
        now = datetime.now(timezone.utc)
        state.last_attempted_at = now
        state.last_trigger = trigger
        last_fingerprint: Optional[str] = None

        try:
            client = ScraperControlClient.from_settings()
            scrape_service = ScrapeService(self.db)

            races_items = _export_items(client, "/control/export/races")
            changes_items = _export_items(client, "/control/export/race-changes")
            entries_items = _export_items(client, "/control/export/race-entries")
            results_items = _export_items(client, "/control/export/race-results")
            payouts_items = _export_items(client, "/control/export/payouts")
            odds_items = _export_items(client, "/control/export/odds-snapshots")

            races_by_venue: dict[tuple[str, int], list[dict]] = {}
            for item in races_items:
                key = _race_key_tuple(item)
                if key is None:
                    continue
                races_by_venue.setdefault((key[0], key[1]), []).append(item)

            changes_by_venue: dict[tuple[str, int], list[dict]] = {}
            for item in changes_items:
                key = _race_key_tuple(item)
                if key is None:
                    continue
                changes_by_venue.setdefault((key[0], key[1]), []).append(item)

            race_list_keys = set(races_by_venue.keys()) | set(changes_by_venue.keys())
            for (race_date, baba_code) in race_list_keys:
                races_payloads = races_by_venue.get((race_date, baba_code), [])
                changes_payloads = changes_by_venue.get((race_date, baba_code), [])
                races_payloads.sort(
                    key=lambda x: int(x["race_key"]["race_no"])
                )
                changes_payloads.sort(
                    key=lambda x: (
                        int(x["race_key"]["race_no"]),
                        x.get("change_type") or "",
                        x.get("captured_at") or "",
                    )
                )

                diff_key = _diff_key(
                    page_type=PAGE_RACE_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                fingerprint = _fingerprint_payload(
                    {"races": races_payloads, "race_changes": changes_payloads}
                )
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    if races_payloads:
                        req = RaceUpsertBatchRequest(
                            items=[
                                RaceUpsert.model_validate(item)
                                for item in races_payloads
                            ],
                        )
                        scrape_service.upsert_races(req)
                    if changes_payloads:
                        req = RaceChangeInsertBatchRequest(
                            items=[
                                RaceChangeInsert.model_validate(item)
                                for item in changes_payloads
                            ],
                        )
                        scrape_service.insert_race_changes(req)
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            entries_by_race: dict[tuple[str, int, int], list[dict]] = {}
            for item in entries_items:
                key = _race_key_tuple(item)
                if key is None:
                    continue
                entries_by_race.setdefault(key, []).append(item)

            for (race_date, baba_code, race_no), items in entries_by_race.items():
                items.sort(key=lambda x: int(x["horse_number"]))
                diff_key = _diff_key(
                    page_type=PAGE_DEBA_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                fingerprint = _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    req = RaceEntryUpsertBatchRequest(
                        items=[
                            RaceEntryUpsert.model_validate(item) for item in items
                        ],
                    )
                    scrape_service.upsert_entries(req)
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            results_by_race: dict[tuple[str, int, int], list[dict]] = {}
            for item in results_items:
                key = _race_key_tuple(item)
                if key is None:
                    continue
                results_by_race.setdefault(key, []).append(item)

            for (race_date, baba_code, race_no), items in results_by_race.items():
                items.sort(key=lambda x: int(x["finish_position"]))
                diff_key = _diff_key(
                    page_type=PAGE_RACE_MARK_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                fingerprint = _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    req = RaceResultUpsertBatchRequest(
                        items=[
                            RaceResultUpsert.model_validate(item) for item in items
                        ],
                    )
                    scrape_service.upsert_results(req)
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            payouts_by_venue: dict[tuple[str, int], list[dict]] = {}
            for item in payouts_items:
                key = _race_key_tuple(item)
                if key is None:
                    continue
                payouts_by_venue.setdefault((key[0], key[1]), []).append(item)

            for (race_date, baba_code), items in payouts_by_venue.items():
                items.sort(
                    key=lambda x: (
                        int(x["race_key"]["race_no"]),
                        x.get("bet_type") or "",
                        x.get("legs") or [],
                        bool(x.get("is_ordered")),
                    )
                )
                diff_key = _diff_key(
                    page_type=PAGE_REFUND_MONEY_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                fingerprint = _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    req = PayoutUpsertBatchRequest(
                        items=[PayoutUpsert.model_validate(item) for item in items],
                    )
                    scrape_service.upsert_payouts(req)
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            for snap in odds_items:
                race_key = _race_key_tuple(snap)
                if race_key is None:
                    continue
                bet_type = snap.get("bet_type")
                if not isinstance(bet_type, str):
                    continue
                page_type = ODDS_PAGE_BY_BET_TYPE.get(bet_type)
                if page_type is None:
                    continue
                snapshot_kind = snap.get("snapshot_kind")
                if not isinstance(snapshot_kind, str):
                    continue
                odds_flg = snap.get("odds_flg")

                diff_key = _diff_key(
                    page_type=page_type,
                    race_date=race_key[0],
                    baba_code=race_key[1],
                    race_no=race_key[2],
                    snapshot_kind=snapshot_kind,
                    odds_flg=odds_flg,
                )

                item_payloads = snap.get("items")
                if not isinstance(item_payloads, list):
                    item_payloads = []
                item_payloads = [
                    item for item in item_payloads if isinstance(item, dict)
                ]
                item_payloads.sort(
                    key=lambda x: (
                        x.get("legs") or [],
                        bool(x.get("is_ordered")),
                        x.get("odds_min"),
                        x.get("odds_max"),
                        x.get("popularity"),
                        x.get("raw_text") or "",
                    )
                )

                fingerprint_payload = {
                    "race_key": snap.get("race_key"),
                    "bet_type": bet_type,
                    "snapshot_kind": snapshot_kind,
                    "captured_at": snap.get("captured_at"),
                    "source_url": snap.get("source_url"),
                    "odds_flg": odds_flg,
                    "is_final": snap.get("is_final", False),
                    "items": item_payloads,
                }
                fingerprint = _fingerprint_payload(fingerprint_payload)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    req = OddsSnapshotUpsertRequest.model_validate(fingerprint_payload)
                    scrape_service.upsert_odds_snapshot(req)
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            state.last_synced_at = now
            if last_fingerprint is not None:
                state.last_fingerprint = last_fingerprint
            state.last_status = "success"
            state.last_error = None
            self.state_store.save(state)
        except Exception as exc:
            state.last_status = "failed"
            state.last_error = str(exc)
            self.state_store.save(state)
            raise

        return SyncResult(
            sync_id=uuid.uuid4().hex,
            started_at=now,
            last_fingerprint=last_fingerprint,
        )
