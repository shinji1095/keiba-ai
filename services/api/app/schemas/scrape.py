from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.odds import BetType, SnapshotKind
from app.schemas.race import RaceKey


class BatchUpsertResponse(BaseModel):
    accepted: int
    upserted: int
    warnings: Optional[list[str]] = None


class ManualScrapeTaskRequest(BaseModel):
    event_id: Optional[str] = Field(
        default=None, description="Idempotency key (optional)"
    )
    race_date: Optional[dt.date] = Field(
        default=None, description="YYYY-MM-DD (JST). Omit to use today (JST)."
    )
    baba_code: int
    race_no: Optional[int] = Field(default=None, ge=1, le=12)
    reason: Optional[str] = None


class ManualScrapeTaskResponse(BaseModel):
    task_id: str
    status: str
    accepted_at: dt.datetime


class ScrapeScheduleStatus(BaseModel):
    enabled: bool
    baba_codes: Optional[list[int]] = None
    mode: Optional[str] = None
    updated_at: dt.datetime
    note: Optional[str] = None


class ScrapeScheduleUpdateRequest(BaseModel):
    enabled: bool
    baba_codes: Optional[list[int]] = None


class ScrapeSyncRequest(BaseModel):
    event_id: Optional[str] = Field(
        default=None, description="Idempotency key (optional)"
    )
    reason: Optional[str] = None


class ScrapeSyncScheduleRequest(BaseModel):
    enabled: bool
    interval_days: int = Field(ge=1)
    diff_enabled: Optional[bool] = None


class ScrapeSyncResponse(BaseModel):
    sync_id: str
    status: str
    started_at: dt.datetime


class ScrapeSyncStatus(BaseModel):
    enabled: bool
    interval_days: int = Field(ge=1)
    diff_enabled: bool
    last_synced_at: Optional[dt.datetime] = None
    next_scheduled_at: Optional[dt.datetime] = None
    last_fingerprint: Optional[str] = None
    last_attempted_at: Optional[dt.datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_trigger: Optional[str] = None
    schedule_updated_at: Optional[dt.datetime] = None


class RaceUpsert(BaseModel):
    race_key: RaceKey
    start_time: Optional[dt.time] = None
    distance_m: Optional[int] = None
    course: Optional[str] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None
    race_name: Optional[str] = None
    field_size: Optional[int] = None
    status: Optional[str] = None


class RaceUpsertBatchRequest(BaseModel):
    event_id: str
    items: list[RaceUpsert] = Field(min_length=1)


class RaceEntryUpsert(BaseModel):
    race_key: RaceKey
    horse_id: Optional[int] = None
    post_position: Optional[int] = None
    horse_number: int
    horse_name: str
    jockey_name: Optional[str] = None
    trainer_name: Optional[str] = None
    handicap_kg: Optional[float] = None
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None


class RaceEntryUpsertBatchRequest(BaseModel):
    event_id: str
    items: list[RaceEntryUpsert] = Field(min_length=1)


class OddsItemUpsert(BaseModel):
    legs: list[int]
    is_ordered: bool
    odds_min: Optional[float] = None
    odds_max: Optional[float] = None
    popularity: Optional[int] = None
    raw_text: Optional[str] = None


class OddsSnapshotUpsertRequest(BaseModel):
    event_id: str
    race_key: RaceKey
    bet_type: BetType
    snapshot_kind: SnapshotKind
    captured_at: dt.datetime
    source_url: str
    odds_flg: Optional[int] = None
    is_final: bool = False
    items: list[OddsItemUpsert]


class OddsSnapshotUpsertResponse(BaseModel):
    race_id: int
    bet_type: BetType
    snapshot_kind: SnapshotKind
    odds_snapshot_id: int
    num_items: int


class RaceResultUpsert(BaseModel):
    race_key: RaceKey
    finish_position: int
    horse_number: Optional[int] = None
    time_str: Optional[str] = None
    margin: Optional[str] = None
    last3f: Optional[float] = None
    popularity: Optional[int] = None
    corner1: Optional[str] = None
    corner2: Optional[str] = None
    corner3: Optional[str] = None
    corner4: Optional[str] = None


class RaceResultUpsertBatchRequest(BaseModel):
    event_id: str
    items: list[RaceResultUpsert] = Field(min_length=1)


class PayoutUpsert(BaseModel):
    race_key: RaceKey
    bet_type: BetType
    legs: list[int]
    is_ordered: bool
    payout_yen: Optional[int] = None
    popularity: Optional[int] = None


class PayoutUpsertBatchRequest(BaseModel):
    event_id: str
    items: list[PayoutUpsert] = Field(min_length=1)


class RaceChangeInsert(BaseModel):
    race_key: RaceKey
    change_type: str
    payload: dict[str, Any]
    captured_at: dt.datetime


class RaceChangeInsertBatchRequest(BaseModel):
    event_id: str
    items: list[RaceChangeInsert] = Field(min_length=1)


class RawFetchLogInsert(BaseModel):
    race_key: Optional[RaceKey] = None
    page_type: str
    url: str
    http_status: int
    sha256: Optional[str] = None
    storage_path: Optional[str] = None
    captured_at: dt.datetime
    note: Optional[str] = None


class RawFetchLogInsertBatchRequest(BaseModel):
    event_id: str
    items: list[RawFetchLogInsert] = Field(min_length=1)
