import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def sample(at=None, sequence=0, **values):
    return {
        "host_id": "test-pc",
        "hostname": "test-pc",
        "scope": "host",
        "boot_id": "boot1",
        "sequence": sequence,
        "sampled_at": (at or datetime.now(UTC)).isoformat(),
        "uptime_sec": 100,
        "cpu_count": 2,
        "cpu_percent": 40,
        "cpu_per_core": [30, 50],
        "memory_total_bytes": 1000,
        "memory_available_bytes": 600,
        "memory_percent": 40,
        "swap_total_bytes": 0,
        "swap_used_bytes": 0,
        "disks": [
            {
                "path": "/",
                "label": "OS",
                "total_bytes": 1000,
                "used_bytes": 500,
                "available_bytes": 500,
                "percent": 50,
            }
        ],
        **values,
    }


@pytest.fixture
def monitor_db(client, tmp_path):
    from app.db.base import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'metrics.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_ingest_deduplicates_and_does_not_rewind_latest(monitor_db):
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    service = MonitoringService(monitor_db)
    now = datetime.now(UTC).replace(second=20, microsecond=0)
    newer = MetricSample(**sample(now, 2, cpu_percent=80))
    assert service.ingest(newer, now)["accepted"]
    assert service.ingest(newer, now)["duplicate"]
    service.ingest(
        MetricSample(**sample(now - timedelta(seconds=10), 1, cpu_percent=20)),
        now,
    )
    assert service.latest(now=now)["sample"]["cpu_percent"] == 80
    points = service.history(24, now=now)["points"]
    assert points[0]["values"]["cpu_percent"] == 50
    assert points[0]["max_values"]["cpu_percent"] == 80
    assert points[0]["sample_counts"]["cpu_percent"] == 2


def test_missing_cpu_not_averaged_as_zero_and_freshness(monitor_db):
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    service = MonitoringService(monitor_db)
    now = datetime.now(UTC).replace(second=20, microsecond=0)
    service.ingest(
        MetricSample(
            **sample(now - timedelta(seconds=10), 0, cpu_percent=None)
        ),
        now,
    )
    service.ingest(MetricSample(**sample(now, 1, cpu_percent=80)), now)
    history = service.history(24, now=now)
    assert history["points"][0]["values"]["cpu_percent"] == 80
    assert service.latest(now=now + timedelta(seconds=30))["status"] == "stale"
    assert (
        service.latest(now=now + timedelta(seconds=60))["status"]
        == "unavailable"
    )


def test_sustained_warning_gap_and_recovery(monitor_db):
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    service = MonitoringService(monitor_db)
    base = datetime.now(UTC) - timedelta(minutes=12)
    seq = 0
    for seconds in [0, 10, 20, *range(120, 420, 10)]:
        at = base + timedelta(seconds=seconds)
        service.ingest(MetricSample(**sample(at, seq, cpu_percent=85)), at)
        seq += 1
    assert not service.events(active_only=True)["items"]
    at = base + timedelta(seconds=420)
    service.ingest(MetricSample(**sample(at, seq, cpu_percent=85)), at)
    assert len(service.events(active_only=True)["items"]) == 1
    for seconds in range(430, 501, 10):
        seq += 1
        at = base + timedelta(seconds=seconds)
        service.ingest(MetricSample(**sample(at, seq, cpu_percent=20)), at)
    assert not service.events(active_only=True)["items"]
    assert service.events()["items"][0]["resolved_at"]


def test_disk_alert_immediate_and_null_cpu_resets_candidate(monitor_db):
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    service = MonitoringService(monitor_db)
    payload = sample()
    payload["disks"][0]["percent"] = 95
    service.ingest(MetricSample(**payload))
    assert service.latest()["status"] == "critical"
    assert len(service.events(active_only=True)["items"]) == 2


