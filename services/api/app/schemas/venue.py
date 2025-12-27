from __future__ import annotations

from pydantic import BaseModel


class Venue(BaseModel):
    baba_code: int
    venue_name: str


class VenueListResponse(BaseModel):
    items: list[Venue]
