from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_user,
    get_db,
    get_scraper_principal,
    ScraperPrincipal,
)
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
    RawFetchLogInsertBatchRequest,
    ScrapeScheduleStatus,
    ScrapeSyncRequest,
    ScrapeSyncResponse,
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
    _=Depends(get_current_user),
) -> ManualScrapeTaskResponse:
    svc = ScrapeControlService()
    return svc.request_manual_task(payload)


@router.get("/scrape/schedule", response_model=ScrapeScheduleStatus)
def get_schedule() -> ScrapeScheduleStatus:
    svc = ScrapeControlService()
    return svc.get_schedule()


@router.post(
    "/scrape/sync",
    response_model=ScrapeSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync(
    payload: ScrapeSyncRequest | None = None,
    _=Depends(get_current_user),
) -> ScrapeSyncResponse:
    svc = ScrapeControlService()
    return svc.trigger_sync(payload)


@router.get("/scrape/sync/status", response_model=ScrapeSyncStatus)
def get_sync_status(
    _=Depends(get_current_user),
) -> ScrapeSyncStatus:
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
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.upsert_races(payload)


@router.post(
    "/scrape/race-entries",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_entries(
    payload: RaceEntryUpsertBatchRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.upsert_entries(payload)


@router.post(
    "/scrape/odds-snapshots",
    response_model=OddsSnapshotUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_odds(
    payload: OddsSnapshotUpsertRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> OddsSnapshotUpsertResponse:
    svc = ScrapeService(db)
    return svc.upsert_odds_snapshot(payload)


@router.post(
    "/scrape/race-results",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_results(
    payload: RaceResultUpsertBatchRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.upsert_results(payload)


@router.post(
    "/scrape/payouts",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def upsert_payouts(
    payload: PayoutUpsertBatchRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.upsert_payouts(payload)


@router.post(
    "/scrape/race-changes",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def insert_race_changes(
    payload: RaceChangeInsertBatchRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.insert_race_changes(payload)


@router.post(
    "/scrape/raw-fetch-logs",
    response_model=BatchUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def insert_raw_fetch_logs(
    payload: RawFetchLogInsertBatchRequest,
    db=Depends(get_db),
    principal: ScraperPrincipal = Depends(get_scraper_principal),
) -> BatchUpsertResponse:
    svc = ScrapeService(db)
    return svc.insert_raw_fetch_logs(payload)
