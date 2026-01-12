from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path



def test_api_sync_posts_to_scraper_control(
    client, monkeypatch, tmp_path: Path
) -> None:
    from app.core.config import settings

    captured: list[tuple[str, dict]] = []

    race_key = {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7}
    responses = {
        "/control/export/races": {
            "items": [{"race_key": race_key, "race_name": "Sample Race"}]
        },
        "/control/export/odds-snapshots": {
            "items": [
                {
                    "race_key": race_key,
                    "bet_type": "tansho",
                    "snapshot_kind": "t_minus_5m",
                    "captured_at": "2025-12-28T00:00:00+00:00",
                    "source_url": "https://example.invalid/odds",
                    "items": [{"legs": [1], "is_ordered": False, "odds_min": 2.3}],
                }
            ]
        },
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            captured.append((self.path, json.loads(body)))
            response = responses.get(self.path, {"items": []})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        monkeypatch.setattr(settings, "scraper_control_base_url", base_url)
        monkeypatch.setattr(
            settings, "scrape_sync_state_path", tmp_path / "sync_state.json"
        )

        captured.clear()
        r3 = client.post("/scrape/sync", json={})
        assert r3.status_code == 202, r3.text

        paths = [path for path, _ in captured]
        assert "/control/export/races" in paths
        assert "/control/export/odds-snapshots" in paths
    finally:
        server.shutdown()
        thread.join(timeout=1)
