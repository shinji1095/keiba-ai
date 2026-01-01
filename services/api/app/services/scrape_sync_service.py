from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.odds import OddsItem as OddsItemModel
from app.db.models.odds import OddsSnapshot as OddsSnapshotModel
from app.db.models.payout import Payout as PayoutModel
from app.db.models.race import Race as RaceModel
from app.db.models.race_change import RaceChange as RaceChangeModel
from app.db.models.race_entry import RaceEntry as RaceEntryModel
from app.db.models.race_result import RaceResult as RaceResultModel
from app.db.models.raw_fetch_log import RawFetchLog as RawFetchLogModel
from app.services.scrape_sync_state import SyncEntry, SyncState, SyncStateStore
from app.services.scraper_ingest_client import ScraperIngestClient

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

NON_ODDS_PAGES = {
    PAGE_RACE_LIST,
    PAGE_DEBA_TABLE,
    PAGE_RACE_MARK_TABLE,
    PAGE_REFUND_MONEY_LIST,
}


@dataclass
class SyncResult:
    sync_id: str
    started_at: datetime
    last_fingerprint: Optional[str]


@dataclass
class LogFingerprint:
    sha256: str
    captured_at: datetime


def _parse_race_date(value: str) -> Optional[str]:
    if not value:
        return None
    parts = value.split("/")
    if len(parts) != 3:
        return None
    try:
        y = int(parts[0])
        m = int(parts[1])
        d = int(parts[2])
    except ValueError:
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


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


def _race_key_dict(race: RaceModel) -> dict[str, object]:
    return {
        "race_date": race.race_date.isoformat(),
        "baba_code": race.baba_code,
        "race_no": race.race_no,
    }


def _build_log_index(db: Session) -> dict[tuple[str, str], LogFingerprint]:
    index: dict[tuple[str, str], LogFingerprint] = {}
    rows = (
        db.query(RawFetchLogModel, RaceModel)
        .outerjoin(RaceModel, RawFetchLogModel.race_id == RaceModel.race_id)
        .filter(RawFetchLogModel.page_type.in_(NON_ODDS_PAGES))
        .all()
    )

    for log, race in rows:
        if not log.sha256:
            continue

        race_date = None
        baba_code = None
        race_no = None

        if race is not None:
            race_date = race.race_date.isoformat()
            baba_code = race.baba_code
            race_no = race.race_no
        else:
            parsed = parse_qs(urlparse(log.url).query)
            raw_date = parsed.get("k_raceDate", [None])[0]
            if raw_date:
                race_date = _parse_race_date(raw_date)
            raw_baba = parsed.get("k_babaCode", [None])[0]
            if raw_baba:
                try:
                    baba_code = int(raw_baba)
                except ValueError:
                    baba_code = None
            raw_no = parsed.get("k_raceNo", [None])[0]
            if raw_no:
                try:
                    race_no = int(raw_no)
                except ValueError:
                    race_no = None

        try:
            scope_key = _build_scope_key(
                page_type=log.page_type,
                race_date=race_date,
                baba_code=baba_code,
                race_no=race_no,
            )
        except ValueError:
            continue

        key = (log.page_type, scope_key)
        current = index.get(key)
        captured_at = log.captured_at
        if current is None or captured_at > current.captured_at:
            index[key] = LogFingerprint(
                sha256=log.sha256,
                captured_at=captured_at,
            )

    return index


def _dt_to_ts(value: datetime) -> float:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.astimezone(timezone.utc).timestamp()


def _build_odds_log_index(db: Session) -> dict[str, list[LogFingerprint]]:
    index: dict[str, list[LogFingerprint]] = {}
    rows = (
        db.query(RawFetchLogModel)
        .filter(RawFetchLogModel.page_type.in_(set(ODDS_PAGE_BY_BET_TYPE.values())))
        .all()
    )

    for log in rows:
        if not log.sha256 or not log.url:
            continue
        index.setdefault(log.url, []).append(
            LogFingerprint(sha256=log.sha256, captured_at=log.captured_at)
        )

    return index


