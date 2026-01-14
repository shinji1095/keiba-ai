from __future__ import annotations

from scraper_service.config import settings
from scraper_service.control_server import ScheduleStore
from scraper_service.http.client import HttpClient
from scraper_service.ingest.store import IngestStore
from scraper_service.scheduler.plan_scheduler import PlanScheduler, PlanStateStore
from scraper_service.scheduler.runner import ScrapeRunner


def _build_http() -> HttpClient:
    return HttpClient(
        user_agent=settings.user_agent,
        accept_language=settings.accept_language,
        min_interval_sec=settings.min_interval_sec,
        jitter_sec=settings.jitter_sec,
        max_retries=settings.max_retries,
        backoff_base_sec=settings.backoff_base_sec,
        backoff_max_sec=settings.backoff_max_sec,
    )


def main() -> None:
    http = _build_http()
    runner = ScrapeRunner(
        settings=settings,
        http=http,
        sync_store=IngestStore(settings.ingest_dir),
    )
    schedule_store = ScheduleStore(settings.schedule_path)
    state_store = PlanStateStore(settings.control_dir)
    scheduler = PlanScheduler(
        runner=runner,
        schedule_store=schedule_store,
        state_store=state_store,
        tick_sec=int(settings.tick_sec),
    )
    scheduler.run_forever()


if __name__ == "__main__":
    main()
