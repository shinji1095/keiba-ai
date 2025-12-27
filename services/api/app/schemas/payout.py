from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.schemas.odds import BetType


class Payout(BaseModel):
    payout_id: int
    race_id: int
    bet_type: BetType
    legs: list[int]
    is_ordered: bool
    payout_yen: Optional[int] = None
    popularity: Optional[int] = None


class PayoutListResponse(BaseModel):
    items: list[Payout]