def _pick_nearest_log(
    logs: list[LogFingerprint], captured_at: datetime
) -> Optional[LogFingerprint]:
    if not logs:
        return None
    target = _dt_to_ts(captured_at)
    return min(
        logs,
        key=lambda item: abs(_dt_to_ts(item.captured_at) - target),
    )


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
            client = ScraperIngestClient.from_settings()
            if client is None:
                raise AppError.internal("scraper forward is disabled")

            log_index = _build_log_index(self.db)
            odds_log_index = _build_odds_log_index(self.db)

            races_by_venue: dict[tuple[str, int], list[dict[str, object]]] = {}
            for race in self.db.query(RaceModel).all():
                key = (race.race_date.isoformat(), race.baba_code)
                races_by_venue.setdefault(key, []).append(
                    {
                        "race_key": _race_key_dict(race),
                        "start_time": race.start_time.isoformat() if race.start_time else None,
                        "distance_m": race.distance_m,
                        "course": race.course,
                        "weather": race.weather,
                        "track_condition": race.track_condition,
                        "race_name": race.race_name,
                        "field_size": race.field_size,
                        "status": race.status,
                    }
                )

            changes_by_venue: dict[tuple[str, int], list[dict[str, object]]] = {}
            rows = (
                self.db.query(RaceChangeModel, RaceModel)
                .join(RaceModel, RaceChangeModel.race_id == RaceModel.race_id)
                .all()
            )
            for change, race in rows:
                key = (race.race_date.isoformat(), race.baba_code)
                changes_by_venue.setdefault(key, []).append(
                    {
                        "race_key": _race_key_dict(race),
                        "change_type": change.change_type,
                        "payload": change.payload,
                        "captured_at": change.captured_at.isoformat(),
                    }
                )

            race_list_keys = set(races_by_venue.keys()) | set(changes_by_venue.keys())
            for (race_date, baba_code) in race_list_keys:
                races_items = races_by_venue.get((race_date, baba_code), [])
                changes_items = changes_by_venue.get((race_date, baba_code), [])
                races_items.sort(key=lambda x: x["race_key"]["race_no"])
                changes_items.sort(
                    key=lambda x: (
                        x["race_key"]["race_no"],
                        x["change_type"],
                        x["captured_at"],
                    )
                )

                scope_key = _build_scope_key(
                    page_type=PAGE_RACE_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                diff_key = _diff_key(
                    page_type=PAGE_RACE_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                log_fp = log_index.get((PAGE_RACE_LIST, scope_key))
                if log_fp:
                    fingerprint = log_fp.sha256
                else:
                    fingerprint = _fingerprint_payload(
                        {"races": races_items, "race_changes": changes_items}
                    )
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    event_id = str(uuid.uuid4())
                    if races_items:
                        client.post(
                            "/control/ingest/races",
                            {"event_id": event_id, "items": races_items},
                        )
                    if changes_items:
                        client.post(
                            "/control/ingest/race-changes",
                            {"event_id": event_id, "items": changes_items},
                        )
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            entries_by_race: dict[tuple[str, int, int], list[dict[str, object]]] = {}
            rows = (
                self.db.query(RaceEntryModel, RaceModel)
                .join(RaceModel, RaceEntryModel.race_id == RaceModel.race_id)
                .all()
            )
            for entry, race in rows:
                key = (
                    race.race_date.isoformat(),
                    race.baba_code,
                    race.race_no,
                )
                entries_by_race.setdefault(key, []).append(
                    {
                        "race_key": _race_key_dict(race),
                        "horse_id": entry.horse_id,
                        "post_position": entry.post_position,
                        "horse_number": entry.horse_number,
                        "horse_name": entry.horse_name,
                        "jockey_name": entry.jockey_name,
                        "trainer_name": entry.trainer_name,
                        "handicap_kg": entry.handicap_kg,
                        "body_weight": entry.body_weight,
                        "body_weight_diff": entry.body_weight_diff,
                    }
                )

            for (race_date, baba_code, race_no), items in entries_by_race.items():
                items.sort(key=lambda x: x["horse_number"])
                scope_key = _build_scope_key(
                    page_type=PAGE_DEBA_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                diff_key = _diff_key(
                    page_type=PAGE_DEBA_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                log_fp = log_index.get((PAGE_DEBA_TABLE, scope_key))
                fingerprint = log_fp.sha256 if log_fp else _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    client.post(
                        "/control/ingest/race-entries",
                        {"event_id": str(uuid.uuid4()), "items": items},
                    )
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            results_by_race: dict[tuple[str, int, int], list[dict[str, object]]] = {}
            rows = (
                self.db.query(RaceResultModel, RaceModel)
                .join(RaceModel, RaceResultModel.race_id == RaceModel.race_id)
                .all()
            )
            for result, race in rows:
                key = (
                    race.race_date.isoformat(),
                    race.baba_code,
                    race.race_no,
                )
                results_by_race.setdefault(key, []).append(
                    {
                        "race_key": _race_key_dict(race),
                        "finish_position": result.finish_position,
                        "horse_number": result.horse_number,
                        "time_str": result.time_str,
                        "margin": result.margin,
                        "last3f": result.last3f,
                        "popularity": result.popularity,
                        "corner1": result.corner1,
                        "corner2": result.corner2,
                        "corner3": result.corner3,
                        "corner4": result.corner4,
                    }
                )

            for (race_date, baba_code, race_no), items in results_by_race.items():
                items.sort(key=lambda x: x["finish_position"])
                scope_key = _build_scope_key(
                    page_type=PAGE_RACE_MARK_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                diff_key = _diff_key(
                    page_type=PAGE_RACE_MARK_TABLE,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                )
                log_fp = log_index.get((PAGE_RACE_MARK_TABLE, scope_key))
                fingerprint = log_fp.sha256 if log_fp else _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    client.post(
                        "/control/ingest/race-results",
                        {"event_id": str(uuid.uuid4()), "items": items},
                    )
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            payouts_by_venue: dict[tuple[str, int], list[dict[str, object]]] = {}
            rows = (
                self.db.query(PayoutModel, RaceModel)
                .join(RaceModel, PayoutModel.race_id == RaceModel.race_id)
                .all()
            )
            for payout, race in rows:
                key = (race.race_date.isoformat(), race.baba_code)
                payouts_by_venue.setdefault(key, []).append(
                    {
                        "race_key": _race_key_dict(race),
                        "bet_type": payout.bet_type,
                        "legs": list(payout.legs),
                        "is_ordered": payout.is_ordered,
                        "payout_yen": payout.payout_yen,
                        "popularity": payout.popularity,
                    }
                )

            for (race_date, baba_code), items in payouts_by_venue.items():
                items.sort(
                    key=lambda x: (
                        x["race_key"]["race_no"],
                        x["bet_type"],
                        x["legs"],
                        x["is_ordered"],
                    )
                )
                scope_key = _build_scope_key(
                    page_type=PAGE_REFUND_MONEY_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                diff_key = _diff_key(
                    page_type=PAGE_REFUND_MONEY_LIST,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=None,
                )
                log_fp = log_index.get((PAGE_REFUND_MONEY_LIST, scope_key))
                fingerprint = log_fp.sha256 if log_fp else _fingerprint_payload(items)
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    client.post(
                        "/control/ingest/payouts",
                        {"event_id": str(uuid.uuid4()), "items": items},
                    )
                    state.items[diff_key] = SyncEntry(
                        fingerprint=fingerprint, updated_at=now
                    )
                    last_fingerprint = fingerprint

            snapshots = (
                self.db.query(OddsSnapshotModel, RaceModel)
                .join(RaceModel, OddsSnapshotModel.race_id == RaceModel.race_id)
                .all()
            )
            for snap, race in snapshots:
                items = (
                    self.db.query(OddsItemModel)
                    .filter(
                        OddsItemModel.odds_snapshot_id == snap.odds_snapshot_id
                    )
                    .all()
                )
                item_payloads = [
                    {
                        "legs": list(it.legs),
                        "is_ordered": it.is_ordered,
                        "odds_min": it.odds_min,
                        "odds_max": it.odds_max,
                        "popularity": it.popularity,
                        "raw_text": it.raw_text,
                    }
                    for it in items
                ]
                item_payloads.sort(
                    key=lambda x: (
                        x["legs"],
                        x["is_ordered"],
                        x.get("odds_min"),
                        x.get("odds_max"),
                        x.get("popularity"),
                        x.get("raw_text") or "",
                    )
                )

                page_type = ODDS_PAGE_BY_BET_TYPE.get(snap.bet_type)
                if page_type is None:
                    continue

                diff_key = _diff_key(
                    page_type=page_type,
                    race_date=race.race_date.isoformat(),
                    baba_code=race.baba_code,
                    race_no=race.race_no,
                    snapshot_kind=snap.snapshot_kind,
                    odds_flg=snap.odds_flg,
                )
                payload = {
                    "event_id": str(uuid.uuid4()),
                    "race_key": _race_key_dict(race),
                    "bet_type": snap.bet_type,
                    "snapshot_kind": snap.snapshot_kind,
                    "captured_at": snap.captured_at.isoformat(),
                    "source_url": snap.source_url,
                    "odds_flg": snap.odds_flg,
                    "is_final": snap.is_final,
                    "items": item_payloads,
                }
                log_fp = _pick_nearest_log(
                    odds_log_index.get(snap.source_url, []),
                    snap.captured_at,
                )
                fingerprint = (
                    log_fp.sha256
                    if log_fp is not None
                    else _fingerprint_payload(payload)
                )
                if _should_sync(state, diff_key, fingerprint, self.diff_enabled):
                    client.post("/control/ingest/odds-snapshots", payload)
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
