from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from scraper_service.utils.time import JST


def should_sync_interval(
    *,
    last_synced_at: Optional[datetime],
    interval_days: int = 2,
    now: Optional[datetime] = None,
) -> bool:
    if interval_days < 1:
        raise ValueError("interval_days must be >= 1")

    if now is None:
        now = datetime.now(timezone.utc).astimezone(JST)
    else:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        now = now.astimezone(JST)

    if last_synced_at is None:
        return True
    if last_synced_at.tzinfo is None:
        raise ValueError("last_synced_at must be timezone-aware")

    delta_days = (now.date() - last_synced_at.astimezone(JST).date()).days
    return delta_days >= interval_days
