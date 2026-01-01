from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def _parse_datetime(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class SyncEntry:
    fingerprint: str
    updated_at: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "fingerprint": self.fingerprint,
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, str]) -> Optional["SyncEntry"]:
        fingerprint = data.get("fingerprint")
        updated_at = data.get("updated_at")
        if not fingerprint or not updated_at:
            return None
        try:
            ts = datetime.fromisoformat(updated_at)
        except ValueError:
            return None
        return SyncEntry(fingerprint=fingerprint, updated_at=ts)


@dataclass
class SyncSchedule:
    enabled: bool = False
    interval_days: int = 2
    diff_enabled: bool = True
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "interval_days": self.interval_days,
            "diff_enabled": self.diff_enabled,
            "updated_at": self.updated_at.isoformat()
            if self.updated_at
            else None,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "SyncSchedule":
        enabled = bool(data.get("enabled", False))
        interval_raw = data.get("interval_days", 2)
        try:
            interval_days = int(interval_raw)
        except (TypeError, ValueError):
            interval_days = 2
        if interval_days < 1:
            interval_days = 1

        diff_raw = data.get("diff_enabled", True)
        diff_enabled = bool(diff_raw)
        updated_at = _parse_datetime(data.get("updated_at"))
        return SyncSchedule(
            enabled=enabled,
            interval_days=interval_days,
            diff_enabled=diff_enabled,
            updated_at=updated_at,
        )


@dataclass
class SyncState:
    last_synced_at: Optional[datetime] = None
    last_fingerprint: Optional[str] = None
    items: dict[str, SyncEntry] = field(default_factory=dict)
    schedule: SyncSchedule = field(default_factory=SyncSchedule)
    last_attempted_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_trigger: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "last_synced_at": self.last_synced_at.isoformat()
            if self.last_synced_at
            else None,
            "last_fingerprint": self.last_fingerprint,
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "schedule": self.schedule.to_dict(),
            "last_attempted_at": self.last_attempted_at.isoformat()
            if self.last_attempted_at
            else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_trigger": self.last_trigger,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "SyncState":
        last_synced_at = _parse_datetime(data.get("last_synced_at"))

        last_fingerprint = data.get("last_fingerprint")
        if not isinstance(last_fingerprint, str):
            last_fingerprint = None

        items: dict[str, SyncEntry] = {}
        raw_items = data.get("items")
        if isinstance(raw_items, dict):
            for k, v in raw_items.items():
                if not isinstance(k, str) or not isinstance(v, dict):
                    continue
                entry = SyncEntry.from_dict(v)
                if entry is not None:
                    items[k] = entry

        schedule_raw = data.get("schedule")
        if isinstance(schedule_raw, dict):
            schedule = SyncSchedule.from_dict(schedule_raw)
        else:
            schedule = SyncSchedule()

        last_attempted_at = _parse_datetime(data.get("last_attempted_at"))
        last_status = data.get("last_status")
        if not isinstance(last_status, str):
            last_status = None
        last_error = data.get("last_error")
        if not isinstance(last_error, str):
            last_error = None
        last_trigger = data.get("last_trigger")
        if not isinstance(last_trigger, str):
            last_trigger = None

        return SyncState(
            last_synced_at=last_synced_at,
            last_fingerprint=last_fingerprint,
            items=items,
            schedule=schedule,
            last_attempted_at=last_attempted_at,
            last_status=last_status,
            last_error=last_error,
            last_trigger=last_trigger,
        )


class SyncStateStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> SyncState:
        with self._lock:
            if not self._path.exists():
                return SyncState()
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return SyncState()
            return SyncState.from_dict(data)

    def save(self, state: SyncState) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(state.to_dict(), ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
