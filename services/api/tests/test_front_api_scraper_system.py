import os
import datetime as dt
import pytest

from app.core.errors import AppError
from app.schemas.scrape import ManualScrapeTaskRequest
from app.services.scrape_control_service import ScrapeControlService
from app.services.scraper_control_client import ScraperControlClient


def _require_scraper_base_url() -> str:
    base_url = os.getenv("SCRAPER_CONTROL_BASE_URL", "").strip()
    if not base_url:
        pytest.skip("SCRAPER_CONTROL_BASE_URL is not set (Pi scraper control API)")
    return base_url


def _skip_or_fail_on_connection_error(exc: Exception) -> None:
    # In CI/dev environments without Pi connectivity, we don't want to fail hard.
    # If you want to enforce connectivity, set REQUIRE_PI_SCRAPER=1.
    require = os.getenv("REQUIRE_PI_SCRAPER", "").strip() in ("1", "true", "yes")
    if require:
        raise AssertionError("failed to reach Pi scraper control API") from exc
    pytest.skip(f"Pi scraper control API is not reachable: {exc}")


def _skip_or_fail_on_busy(exc: Exception) -> None:
    require = os.getenv("REQUIRE_PI_SCRAPER", "").strip() in ("1", "true", "yes")
    if require:
        raise AssertionError("Pi scraper is busy but required to accept manual tasks") from exc
    pytest.skip(f"Pi scraper is busy (skipping): {exc}")


@pytest.mark.system
def test_pi_scraper_control_health() -> None:
    _require_scraper_base_url()
    client = ScraperControlClient.from_settings()
    try:
        payload = client.get_json("/health")
    except Exception as exc:  # noqa: BLE001 - explicit skip/fail decision
        _skip_or_fail_on_connection_error(exc)
        return
    assert payload.get("status") == "ok"


@pytest.mark.system
def test_pi_scraper_control_schedule_can_be_fetched() -> None:
    _require_scraper_base_url()
    svc = ScrapeControlService()
    try:
        status = svc.get_schedule()
    except Exception as exc:  # noqa: BLE001 - explicit skip/fail decision
        _skip_or_fail_on_connection_error(exc)
        return
    assert isinstance(status.enabled, bool)
    # ScrapeScheduleStatus.baba_codes may be None depending on response
    assert status.updated_at is not None


@pytest.mark.system
def test_pi_scraper_control_manual_task_can_be_requested() -> None:
    _require_scraper_base_url()
    svc = ScrapeControlService()
    try:
        resp = svc.request_manual_task(
            ManualScrapeTaskRequest(
                baba_code=32,
                race_date=dt.date(2025, 12, 28),
                race_no=1,
                reason="system-test",
            )
        )
    except AppError as exc:
        if exc.status_code == 409:
            _skip_or_fail_on_busy(exc)
            return
        _skip_or_fail_on_connection_error(exc)
        return
    except Exception as exc:  # noqa: BLE001 - explicit skip/fail decision
        _skip_or_fail_on_connection_error(exc)
        return

    assert isinstance(resp.task_id, str)
    assert resp.task_id
    assert resp.status == "accepted"

