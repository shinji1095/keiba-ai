from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RaceKey(BaseModel):
    race_date: str = Field(..., description="YYYY-MM-DD (JST)")
    baba_code: int
    race_no: int


BetType = Literal[
    "tansho",
    "fukusho",
    "wakuren",
    "wakutan",
    "umaren",
    "umatan",
    "wide",
    "sanrenpuku",
    "sanrentan",
]


SnapshotKind = Literal[
    "t_minus_60m",
    "t_minus_30m",
    "t_minus_20m",
    "t_minus_10m",
    "t_minus_5m",
    "t_minus_1m",
    "final",
    "manual",
]


class OddsItemUpsert(BaseModel):
    legs: list[int]
    is_ordered: bool
    odds_min: Optional[float] = None
    odds_max: Optional[float] = None
    popularity: Optional[int] = None


class OddsSnapshotUpsertRequest(BaseModel):
    race_key: RaceKey
    bet_type: BetType
    snapshot_kind: SnapshotKind
    captured_at: str
    source_url: str
    odds_flg: Optional[int] = None
    is_final: bool = False
    items: list[OddsItemUpsert]


class RaceUpsert(BaseModel):
    race_key: RaceKey
    start_time: Optional[str] = None  # HH:MM:SS (OpenAPI 'time' format; we send HH:MM:SS)
    distance_m: Optional[int] = None
    course: Optional[str] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None
    race_name: Optional[str] = None
    field_size: Optional[int] = None
    status: Optional[str] = None


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


class PayoutUpsert(BaseModel):
    race_key: RaceKey
    bet_type: BetType
    legs: list[int]
    is_ordered: bool
    payout_yen: Optional[int] = None
    popularity: Optional[int] = None


class RaceChangeInsert(BaseModel):
    race_key: RaceKey
    change_type: str
    payload: dict[str, Any]
    captured_at: str
