from __future__ import annotations

import json
from types import SimpleNamespace

from cron import cron_run


class DummyResponse:
    def __init__(self, status: int, body: dict) -> None:
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_cron_run_skips_when_disabled(monkeypatch) -> None:
    def fake_urlopen(request, timeout=10):
        _ = (request, timeout)
        return DummyResponse(
            200,
            {"enabled": False, "baba_codes": [], "updated_at": "2025-01-01T00:00:00+00:00"},
        )

    monkeypatch.setenv("SCRAPER_CONTROL_URL", "http://localhost:8080")
    monkeypatch.setattr(cron_run.urllib.request, "urlopen", fake_urlopen)

    calls: list[list[str]] = []

    def fake_run(cmd, check=True, **_kwargs):
        _ = check
        _ = kwargs
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cron_run.subprocess, "run", fake_run)

    assert cron_run.main() == 0
    assert calls == []


def test_cron_run_executes_when_enabled(monkeypatch) -> None:
    def fake_urlopen(request, timeout=10):
        _ = (request, timeout)
        return DummyResponse(
            200,
            {"enabled": True, "baba_codes": [1, 2], "updated_at": "2025-01-01T00:00:00+00:00"},
        )

    monkeypatch.setenv("SCRAPER_CONTROL_URL", "http://localhost:8080")
    monkeypatch.setattr(cron_run.urllib.request, "urlopen", fake_urlopen)

    calls: list[list[str]] = []

    def fake_run(cmd, check=True, **_kwargs):
        _ = check
        _ = kwargs
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cron_run.subprocess, "run", fake_run)

    assert cron_run.main() == 0
    assert calls
    cmd = calls[0]
    assert "scrape" in cmd
    assert "scheduled" in cmd
    assert cmd.count("--baba-code") == 2
