from __future__ import annotations

from datetime import datetime

from scraper_service.sync.policy import should_sync_interval
from scraper_service.utils.time import JST


def test_should_sync_interval_when_never_synced() -> None:
    now = datetime(2025, 12, 28, 9, 0, 0, tzinfo=JST)
    assert should_sync_interval(last_synced_at=None, interval_days=2, now=now) is True


def test_should_sync_interval_same_day() -> None:
    last = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 23, 59, 0, tzinfo=JST)
    assert should_sync_interval(last_synced_at=last, interval_days=2, now=now) is False


def test_should_sync_interval_next_day_not_due() -> None:
    last = datetime(2025, 12, 27, 23, 59, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    assert should_sync_interval(last_synced_at=last, interval_days=2, now=now) is False


def test_should_sync_interval_two_days() -> None:
    last = datetime(2025, 12, 26, 23, 59, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    assert should_sync_interval(last_synced_at=last, interval_days=2, now=now) is True
