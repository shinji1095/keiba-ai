from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_current_user, get_db
from app.schemas.spec_race_card import (
    SpecBestTime,
    SpecHorse,
    SpecLast5,
    SpecPerf,
    SpecPerson,
    SpecRaceCardRace,
    SpecRaceCardResponse,
    SpecRaceEntry,
)
from app.services.spec_race_card_service import SpecRaceCardService

router = APIRouter()


@router.get(
    "/spec/race-cards/{baba_code}/{race_date}/{race_no}",
    response_model=SpecRaceCardResponse,
)
def get_spec_race_card(
    baba_code: int = Path(..., ge=1),
    race_date: dt.date = Path(...),
    race_no: int = Path(..., ge=1, le=12),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> SpecRaceCardResponse:
    svc = SpecRaceCardService(db)
    card = svc.get_race_card(baba_code=baba_code, race_date=race_date, race_no=race_no)
    return SpecRaceCardResponse(
        race=SpecRaceCardRace(**card["race"]),
        persons=[SpecPerson(**p) for p in card["persons"]],
        horses=[SpecHorse(**h) for h in card["horses"]],
        race_entries=[SpecRaceEntry(**e) for e in card["race_entries"]],
        perf_total=[SpecPerf(**p) for p in card["perf_total"]],
        perf_dirt_left=[SpecPerf(**p) for p in card["perf_dirt_left"]],
        perf_dirt_right=[SpecPerf(**p) for p in card["perf_dirt_right"]],
        perf_track=[SpecPerf(**p) for p in card["perf_track"]],
        perf_distance=[SpecPerf(**p) for p in card["perf_distance"]],
        best_time=[SpecBestTime(**b) for b in card["best_time"]],
        last5=[SpecLast5(**x) for x in card["last5"]],
    )




