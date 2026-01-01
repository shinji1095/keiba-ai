from __future__ import annotations

from datetime import datetime, timezone

from zoneinfo import ZoneInfo

from app.services.scrape_sync_policy import next_scheduled_at, should_run_sync

JST = ZoneInfo("Asia/Tokyo")


def test_should_run_sync_when_never_synced() -> None:
    now = datetime(2025, 12, 28, 9, 0, 0, tzinfo=JST)
    assert should_run_sync(last_synced_at=None, interval_days=2, now=now) is True


def test_should_run_sync_same_day_jst() -> None:
    last = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 23, 59, 0, tzinfo=JST)
    assert should_run_sync(last_synced_at=last, interval_days=2, now=now) is False


def test_should_run_sync_next_day_not_due() -> None:
    last = datetime(2025, 12, 27, 23, 59, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    assert should_run_sync(last_synced_at=last, interval_days=2, now=now) is False


def test_should_run_sync_two_days() -> None:
    last = datetime(2025, 12, 26, 23, 59, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    assert should_run_sync(last_synced_at=last, interval_days=2, now=now) is True


def test_next_scheduled_at_jst_boundary() -> None:
    last = datetime(2025, 12, 28, 10, 30, 0, tzinfo=JST)
    next_at = next_scheduled_at(last_synced_at=last, interval_days=2)
    assert next_at is not None
    assert next_at.astimezone(JST).date().isoformat() == "2025-12-30"
    assert next_at.astimezone(JST).hour == 0
    assert next_at.astimezone(JST).minute == 0
