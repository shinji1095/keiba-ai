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
    snapshot_kinds: Optional[list[str]] = None
    prefetch_days: Optional[int] = Field(default=None, ge=0, le=31)
    mode: Optional[str] = None
    updated_at: dt.datetime
    note: Optional[str] = None


class ScrapeScheduleUpdateRequest(BaseModel):
    enabled: bool
    baba_codes: Optional[list[int]] = None
    snapshot_kinds: Optional[list[str]] = None
    prefetch_days: Optional[int] = Field(default=None, ge=0, le=31)


class ScrapePlanKey(BaseModel):
    race_date: str
    baba_code: int
    race_no: Optional[int] = None


class ScrapePlanItem(BaseModel):
    task_kind: str
    page_name: str
    race_key: ScrapePlanKey
    start_time: Optional[str] = None
    snapshot_kind: str
    odds_flg: Optional[int] = None
    target_at: dt.datetime
    scheduled_at: dt.datetime
    priority: int
    within_tolerance: bool
    delay_sec: int


class ScrapePlan(BaseModel):
    race_date: str
    snapshot_kinds: list[str]
    generated_at: dt.datetime
    interval_sec: int
    tolerance_sec: int
    items: list[ScrapePlanItem]


class ScrapeSyncRequest(BaseModel):
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
    items: list[RaceEntryUpsert] = Field(min_length=1)


class OddsItemUpsert(BaseModel):
    legs: list[int]
    is_ordered: bool
    odds_min: Optional[float] = None
    odds_max: Optional[float] = None
    popularity: Optional[int] = None
    raw_text: Optional[str] = None


class OddsSnapshotUpsertRequest(BaseModel):
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
    items: list[RaceResultUpsert] = Field(min_length=1)


class PayoutUpsert(BaseModel):
    race_key: RaceKey
    bet_type: BetType
    legs: list[int]
    is_ordered: bool
    payout_yen: Optional[int] = None
    popularity: Optional[int] = None


class PayoutUpsertBatchRequest(BaseModel):
    items: list[PayoutUpsert] = Field(min_length=1)


class RaceChangeInsert(BaseModel):
    race_key: RaceKey
    change_type: str
    payload: dict[str, Any]
    captured_at: dt.datetime


class RaceChangeInsertBatchRequest(BaseModel):
    items: list[RaceChangeInsert] = Field(min_length=1)
