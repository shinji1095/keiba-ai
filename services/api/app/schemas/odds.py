from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class BetType(str, Enum):
    tansho = "tansho"
    fukusho = "fukusho"
    wakuren = "wakuren"
    wakutan = "wakutan"
    umaren = "umaren"
    umatan = "umatan"
    wide = "wide"
    sanrenpuku = "sanrenpuku"
    sanrentan = "sanrentan"


SnapshotKind = str


class OddsSnapshot(BaseModel):
    odds_snapshot_id: int
    race_id: int
    bet_type: BetType
    snapshot_kind: SnapshotKind
    captured_at: dt.datetime
    source_url: str
    odds_flg: Optional[int] = None
    is_final: bool


class OddsItem(BaseModel):
    odds_item_id: int
    odds_snapshot_id: int
    legs: list[int]
    is_ordered: bool
    odds_min: Optional[float] = None
    odds_max: Optional[float] = None
    popularity: Optional[int] = None
    raw_text: Optional[str] = None


class OddsSnapshotQueryResponse(BaseModel):
    snapshot: OddsSnapshot
    items: list[OddsItem]
