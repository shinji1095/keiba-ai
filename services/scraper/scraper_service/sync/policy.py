from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from scraper_service.utils.time import JST


def should_sync_daily(*, last_synced_at: Optional[datetime], now: Optional[datetime] = None) -> bool:
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

    return last_synced_at.astimezone(JST).date() < now.date()
