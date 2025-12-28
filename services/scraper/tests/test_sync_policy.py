from __future__ import annotations

from datetime import datetime

from scraper_service.sync.policy import should_sync_daily
from scraper_service.utils.time import JST


def test_should_sync_daily_when_never_synced() -> None:
    now = datetime(2025, 12, 28, 9, 0, 0, tzinfo=JST)
    assert should_sync_daily(last_synced_at=None, now=now) is True


def test_should_sync_daily_same_day() -> None:
    last = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 23, 59, 0, tzinfo=JST)
    assert should_sync_daily(last_synced_at=last, now=now) is False


def test_should_sync_daily_next_day() -> None:
    last = datetime(2025, 12, 27, 23, 59, 0, tzinfo=JST)
    now = datetime(2025, 12, 28, 0, 1, 0, tzinfo=JST)
    assert should_sync_daily(last_synced_at=last, now=now) is True
