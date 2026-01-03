from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class RaceKey(BaseModel):
    race_date: dt.date
    baba_code: int
    race_no: int = Field(ge=1, le=12)


class RaceSummary(BaseModel):
    race_id: int
    race_key: RaceKey
    start_time: Optional[dt.time] = None
    race_name: Optional[str] = None
    status: Optional[str] = None


class Race(BaseModel):
    race_id: int
    race_key: RaceKey
    start_time: Optional[dt.time] = None
    distance_m: Optional[int] = None
    course: Optional[str] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None
    race_name: Optional[str] = None
    field_size: Optional[int] = None
    status: Optional[str] = None


class RaceListResponse(BaseModel):
    items: list[RaceSummary]
    page: int
    page_size: int


class RaceEntry(BaseModel):
    race_entry_id: int
    race_id: int
    horse_id: Optional[int] = None
    post_position: Optional[int] = None
    horse_number: int
    horse_name: str
    jockey_name: Optional[str] = None
    trainer_name: Optional[str] = None
    handicap_kg: Optional[float] = None
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None


class RaceEntryListResponse(BaseModel):
    items: list[RaceEntry]


class RaceEntryWithRace(BaseModel):
    race_entry_id: int
    race_id: int
    race_key: RaceKey
    start_time: Optional[dt.time] = None
    race_name: Optional[str] = None
    status: Optional[str] = None

    horse_id: Optional[int] = None
    post_position: Optional[int] = None
    horse_number: int
    horse_name: str
    jockey_name: Optional[str] = None
    trainer_name: Optional[str] = None
    handicap_kg: Optional[float] = None
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None


class RaceEntryWithRaceListResponse(BaseModel):
    items: list[RaceEntryWithRace]
    page: int
    page_size: int


class RaceEntryResultWithRace(BaseModel):
    race_entry_id: int
    race_id: int
    race_key: RaceKey
    start_time: Optional[dt.time] = None
    race_name: Optional[str] = None
    status: Optional[str] = None

    horse_id: Optional[int] = None
    post_position: Optional[int] = None
    horse_number: int
    horse_name: str
    jockey_name: Optional[str] = None
    trainer_name: Optional[str] = None
    handicap_kg: Optional[float] = None
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None

    # Result (may be missing if not scraped/ingested yet)
    race_result_id: Optional[int] = None
    finish_position: Optional[int] = None
    time_str: Optional[str] = None
    margin: Optional[str] = None
    last3f: Optional[float] = None
    popularity: Optional[int] = None
    corner1: Optional[str] = None
    corner2: Optional[str] = None
    corner3: Optional[str] = None
    corner4: Optional[str] = None


class RaceEntryResultWithRaceListResponse(BaseModel):
    items: list[RaceEntryResultWithRace]
    page: int
    page_size: int


class RaceResult(BaseModel):
    race_result_id: int
    race_id: int
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


class RaceResultListResponse(BaseModel):
    items: list[RaceResult]
