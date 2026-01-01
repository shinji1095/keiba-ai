from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from cron import cron_sync


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


def test_cron_sync_requires_base_url(monkeypatch) -> None:
    monkeypatch.delenv("SCRAPE_SYNC_API_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    assert cron_sync.main() == 2


def test_cron_sync_success(monkeypatch) -> None:
    calls: list[str] = []

    def fake_urlopen(request, timeout=10):
        _ = timeout
        calls.append(request.full_url)
        return DummyResponse(202, {"status": "accepted"})

    monkeypatch.setenv("SCRAPE_SYNC_API_URL", "http://localhost:9999")
    monkeypatch.setattr(cron_sync.urllib.request, "urlopen", fake_urlopen)

    assert cron_sync.main() == 0
    assert calls == ["http://localhost:9999/scrape/sync/scheduled"]


def test_cron_sync_failure(monkeypatch) -> None:
    def fake_urlopen(request, timeout=10):
        _ = (request, timeout)
        return DummyResponse(500, {"error": "fail"})

    monkeypatch.setenv("SCRAPE_SYNC_API_URL", "http://localhost:9999")
    monkeypatch.setattr(cron_sync.urllib.request, "urlopen", fake_urlopen)

    assert cron_sync.main() == 1


def test_cron_sync_integration(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            captured["path"] = self.path
            captured["body"] = body
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        monkeypatch.setenv("SCRAPE_SYNC_API_URL", base_url)
        assert cron_sync.main() == 0
        assert captured.get("path") == "/scrape/sync/scheduled"
        assert "reason" in json.loads(captured.get("body", "{}"))
    finally:
        server.shutdown()
        thread.join(timeout=1)