def test_retention_keeps_rollups(monitor_db):
    from app.db.models.monitoring import MetricMinute, SystemMetric
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    service = MonitoringService(monitor_db)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    old = now - timedelta(days=2)
    service.ingest(MetricSample(**sample(old)), old)
    service.ingest(MetricSample(**sample(now, 1)), now)
    assert len(monitor_db.scalars(select(SystemMetric)).all()) == 1
    assert len(monitor_db.scalars(select(MetricMinute)).all()) == 2
    assert len(service.history(168, now=now)["points"]) == 2


def _user_headers(client):
    login = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def _service_headers(client, scopes):
    created = client.post(
        "/admin/oauth-clients",
        headers=_user_headers(client),
        json={"name": "monitor-" + uuid.uuid4().hex, "scopes": scopes},
    ).json()["client"]
    response = client.post(
        "/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": created["client_id"],
            "client_secret": created["client_secret"],
        },
    )
    return {
        "Authorization": "Bearer " + response.json()["access_token"]
    }, created


def test_monitoring_authentication_and_ingest_roundtrip(client):
    for path in (
        "/system/metrics",
        "/system/metrics/history",
        "/system/events",
        "/scrape/status",
        "/scrape/jobs",
        "/scrape/jobs/abc",
    ):
        assert client.get(path).status_code == 401
    assert client.post("/system/metrics", json=sample()).status_code == 401
    reader, _ = _service_headers(client, ["monitor:read"])
    assert (
        client.post(
            "/system/metrics", headers=reader, json=sample()
        ).status_code
        == 403
    )
    user = _user_headers(client)
    assert (
        client.post("/system/metrics", headers=user, json=sample()).status_code
        == 403
    )
    writer, created = _service_headers(client, ["monitor:write"])
    payload = sample(host_id="api-" + uuid.uuid4().hex)
    assert client.post("/system/metrics", headers=writer, json=payload).json()[
        "accepted"
    ]
    assert client.get("/system/metrics", headers=reader).status_code == 200
    assert client.get("/system/metrics", headers=writer).status_code == 403
    assert (
        client.get("/system/metrics", headers=user).json()["sample"]["host_id"]
        == payload["host_id"]
    )
    assert client.get(
        "/system/metrics/history?hours=168", headers=user
    ).json()["points"]
    assert (
        client.get(
            "/system/metrics/history?hours=999", headers=user
        ).status_code
        == 400
    )
    client.delete("/admin/oauth-clients/" + created["client_id"], headers=user)
    assert (
        client.post(
            "/system/metrics", headers=writer, json=sample()
        ).status_code
        == 403
    )


def test_invalid_future_and_capacity_rejected(client):
    writer, _ = _service_headers(client, ["monitor:write"])
    for payload in (
        sample(datetime.now(UTC) + timedelta(minutes=5)),
        sample(memory_available_bytes=1001),
        sample(cpu_percent=101),
        sample(cpu_per_core=[-1]),
    ):
        assert (
            client.post(
                "/system/metrics", headers=writer, json=payload
            ).status_code
            == 400
        )


def test_scraper_failure_returns_partial_status_with_sync(client, monkeypatch):
    import app.api.routes.monitoring as routes

    def broken():
        raise OSError("offline")

    monkeypatch.setattr(routes, "control_client", broken)
    response = client.get("/scrape/status", headers=_user_headers(client))
    assert response.status_code == 200
    assert response.json()["connection"] == "unavailable"
    assert "sync" in response.json()


def test_free_capacity_warning_and_collection_errors(monitor_db, monkeypatch):
    from app.core.config import settings
    from app.schemas.monitoring import MetricSample
    from app.services.monitoring_service import MonitoringService

    monkeypatch.setattr(settings, "monitor_disk_min_free_bytes", 600)
    service = MonitoringService(monitor_db)
    service.ingest(MetricSample(**sample()))
    events = service.events(active_only=True)["items"]
    assert len(events) == 1
    assert "600 bytes 未満" in events[0]["message"]
    monkeypatch.setattr(settings, "monitor_disk_min_free_bytes", 0)
    service.ingest(
        MetricSample(
            **sample(
                sequence=1,
                host_id="missing-disk",
                disks=[],
                errors=["ディスク取得失敗"],
            )
        )
    )
    assert service.latest()["status"] == "warning"
