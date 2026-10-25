from datetime import date
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends

from app.api.deps import DbDep
from app.api.monitoring_auth import monitoring_reader, monitoring_writer
from app.core.errors import AppError
from app.schemas.monitoring import (
    MetricEventList,
    MetricHistory,
    MetricReceipt,
    MetricSample,
    MetricStatus,
)
from app.services.monitoring_service import MonitoringService
from app.services.scrape_control_service import ScrapeControlService
from app.services.scraper_control_client import ScraperControlClient

router = APIRouter(tags=["monitoring"])


@router.post(
    "/system/metrics",
    response_model=MetricReceipt,
    dependencies=[Depends(monitoring_writer)],
)
def receive_metrics(payload: MetricSample, db: DbDep):
    return MonitoringService(db).ingest(payload)


@router.get(
    "/system/metrics",
    response_model=MetricStatus,
    dependencies=[Depends(monitoring_reader)],
)
def latest_metrics(db: DbDep):
    return MonitoringService(db).latest()


@router.get(
    "/system/metrics/history",
    response_model=MetricHistory,
    dependencies=[Depends(monitoring_reader)],
)
def metric_history(db: DbDep, hours: int = 1):
    if hours not in (1, 24, 168):
        raise AppError.bad_request("hours must be 1, 24 or 168")
    return MonitoringService(db).history(hours)


@router.get(
    "/system/events",
    response_model=MetricEventList,
    dependencies=[Depends(monitoring_reader)],
)
def metric_events(db: DbDep):
    return MonitoringService(db).events()


def control_client():
    client = ScraperControlClient.from_settings()
    client.timeout_sec = min(client.timeout_sec, 3)
    return client


@router.get("/scrape/status", dependencies=[Depends(monitoring_reader)])
def scrape_status():
    try:
        result = control_client().get_json("/control/status")
        result["connection"] = "ok"
    except (AppError, TimeoutError, OSError):
        result = {
            "connection": "unavailable",
            "error": "scraperへの接続に失敗しました",
        }
    try:
        result["sync"] = (
            ScrapeControlService().get_sync_status().model_dump(mode="json")
        )
    except (OSError, ValueError):
        result["sync"] = None
    return result


@router.get("/scrape/jobs", dependencies=[Depends(monitoring_reader)])
def scrape_jobs(
    race_date: str | None = None,
    baba_code: int | None = None,
    status: str | None = None,
    page: int = 1,
):
    if race_date:
        try:
            date.fromisoformat(race_date)
        except ValueError:
            raise AppError.bad_request("race_date must be YYYY-MM-DD")
    if page < 1 or page > 10000:
        raise AppError.bad_request("invalid page")
    query = urlencode(
        {
            k: v
            for k, v in {
                "race_date": race_date,
                "baba_code": baba_code,
                "status": status,
                "page": page,
            }.items()
            if v is not None
        }
    )
    return control_client().get_json(f"/control/jobs?{query}")


@router.get("/scrape/jobs/{job_id}", dependencies=[Depends(monitoring_reader)])
def scrape_job(job_id: str):
    result = control_client().get_json_optional(
        f"/control/jobs/{quote(job_id, safe='')}"
    )
    if result is None:
        raise AppError.not_found("scrape job not found")
    return result
