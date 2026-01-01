from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_jst_date(dt: datetime) -> date:
    return _ensure_utc(dt).astimezone(JST).date()


def should_run_sync(
    *,
    last_synced_at: Optional[datetime],
    interval_days: int,
    now: Optional[datetime] = None,
) -> bool:
    if interval_days < 1:
        raise ValueError("interval_days must be >= 1")
    if last_synced_at is None:
        return True
    if now is None:
        now = datetime.now(timezone.utc)
    delta_days = (_to_jst_date(now) - _to_jst_date(last_synced_at)).days
    return delta_days >= interval_days


def next_scheduled_at(
    *,
    last_synced_at: Optional[datetime],
    interval_days: int,
) -> Optional[datetime]:
    if interval_days < 1:
        raise ValueError("interval_days must be >= 1")
    if last_synced_at is None:
        return None
    last_date = _to_jst_date(last_synced_at)
    next_date = last_date + timedelta(days=interval_days)
    next_jst = datetime.combine(next_date, time(0, 0), tzinfo=JST)
    return next_jst.astimezone(timezone.utc)
