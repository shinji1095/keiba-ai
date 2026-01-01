from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import ValidationError

from scraper_service.config import Settings, settings
from scraper_service.ingest.store import IngestStore
from scraper_service.http.client import HttpClient
from scraper_service.keiba.models import (
    OddsSnapshotUpsertRequest,
    PayoutUpsert,
    RaceChangeInsert,
    RaceEntryUpsert,
    RaceResultUpsert,
    RaceUpsert,
    RawFetchLogInsert,
)
from scraper_service.scheduler.runner import ScrapeRunner
from scraper_service.utils.raw_fetch_logger import RawFetchLogger
from scraper_service.utils.time import iso_now_jst, today_jst_str


@dataclass
class ScheduleState:
    enabled: bool
    baba_codes: list[int]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "baba_codes": self.baba_codes,
            "updated_at": self.updated_at,
        }


class ScheduleStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> ScheduleState:
        with self._lock:
            if not self._path.exists():
                return ScheduleState(enabled=False, baba_codes=[], updated_at=iso_now_jst())
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return ScheduleState(
                enabled=bool(data.get("enabled", False)),
                baba_codes=[int(x) for x in data.get("baba_codes", [])],
                updated_at=str(data.get("updated_at", "")) or iso_now_jst(),
            )

    def save(self, state: ScheduleState) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = state.to_dict()
            self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


@dataclass
class ScrapeRequest:
    baba_code: int
    race_date: str
    race_no: Optional[int]


class BusyError(RuntimeError):
    pass


def _build_http(cfg: Settings) -> HttpClient:
    return HttpClient(
        user_agent=cfg.user_agent,
        accept_language=cfg.accept_language,
        min_interval_sec=cfg.min_interval_sec,
        jitter_sec=cfg.jitter_sec,
        max_retries=cfg.max_retries,
        backoff_base_sec=cfg.backoff_base_sec,
        backoff_max_sec=cfg.backoff_max_sec,
    )


def _validate_batch(payload: dict[str, Any], model) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    return [model.model_validate(item).model_dump(mode="json") for item in items]


def _validate_single(payload: dict[str, Any], model) -> list[dict[str, Any]]:
    return [model.model_validate(payload).model_dump(mode="json")]


INGEST_ROUTES: dict[str, tuple[str, Any]] = {
    "/control/ingest/races": ("races", lambda p: _validate_batch(p, RaceUpsert)),
    "/control/ingest/race-entries": (
        "race_entries",
        lambda p: _validate_batch(p, RaceEntryUpsert),
    ),
    "/control/ingest/odds-snapshots": (
        "odds_snapshots",
        lambda p: _validate_single(p, OddsSnapshotUpsertRequest),
    ),
    "/control/ingest/race-results": (
        "race_results",
        lambda p: _validate_batch(p, RaceResultUpsert),
    ),
    "/control/ingest/payouts": (
        "payouts",
        lambda p: _validate_batch(p, PayoutUpsert),
    ),
    "/control/ingest/race-changes": (
        "race_changes",
        lambda p: _validate_batch(p, RaceChangeInsert),
    ),
    "/control/ingest/raw-fetch-logs": (
        "raw_fetch_logs",
        lambda p: _validate_batch(p, RawFetchLogInsert),
    ),
}


class ControlApp:
    def __init__(self, cfg: Settings, schedule_path: Path):
        self._cfg = cfg
        self._store = ScheduleStore(schedule_path)
        self._ingest = IngestStore(cfg.ingest_dir)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        self._current: Optional[Future] = None

    def get_schedule(self) -> ScheduleState:
        return self._store.load()

    def update_schedule(self, *, enabled: bool, baba_codes: list[int]) -> ScheduleState:
        state = ScheduleState(enabled=enabled, baba_codes=sorted(set(baba_codes)), updated_at=iso_now_jst())
        self._store.save(state)
        return state

    def ingest(self, *, kind: str, payloads: list[dict[str, Any]]) -> int:
        return self._ingest.append(kind=kind, payloads=payloads)

    def submit_scrape(self, req: ScrapeRequest) -> str:
        with self._lock:
            if self._current is not None and not self._current.done():
                raise BusyError("scrape already running")
            job_id = uuid.uuid4().hex
            self._current = self._executor.submit(self._run_scrape, req)
            return job_id

    def _run_scrape(self, req: ScrapeRequest) -> None:
        cfg = self._cfg
        http = _build_http(cfg)
        raw_logger = RawFetchLogger(cfg.local_log_dir / "raw_fetch_logs.csv")
        runner = ScrapeRunner(settings=cfg, http=http, raw_logger=raw_logger)
        runner.run_once(
            race_date=req.race_date,
            baba_codes=[req.baba_code],
            race_no=req.race_no,
        )


class ControlHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler, app: ControlApp):
        super().__init__(server_address, handler)
        self.app = app


class ControlHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid json") from exc

    @property
    def _app(self) -> ControlApp:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/health", "/"):
            self._send_json(200, {"status": "ok"})
            return
        if path == "/control/schedule":
            state = self._app.get_schedule()
            self._send_json(200, state.to_dict())
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError:
            self._send_json(400, {"error": "invalid json"})
            return

        if path in INGEST_ROUTES:
            kind, validator = INGEST_ROUTES[path]
            try:
                records = validator(payload)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except ValidationError as exc:
                self._send_json(
                    400, {"error": "invalid payload", "details": exc.errors()}
                )
                return
            stored = self._app.ingest(kind=kind, payloads=records)
            self._send_json(
                201, {"accepted": len(records), "stored": stored}
            )
            return

        if path == "/control/schedule":
            if "enabled" not in payload:
                self._send_json(400, {"error": "enabled is required"})
                return
            enabled = bool(payload.get("enabled"))
            raw_codes = payload.get("baba_codes", [])
            if not isinstance(raw_codes, list):
                self._send_json(400, {"error": "baba_codes must be a list"})
                return
            baba_codes: list[int] = []
            for item in raw_codes:
                try:
                    baba_codes.append(int(item))
                except (TypeError, ValueError):
                    self._send_json(400, {"error": "baba_codes must contain integers"})
                    return
            state = self._app.update_schedule(enabled=enabled, baba_codes=baba_codes)
            self._send_json(200, state.to_dict())
            return

        if path == "/control/scrape":
            if "baba_code" not in payload:
                self._send_json(400, {"error": "baba_code is required"})
                return
            try:
                baba_code = int(payload.get("baba_code"))
            except (TypeError, ValueError):
                self._send_json(400, {"error": "baba_code must be an integer"})
                return

            race_date = payload.get("race_date") or today_jst_str()
            race_no = payload.get("race_no")
            if race_no is not None:
                try:
                    race_no = int(race_no)
                except (TypeError, ValueError):
                    self._send_json(400, {"error": "race_no must be an integer"})
                    return

            try:
                job_id = self._app.submit_scrape(
                    ScrapeRequest(baba_code=baba_code, race_date=race_date, race_no=race_no)
                )
            except BusyError:
                self._send_json(409, {"error": "scrape already running"})
                return

            self._send_json(202, {"accepted": True, "job_id": job_id})
            return

        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    host = os.getenv("SCRAPER_CONTROL_HOST", "0.0.0.0")
    port = int(os.getenv("SCRAPER_CONTROL_PORT", "8080"))
    schedule_path = settings.schedule_path

    app = ControlApp(settings, schedule_path)
    server = ControlHTTPServer((host, port), ControlHandler, app)
    server.serve_forever()


if __name__ == "__main__":
    main()
