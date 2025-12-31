from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.scrape import (
    ManualScrapeTaskRequest,
    ManualScrapeTaskResponse,
    ScrapeScheduleStatus,
    ScrapeSyncRequest,
    ScrapeSyncResponse,
    ScrapeSyncStatus,
)


@dataclass
class _ScheduleState:
    enabled: bool = False
    baba_codes: Optional[list[int]] = None
    mode: Optional[str] = None
    note: Optional[str] = None
    updated_at: dt.datetime = field(default_factory=lambda: dt.datetime.utcnow())


@dataclass
class _SyncState:
    enabled: bool = False
    interval_days: int = 1
    diff_enabled: bool = False
    last_synced_at: Optional[dt.datetime] = None
    next_scheduled_at: Optional[dt.datetime] = None
    last_fingerprint: Optional[str] = None


_GLOBAL_SCHEDULE = _ScheduleState()
_GLOBAL_SYNC = _SyncState()


class ScrapeControlService:
    def __init__(self) -> None:
        self._schedule = _GLOBAL_SCHEDULE
        self._sync = _GLOBAL_SYNC

    def get_schedule(self) -> ScrapeScheduleStatus:
        return ScrapeScheduleStatus(
            enabled=self._schedule.enabled,
            baba_codes=(
                list(self._schedule.baba_codes)
                if self._schedule.baba_codes is not None
                else None
            ),
            mode=self._schedule.mode,
            updated_at=self._schedule.updated_at,
            note=self._schedule.note,
        )

    def request_manual_task(
        self, payload: ManualScrapeTaskRequest
    ) -> ManualScrapeTaskResponse:
        now = dt.datetime.utcnow()
        task_id = uuid.uuid4().hex
        return ManualScrapeTaskResponse(
            task_id=task_id, status="accepted", accepted_at=now
        )

    def trigger_sync(
        self, payload: ScrapeSyncRequest | None
    ) -> ScrapeSyncResponse:
        now = dt.datetime.utcnow()
        sync_id = uuid.uuid4().hex
        self._sync.last_synced_at = now
        if self._sync.enabled:
            self._sync.next_scheduled_at = now + dt.timedelta(
                days=self._sync.interval_days
            )
        else:
            self._sync.next_scheduled_at = None
        return ScrapeSyncResponse(
            sync_id=sync_id, status="accepted", started_at=now
        )

    def get_sync_status(self) -> ScrapeSyncStatus:
        return ScrapeSyncStatus(
            enabled=self._sync.enabled,
            interval_days=self._sync.interval_days,
            diff_enabled=self._sync.diff_enabled,
            last_synced_at=self._sync.last_synced_at,
            next_scheduled_at=self._sync.next_scheduled_at,
            last_fingerprint=self._sync.last_fingerprint,
        )
