from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/health", "/"):
            self.send_error(404)
            return

        payload = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    host = os.getenv("SCRAPER_HEALTH_HOST", "0.0.0.0")
    port = int(os.getenv("SCRAPER_HEALTH_PORT", "8081"))
    server = ThreadingHTTPServer((host, port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
