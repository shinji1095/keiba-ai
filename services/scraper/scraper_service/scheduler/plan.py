from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from scraper_service.keiba.models import BetType, RaceKey, SnapshotKind


TaskType = Literal[
    "fetch_race_list",
    "fetch_deba_table",
    "fetch_odds",
    "fetch_race_mark_table",
    "fetch_refund_money_list",
]


class Task(BaseModel):
    task_id: str
    task_type: TaskType
    due_at: str  # ISO-8601 with timezone
    race_key: Optional[RaceKey] = None

    # venue-level context (used when race_key is None)
    race_date: Optional[str] = None
    baba_code: Optional[int] = None

    # odds-related
    page_name: Optional[str] = None
    bet_type: Optional[BetType] = None
    snapshot_kind: Optional[SnapshotKind] = None
    odds_flg: Optional[int] = None
    is_final: bool = False

    done_at: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class Plan(BaseModel):
    race_date: str
    baba_codes: list[int]
    tasks: list[Task] = Field(default_factory=list)
    created_at: str
    updated_at: str
