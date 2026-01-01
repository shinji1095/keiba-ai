from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from app.core.config import settings


def test_api_sync_posts_to_scraper_control(
    client, monkeypatch, tmp_path: Path
) -> None:
    captured: list[tuple[str, dict]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            captured.append((self.path, json.loads(body)))
            self.send_response(201)
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
        monkeypatch.setattr(settings, "scraper_forward_enabled", True)
        monkeypatch.setattr(settings, "scraper_control_base_url", base_url)
        monkeypatch.setattr(
            settings, "scrape_sync_state_path", tmp_path / "sync_state.json"
        )

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

        captured.clear()
        r3 = client.post("/scrape/sync", json={"event_id": str(uuid.uuid4())})
        assert r3.status_code == 202, r3.text

        paths = [path for path, _ in captured]
        assert "/control/ingest/races" in paths
        assert "/control/ingest/odds-snapshots" in paths
    finally:
        server.shutdown()
        thread.join(timeout=1)
