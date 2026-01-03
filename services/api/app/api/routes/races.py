from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import get_current_user, get_db
from app.schemas.odds import BetType, OddsSnapshotQueryResponse, SnapshotKind
from app.schemas.payout import PayoutListResponse
from app.schemas.race import (
    Race,
    RaceEntryListResponse,
    RaceEntryWithRaceListResponse,
    RaceEntryResultWithRaceListResponse,
    RaceListResponse,
    RaceResultListResponse,
)
from app.services.race_service import RaceService

router = APIRouter()


@router.get("/races", response_model=RaceListResponse)
def list_races(
    race_date: dt.date = Query(...),
    baba_code: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> RaceListResponse:
    svc = RaceService(db)
    return svc.list_races(
        race_date=race_date,
        baba_code=baba_code,
        page=page,
        page_size=page_size,
    )


@router.get("/races/{race_id}", response_model=Race)
def get_race(
    race_id: int = Path(..., ge=1),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> Race:
    svc = RaceService(db)
    return svc.get_race(race_id)


@router.get("/races/{race_id}/entries", response_model=RaceEntryListResponse)
def get_entries(
    race_id: int, db=Depends(get_db), _=Depends(get_current_user)
) -> RaceEntryListResponse:
    svc = RaceService(db)
    return svc.get_entries(race_id)


@router.get("/race-entries", response_model=RaceEntryWithRaceListResponse)
def list_race_entries(
    race_date: dt.date = Query(...),
    baba_code: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=500),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> RaceEntryWithRaceListResponse:
    svc = RaceService(db)
    return svc.list_race_entries(
        race_date=race_date,
        baba_code=baba_code,
        page=page,
        page_size=page_size,
    )


@router.get("/race-entry-results", response_model=RaceEntryResultWithRaceListResponse)
def list_race_entry_results(
    race_date: dt.date = Query(...),
    baba_code: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=500),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> RaceEntryResultWithRaceListResponse:
    svc = RaceService(db)
    return svc.list_race_entry_results(
        race_date=race_date,
        baba_code=baba_code,
        page=page,
        page_size=page_size,
    )


@router.get("/races/{race_id}/odds", response_model=OddsSnapshotQueryResponse)
def get_odds(
    race_id: int,
    snapshot_kind: SnapshotKind,
    bet_type: BetType,
    odds_flg: int | None = Query(default=None),
    db=Depends(get_db),
    _=Depends(get_current_user),
) -> OddsSnapshotQueryResponse:
    svc = RaceService(db)
    return svc.get_odds(
        race_id=race_id,
        snapshot_kind=snapshot_kind,
        bet_type=bet_type,
        odds_flg=odds_flg,
    )


@router.get("/races/{race_id}/results", response_model=RaceResultListResponse)
def get_results(
    race_id: int, db=Depends(get_db), _=Depends(get_current_user)
) -> RaceResultListResponse:
    svc = RaceService(db)
    return svc.get_results(race_id)


@router.get("/races/{race_id}/payouts", response_model=PayoutListResponse)
def get_payouts(
    race_id: int, db=Depends(get_db), _=Depends(get_current_user)
) -> PayoutListResponse:
    svc = RaceService(db)
    return svc.get_payouts(race_id)
