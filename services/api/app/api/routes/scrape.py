from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_db
from app.schemas.scrape import (
    BatchUpsertResponse,
    ManualScrapeTaskRequest,
    ManualScrapeTaskResponse,
    OddsSnapshotUpsertRequest,
    OddsSnapshotUpsertResponse,
    PayoutUpsertBatchRequest,
    RaceChangeInsertBatchRequest,
    RaceEntryUpsertBatchRequest,
    RaceResultUpsertBatchRequest,
    RaceUpsertBatchRequest,
    ScrapePlan,
    ScrapeScheduleStatus,
    ScrapeScheduleUpdateRequest,
    ScrapeSyncRequest,
    ScrapeSyncResponse,
    ScrapeSyncScheduleRequest,
    ScrapeSyncStatus,
)
from app.services.scrape_control_service import ScrapeControlService
from app.services.scrape_service import ScrapeService

router = APIRouter()


@router.post(
    "/scrape/manual-tasks",
    response_model=ManualScrapeTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_manual_task(
    payload: ManualScrapeTaskRequest,
) -> ManualScrapeTaskResponse:
    svc = ScrapeControlService()
    return svc.request_manual_task(payload)


@router.get("/scrape/schedule", response_model=ScrapeScheduleStatus)
def get_schedule() -> ScrapeScheduleStatus:
    svc = ScrapeControlService()
    return svc.get_schedule()


@router.post("/scrape/schedule", response_model=ScrapeScheduleStatus)
def update_schedule(
    payload: ScrapeScheduleUpdateRequest,
) -> ScrapeScheduleStatus:
    svc = ScrapeControlService()
    return svc.update_schedule(payload)


@router.get("/scrape/plan", response_model=ScrapePlan)
def get_plan(race_date: dt.date | None = None) -> ScrapePlan:
    svc = ScrapeControlService()
    return svc.get_plan(race_date=race_date)


@router.post(
    "/scrape/sync",
    response_model=ScrapeSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync(
    payload: ScrapeSyncRequest | None = None,
    db=Depends(get_db),
) -> ScrapeSyncResponse:
    svc = ScrapeControlService(db=db)
    return svc.trigger_sync(payload)


@router.post(
    "/scrape/sync/scheduled",
    response_model=ScrapeSyncResponse,
)
def trigger_scheduled_sync(
    response: Response,
    payload: ScrapeSyncRequest | None = None,
    db=Depends(get_db),
) -> ScrapeSyncResponse:
    svc = ScrapeControlService(db=db)
    result = svc.trigger_scheduled_sync(payload)
    response.status_code = (
        status.HTTP_200_OK
        if result.status == "skipped"
        else status.HTTP_202_ACCEPTED
    )
    return result


@router.post(
    "/scrape/sync/schedule",
    response_model=ScrapeSyncStatus,
)
def update_sync_schedule(
    payload: ScrapeSyncScheduleRequest,
) -> ScrapeSyncStatus:
    svc = ScrapeControlService()
    return svc.update_sync_schedule(payload)


@router.get("/scrape/sync/status", response_model=ScrapeSyncStatus)
def get_sync_status() -> ScrapeSyncStatus:
    svc = ScrapeControlService()
    return svc.get_sync_status()


@router.post(
    "/scrape/races",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_races(
    payload: RaceUpsertBatchRequest,
    db=Depends(get_db),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.upsert_races(payload)
    return resp


@router.post(
    "/scrape/race-entries",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_entries(
    payload: RaceEntryUpsertBatchRequest,
    db=Depends(get_db),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.upsert_entries(payload)
    return resp


@router.post(
    "/scrape/odds-snapshots",
    response_model=OddsSnapshotUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_odds(
    payload: OddsSnapshotUpsertRequest,
    db=Depends(get_db),
) -> OddsSnapshotUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.upsert_odds_snapshot(payload)
    return resp


@router.post(
    "/scrape/race-results",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_results(
    payload: RaceResultUpsertBatchRequest,
    db=Depends(get_db),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.upsert_results(payload)
    return resp


@router.post(
    "/scrape/payouts",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_payouts(
    payload: PayoutUpsertBatchRequest,
    db=Depends(get_db),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.upsert_payouts(payload)
    return resp


@router.post(
    "/scrape/race-changes",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def insert_race_changes(
    payload: RaceChangeInsertBatchRequest,
    db=Depends(get_db),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    resp = svc.insert_race_changes(payload)
    return resp
