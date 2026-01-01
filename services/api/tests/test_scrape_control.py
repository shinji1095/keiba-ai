from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
import app.services.scrape_control_service as control_service
import app.services.scrape_sync_service as sync_service


class DummyControlClient:
    def __init__(self, schedule_payload: dict, job_id: str = "job123") -> None:
        self.schedule_payload = schedule_payload
        self.job_id = job_id
        self.calls: list[tuple[str, dict]] = []

    def get_json(self, path: str) -> dict:
        assert path == "/control/schedule"
        return self.schedule_payload

    def post_json(self, path: str, payload: dict) -> dict:
        self.calls.append((path, payload))
        if path == "/control/schedule":
            return self.schedule_payload
        return {"job_id": self.job_id}


class DummyIngestClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []

    def post(self, path: str, payload: dict) -> None:
        self.posts.append((path, payload))


def _patch_control_client(monkeypatch, dummy: DummyControlClient) -> None:
    monkeypatch.setattr(
        control_service.ScraperControlClient,
        "from_settings",
        classmethod(lambda cls: dummy),
    )


def _patch_sync_client(monkeypatch, dummy: DummyIngestClient) -> None:
    monkeypatch.setattr(
        sync_service.ScraperIngestClient,
        "from_settings",
        classmethod(lambda cls: dummy),
    )


def test_manual_scrape_task_accepts_minimum_payload(
    client, monkeypatch
) -> None:
    dummy = DummyControlClient(
        schedule_payload={
            "enabled": False,
            "baba_codes": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _patch_control_client(monkeypatch, dummy)

    r = client.post("/scrape/manual-tasks", json={"baba_code": 18})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["task_id"] == "job123"

    assert dummy.calls
    path, payload = dummy.calls[0]
    assert path == "/control/scrape"
    assert payload == {"baba_code": 18}


def test_scrape_schedule_status(client, monkeypatch) -> None:
    updated_at = datetime.now(timezone.utc).isoformat()
    dummy = DummyControlClient(
        schedule_payload={
            "enabled": True,
            "baba_codes": [1, 2],
            "updated_at": updated_at,
        }
    )
    _patch_control_client(monkeypatch, dummy)

    r = client.get("/scrape/schedule")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["baba_codes"] == [1, 2]
    assert body["updated_at"].startswith(updated_at[:19])


def test_scrape_schedule_update(client, monkeypatch) -> None:
    updated_at = datetime.now(timezone.utc).isoformat()
    dummy = DummyControlClient(
        schedule_payload={
            "enabled": True,
            "baba_codes": [3, 4],
            "updated_at": updated_at,
        }
    )
    _patch_control_client(monkeypatch, dummy)

    r = client.post(
        "/scrape/schedule",
        json={"enabled": True, "baba_codes": [3, 4]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["baba_codes"] == [3, 4]

    assert dummy.calls
    path, payload = dummy.calls[0]
    assert path == "/control/schedule"
    assert payload == {"enabled": True, "baba_codes": [3, 4]}


def test_scrape_sync_creates_state(
    client, monkeypatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(settings, "scrape_sync_state_path", state_path)
    dummy = DummyIngestClient()
    _patch_sync_client(monkeypatch, dummy)

    r = client.post(
        "/scrape/sync",
        json={"event_id": str(uuid.uuid4()), "reason": "test"},
    )
    assert r.status_code == 202, r.text
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["last_synced_at"]


def test_scrape_sync_status_reads_state(
    client, monkeypatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "sync_state.json"
    payload = {
        "last_synced_at": "2025-01-01T00:00:00+00:00",
        "last_fingerprint": "abc123",
        "schedule": {
            "enabled": True,
            "interval_days": 3,
            "diff_enabled": True,
            "updated_at": "2025-01-01T01:00:00+00:00",
        },
        "last_status": "success",
        "last_trigger": "manual",
        "items": {},
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(settings, "scrape_sync_state_path", state_path)

    r = client.get("/scrape/sync/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["diff_enabled"] is True
    assert body["interval_days"] == 3
    assert body["last_fingerprint"] == "abc123"
    assert body["last_status"] == "success"
    assert body["last_trigger"] == "manual"


def test_scrape_sync_sends_payloads(
    client, monkeypatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(settings, "scrape_sync_state_path", state_path)
    dummy = DummyIngestClient()
    _patch_sync_client(monkeypatch, dummy)

    race_key = {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7}
    r1 = client.post(
        "/scrape/races",
        json={
            "event_id": str(uuid.uuid4()),
            "items": [{"race_key": race_key, "race_name": "Sample Race"}],
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/scrape/odds-snapshots",
        json={
            "event_id": str(uuid.uuid4()),
            "race_key": race_key,
            "bet_type": "tansho",
            "snapshot_kind": "t_minus_5m",
            "captured_at": "2025-12-28T00:00:00+00:00",
            "source_url": "https://example.invalid/odds",
            "items": [{"legs": [1], "is_ordered": False, "odds_min": 2.3}],
        },
    )
    assert r2.status_code == 201, r2.text

    r3 = client.post("/scrape/sync", json={"event_id": str(uuid.uuid4())})
    assert r3.status_code == 202, r3.text

    paths = [path for path, _ in dummy.posts]
    assert "/control/ingest/races" in paths
    assert "/control/ingest/odds-snapshots" in paths


def test_scrape_sync_schedule_update(
    client, monkeypatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "sync_state.json"
    monkeypatch.setattr(settings, "scrape_sync_state_path", state_path)

    r = client.post(
        "/scrape/sync/schedule",
        json={"enabled": True, "interval_days": 3},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["interval_days"] == 3
    assert body["schedule_updated_at"]


def test_scrape_sync_scheduled_skip_when_not_due(
    client, monkeypatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "sync_state.json"
    payload = {
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "schedule": {
            "enabled": True,
            "interval_days": 2,
            "diff_enabled": True,
        },
        "items": {},
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(settings, "scrape_sync_state_path", state_path)

    r = client.post("/scrape/sync/scheduled", json={"reason": "cron"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "skipped"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["last_status"] == "skipped"
    assert state["last_error"] == "not due"
