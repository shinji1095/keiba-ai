from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel


class SpecRaceCardRace(BaseModel):
    race_id: str
    race_date: dt.date
    baba_code: int
    race_no: int
    post_time: Optional[dt.time] = None
    race_name: str
    surface: Optional[str] = None
    distance_m: Optional[int] = None
    direction: Optional[str] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None


class SpecPerson(BaseModel):
    person_id: int
    role: str
    name: str
    affiliation: str


class SpecHorse(BaseModel):
    horse_id: int
    name: str
    sex: Optional[str] = None
    age: Optional[int] = None
    coat: Optional[str] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    birth_md_raw: Optional[str] = None
    sire: Optional[str] = None
    dam: Optional[str] = None
    dam_sire: Optional[str] = None
    breeder: Optional[str] = None


class SpecPerf(BaseModel):
    horse_id: int
    first_cnt: int
    second_cnt: int
    third_cnt: int
    out_cnt: int
    starts: int


class SpecBestTime(BaseModel):
    horse_id: int
    baba_code: int
    surface: str
    distance_m: int
    best_time_sec: Optional[float] = None
    best_time_good_sec: Optional[float] = None
    best_time_raw: Optional[str] = None
    best_time_good_raw: Optional[str] = None


class SpecRaceEntry(BaseModel):
    race_id: str
    horse_no: int
    waku: Optional[int] = None
    horse_id: Optional[int] = None
    burden_weight_display: float
    apprentice_allowance_symbol: Optional[str] = None
    apprentice_allowance_kg: Optional[int] = None
    burden_weight_base: Optional[float] = None
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None
    win_odds: Optional[float] = None
    popularity: Optional[int] = None
    jockey_person_id: Optional[int] = None
    trainer_person_id: Optional[int] = None
    owner_person_id: Optional[int] = None
    perf_total_id: Optional[int] = None
    perf_dirt_left_id: Optional[int] = None
    perf_dirt_right_id: Optional[int] = None
    perf_track_id: Optional[int] = None
    perf_distance_id: Optional[int] = None
    best_time_id: Optional[int] = None


class SpecLast5(BaseModel):
    race_id: str
    horse_no: int
    order_in_last5: int
    finish_pos: Optional[int] = None
    past_race_date: Optional[dt.date] = None
    track_condition: Optional[str] = None
    runners: Optional[int] = None
    place: Optional[str] = None
    direction: Optional[str] = None
    distance_m: Optional[int] = None
    horse_no_in_race: Optional[int] = None
    popularity: Optional[int] = None
    body_weight: Optional[int] = None
    jockey_name: Optional[str] = None
    burden_weight: Optional[float] = None
    time_raw: Optional[str] = None
    time_sec: Optional[float] = None
    passing_order_raw: Optional[str] = None
    passing_order_arr: Optional[list[int]] = None
    last3f: Optional[float] = None
    time_diff: Optional[float] = None
    winner_name: Optional[str] = None


class SpecRaceCardResponse(BaseModel):
    race: SpecRaceCardRace
    persons: list[SpecPerson]
    horses: list[SpecHorse]
    race_entries: list[SpecRaceEntry]
    perf_total: list[SpecPerf]
    perf_dirt_left: list[SpecPerf]
    perf_dirt_right: list[SpecPerf]
    perf_track: list[SpecPerf]
    perf_distance: list[SpecPerf]
    best_time: list[SpecBestTime]
    last5: list[SpecLast5]


