from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_db, get_current_user
from app.schemas.venue import VenueListResponse
from app.services.race_service import RaceService

router = APIRouter()


@router.get("/venues", response_model=VenueListResponse)
def list_venues(db=Depends(get_db), _=Depends(get_current_user)) -> VenueListResponse:
    svc = RaceService(db)
    return svc.list_venues()
