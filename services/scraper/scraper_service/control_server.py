from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import datetime as dt
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from scraper_service.config import Settings, settings
from scraper_service.ingest.store import IngestStore
from scraper_service.http.client import HttpClient
from scraper_service.scheduler.runner import ScrapeRunner
from scraper_service.utils.time import iso_now_jst, today_jst_str


@dataclass
class ScheduleState:
    enabled: bool
    baba_codes: list[int]
    snapshot_kinds: list[str]
    prefetch_days: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "baba_codes": self.baba_codes,
            "snapshot_kinds": self.snapshot_kinds,
            "prefetch_days": self.prefetch_days,
            "updated_at": self.updated_at,
        }


class ScheduleStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def load(self) -> ScheduleState:
        with self._lock:
            if not self._path.exists():
                return ScheduleState(
                    enabled=False,
                    baba_codes=[],
                    snapshot_kinds=["t_minus_60m", "t_minus_30m", "final"],
                    prefetch_days=7,
                    updated_at=iso_now_jst(),
                )
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return ScheduleState(
                enabled=bool(data.get("enabled", False)),
                baba_codes=[int(x) for x in data.get("baba_codes", [])],
                snapshot_kinds=[
                    str(x) for x in (data.get("snapshot_kinds") or ["final"])
                ],
                prefetch_days=int(data.get("prefetch_days") or 7),
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
        min_interval_sec=cfg.manual_min_interval_sec,
        jitter_sec=cfg.manual_jitter_sec,
        max_retries=cfg.max_retries,
        backoff_base_sec=cfg.backoff_base_sec,
        backoff_max_sec=cfg.backoff_max_sec,
    )


def _parse_export_filter(
    payload: dict[str, Any],
) -> tuple[Optional[str], Optional[int], Optional[int]]:
    race_date = payload.get("race_date")
    if race_date is not None and (not isinstance(race_date, str) or not race_date):
        raise ValueError("race_date must be a non-empty string")

    baba_code = payload.get("baba_code")
    if baba_code is not None:
        try:
            baba_code = int(baba_code)
        except (TypeError, ValueError) as exc:
            raise ValueError("baba_code must be an integer") from exc

    race_no = payload.get("race_no")
    if race_no is not None:
        try:
            race_no = int(race_no)
        except (TypeError, ValueError) as exc:
            raise ValueError("race_no must be an integer") from exc

    return race_date, baba_code, race_no


EXPORT_ROUTES: dict[str, str] = {
    "/control/export/races": "races",
    "/control/export/race-entries": "race_entries",
    "/control/export/race-cards": "race_cards",
    "/control/export/odds-snapshots": "odds_snapshots",
    "/control/export/race-results": "race_results",
    "/control/export/payouts": "payouts",
    "/control/export/race-changes": "race_changes",
}


class ControlApp:
    def __init__(self, cfg: Settings, schedule_path: Path):
        self._cfg = cfg
        self._store = ScheduleStore(schedule_path)
        self._sync_store = IngestStore(cfg.ingest_dir)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        self._current: Optional[Future] = None

    def get_schedule(self) -> ScheduleState:
        return self._store.load()

    def update_schedule(
        self,
        *,
        enabled: bool,
        baba_codes: list[int],
        snapshot_kinds: list[str] | None = None,
        prefetch_days: int | None = None,
    ) -> ScheduleState:
        prev = self._store.load()
        state = ScheduleState(
            enabled=enabled,
            baba_codes=sorted(set(baba_codes)),
            snapshot_kinds=snapshot_kinds if snapshot_kinds is not None else prev.snapshot_kinds,
            prefetch_days=prefetch_days if prefetch_days is not None else prev.prefetch_days,
            updated_at=iso_now_jst(),
        )
        self._store.save(state)
        return state

    def export(
        self,
        *,
        kind: str,
        race_date: Optional[str],
        baba_code: Optional[int],
        race_no: Optional[int],
    ) -> list[dict[str, Any]]:
        return self._sync_store.list_latest(
            kind=kind, race_date=race_date, baba_code=baba_code, race_no=race_no
        )

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
        runner = ScrapeRunner(settings=cfg, http=http, sync_store=self._sync_store)
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

    def _read_scrape_plan(self, race_date: str) -> dict[str, Any] | None:
        try:
            dt.date.fromisoformat(race_date)
        except ValueError:
            raise ValueError("race_date must be YYYY-MM-DD") from None

        plan_path = self._app._cfg.control_dir / f"scrape_plan_{race_date}.json"
        if not plan_path.exists():
            return None
        return json.loads(plan_path.read_text(encoding="utf-8"))

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
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/health", "/"):
            self._send_json(200, {"status": "ok"})
            return
        if path == "/control/schedule":
            state = self._app.get_schedule()
            self._send_json(200, state.to_dict())
            return
        if path == "/control/plan":
            qs = parse_qs(parsed.query)
            race_date = (qs.get("race_date") or [None])[0]
            if race_date is None:
                race_date = today_jst_str()
            if not isinstance(race_date, str) or not race_date:
                self._send_json(400, {"error": "race_date must be a non-empty string"})
                return
            try:
                plan = self._read_scrape_plan(race_date)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            if plan is None:
                self._send_json(404, {"error": "scrape plan not found"})
                return
            self._send_json(200, plan)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError:
            self._send_json(400, {"error": "invalid json"})
            return

        if path in EXPORT_ROUTES:
            kind = EXPORT_ROUTES[path]
            try:
                race_date, baba_code, race_no = _parse_export_filter(payload)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            items = self._app.export(
                kind=kind,
                race_date=race_date,
                baba_code=baba_code,
                race_no=race_no,
            )
            self._send_json(200, {"items": items})
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
            # Optional scheduled odds snapshot kinds (default: ["final"])
            snapshot_kinds: list[str] | None = None
            if "snapshot_kinds" in payload:
                raw_kinds = payload.get("snapshot_kinds")
                if not isinstance(raw_kinds, list):
                    self._send_json(400, {"error": "snapshot_kinds must be a list"})
                    return
                snapshot_kinds = []
                for it in raw_kinds:
                    if not isinstance(it, str) or not it.strip():
                        self._send_json(
                            400, {"error": "snapshot_kinds must contain strings"}
                        )
                        return
                    snapshot_kinds.append(it.strip())

                allowed = {
                    "t_minus_60m",
                    "t_minus_30m",
                    "t_minus_20m",
                    "t_minus_10m",
                    "t_minus_5m",
                    "t_minus_1m",
                    "final",
                }
                unknown = [k for k in snapshot_kinds if k not in allowed]
                if unknown:
                    self._send_json(
                        400,
                        {"error": f"unknown snapshot_kinds: {', '.join(unknown)}"},
                    )
                    return

            # Optional prefetch days (default: 7)
            prefetch_days: int | None = None
            if "prefetch_days" in payload:
                try:
                    prefetch_days = int(payload.get("prefetch_days"))
                except (TypeError, ValueError):
                    self._send_json(400, {"error": "prefetch_days must be an integer"})
                    return
                if prefetch_days < 0 or prefetch_days > 31:
                    self._send_json(400, {"error": "prefetch_days must be 0..31"})
                    return

            state = self._app.update_schedule(
                enabled=enabled,
                baba_codes=baba_codes,
                snapshot_kinds=snapshot_kinds,
                prefetch_days=prefetch_days,
            )
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
