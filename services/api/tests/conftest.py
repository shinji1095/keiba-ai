from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture()
def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    # IMPORTANT:
    # env vars must be set before importing app modules because settings/engine are created at import time.
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("REDIS_ENABLED", "false")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", '["http://localhost:5173"]')

    from app.main import create_app  # local import for test isolation

    app = create_app()
    with TestClient(app) as c:
        yield c


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
