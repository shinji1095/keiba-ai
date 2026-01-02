from __future__ import annotations

import datetime as dt
import uuid
from datetime import datetime, timezone

from app.core.errors import AppError
from app.core.config import settings
from app.schemas.scrape import (
    ManualScrapeTaskRequest,
    ManualScrapeTaskResponse,
    ScrapeScheduleStatus,
    ScrapeScheduleUpdateRequest,
    ScrapeSyncRequest,
    ScrapeSyncResponse,
    ScrapeSyncScheduleRequest,
    ScrapeSyncStatus,
)
from app.services.scraper_control_client import ScraperControlClient
from app.services.scrape_sync_policy import next_scheduled_at, should_run_sync
from app.services.scrape_sync_service import ScrapeSyncService
from app.services.scrape_sync_state import SyncStateStore

class ScrapeControlService:
    def __init__(self, *, db=None) -> None:
        self._db = db
        self._state_store = SyncStateStore(settings.scrape_sync_state_path)

    @staticmethod
    def _parse_schedule_payload(payload: dict) -> ScrapeScheduleStatus:
        enabled = bool(payload.get("enabled", False))

        raw_codes = payload.get("baba_codes")
        if raw_codes is None:
            baba_codes = None
        elif not isinstance(raw_codes, list):
            raise AppError.bad_gateway(
                "invalid schedule response",
                details={"field": "baba_codes"},
            )
        else:
            try:
                baba_codes = [int(x) for x in raw_codes]
            except (TypeError, ValueError) as exc:
                raise AppError.bad_gateway(
                    "invalid schedule response",
                    details={"field": "baba_codes"},
                ) from exc

        updated_at_raw = payload.get("updated_at")
        if not isinstance(updated_at_raw, str) or not updated_at_raw:
            raise AppError.bad_gateway(
                "invalid schedule response",
                details={"field": "updated_at"},
            )
        try:
            updated_at = dt.datetime.fromisoformat(updated_at_raw)
        except ValueError as exc:
            raise AppError.bad_gateway(
                "invalid schedule response",
                details={"field": "updated_at"},
            ) from exc

        raw_kinds = payload.get("snapshot_kinds")
        if raw_kinds is None:
            snapshot_kinds = None
        elif not isinstance(raw_kinds, list):
            raise AppError.bad_gateway(
                "invalid schedule response",
                details={"field": "snapshot_kinds"},
            )
        else:
            snapshot_kinds = [str(x) for x in raw_kinds if str(x).strip()]

        raw_prefetch_days = payload.get("prefetch_days")
        if raw_prefetch_days is None:
            prefetch_days = None
        else:
            try:
                prefetch_days = int(raw_prefetch_days)
            except (TypeError, ValueError) as exc:
                raise AppError.bad_gateway(
                    "invalid schedule response",
                    details={"field": "prefetch_days"},
                ) from exc

        return ScrapeScheduleStatus(
            enabled=enabled,
            baba_codes=baba_codes,
            snapshot_kinds=snapshot_kinds,
            prefetch_days=prefetch_days,
            mode=None,
            updated_at=updated_at,
            note=None,
        )

    def get_schedule(self) -> ScrapeScheduleStatus:
        client = ScraperControlClient.from_settings()
        payload = client.get_json("/control/schedule")
        return self._parse_schedule_payload(payload)

    def update_schedule(
        self, payload: ScrapeScheduleUpdateRequest
    ) -> ScrapeScheduleStatus:
        client = ScraperControlClient.from_settings()
        request_payload: dict[str, object] = {"enabled": payload.enabled}
        if payload.baba_codes is not None:
            request_payload["baba_codes"] = payload.baba_codes
        if payload.snapshot_kinds is not None:
            request_payload["snapshot_kinds"] = payload.snapshot_kinds
        if payload.prefetch_days is not None:
            request_payload["prefetch_days"] = payload.prefetch_days
        response = client.post_json("/control/schedule", request_payload)
        return self._parse_schedule_payload(response)

    def request_manual_task(
        self, payload: ManualScrapeTaskRequest
    ) -> ManualScrapeTaskResponse:
        client = ScraperControlClient.from_settings()
        request_payload: dict[str, object] = {
            "baba_code": payload.baba_code,
        }
        if payload.race_date is not None:
            request_payload["race_date"] = payload.race_date.isoformat()
        if payload.race_no is not None:
            request_payload["race_no"] = payload.race_no

        response = client.post_json("/control/scrape", request_payload)
        job_id = response.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise AppError.bad_gateway(
                "invalid scrape response",
                details={"field": "job_id"},
            )

        now = dt.datetime.utcnow()
        return ManualScrapeTaskResponse(
            task_id=job_id, status="accepted", accepted_at=now
        )

    def trigger_sync(
        self, payload: ScrapeSyncRequest | None
    ) -> ScrapeSyncResponse:
        if self._db is None:
            raise AppError.internal("db session is required for sync")
        _ = payload
        state = self._state_store.load()
        svc = ScrapeSyncService(
            self._db,
            self._state_store,
            diff_enabled=state.schedule.diff_enabled,
        )
        result = svc.run_sync(trigger="manual")
        return ScrapeSyncResponse(
            sync_id=result.sync_id,
            status="accepted",
            started_at=result.started_at,
        )

    def trigger_scheduled_sync(
        self, payload: ScrapeSyncRequest | None
    ) -> ScrapeSyncResponse:
        if self._db is None:
            raise AppError.internal("db session is required for sync")
        _ = payload
        state = self._state_store.load()
        schedule = state.schedule
        now = datetime.now(timezone.utc)

        if not schedule.enabled:
            state.last_attempted_at = now
            state.last_status = "skipped"
            state.last_error = "schedule disabled"
            state.last_trigger = "scheduled"
            self._state_store.save(state)
            return ScrapeSyncResponse(
                sync_id=uuid.uuid4().hex,
                status="skipped",
                started_at=now,
            )

        if not should_run_sync(
            last_synced_at=state.last_synced_at,
            interval_days=schedule.interval_days,
            now=now,
        ):
            state.last_attempted_at = now
            state.last_status = "skipped"
            state.last_error = "not due"
            state.last_trigger = "scheduled"
            self._state_store.save(state)
            return ScrapeSyncResponse(
                sync_id=uuid.uuid4().hex,
                status="skipped",
                started_at=now,
            )

        svc = ScrapeSyncService(
            self._db,
            self._state_store,
            diff_enabled=schedule.diff_enabled,
        )
        result = svc.run_sync(trigger="scheduled")
        return ScrapeSyncResponse(
            sync_id=result.sync_id,
            status="accepted",
            started_at=result.started_at,
        )

    def update_sync_schedule(
        self, payload: ScrapeSyncScheduleRequest
    ) -> ScrapeSyncStatus:
        state = self._state_store.load()
        schedule = state.schedule
        schedule.enabled = payload.enabled
        schedule.interval_days = payload.interval_days
        if payload.diff_enabled is not None:
            schedule.diff_enabled = payload.diff_enabled
        schedule.updated_at = datetime.now(timezone.utc)
        state.schedule = schedule
        self._state_store.save(state)
        return self.get_sync_status()

    def get_sync_status(self) -> ScrapeSyncStatus:
        state = self._state_store.load()
        schedule = state.schedule
        last_synced_at = state.last_synced_at
        next_scheduled = None
        if schedule.enabled:
            try:
                next_scheduled = next_scheduled_at(
                    last_synced_at=last_synced_at,
                    interval_days=schedule.interval_days,
                )
            except ValueError:
                next_scheduled = None
        return ScrapeSyncStatus(
            enabled=schedule.enabled,
            interval_days=schedule.interval_days,
            diff_enabled=schedule.diff_enabled,
            last_synced_at=last_synced_at,
            next_scheduled_at=next_scheduled,
            last_fingerprint=state.last_fingerprint,
            last_attempted_at=state.last_attempted_at,
            last_status=state.last_status,
            last_error=state.last_error,
            last_trigger=state.last_trigger,
            schedule_updated_at=schedule.updated_at,
        )
