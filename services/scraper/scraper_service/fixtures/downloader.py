from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scraper_service.fixtures.manifest import ManifestItem, load_manifest
from scraper_service.http.client import HttpClient
from scraper_service.keiba.soft_errors import SOFT_NO_ODDS_PATTERNS, SOFT_TEMP_UNAVAILABLE_PATTERNS


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class DownloadSummary:
    total: int
    ok: int
    ng: int


class FixtureDownloader:
    def __init__(self, *, http: HttpClient) -> None:
        self._http = http

    def download_manifest(self, *, manifest_path: Path, fixtures_root: Path) -> DownloadSummary:
        items = load_manifest(manifest_path)
        log_path = fixtures_root / "manifest_log.csv"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            with log_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "name",
                        "out_path",
                        "url",
                        "fetched_at",
                        "http_status",
                        "sha256",
                        "content_type",
                        "content_encoding",
                        "elapsed_ms",
                        "note",
                    ]
                )

        ok = 0
        ng = 0

        with log_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)

            for it in items:
                out_path = fixtures_root / it.out
                out_path.parent.mkdir(parents=True, exist_ok=True)

                res = self._http.get_html(it.url, page_type=it.page_name, save_dir=out_path.parent)
                # rename saved file to exact out name (stable)
                # if storage_path already saved, move it
                stored = Path(res.storage_path) if res.storage_path else None
                sha256 = res.sha256
                if stored is not None and stored.exists():
                    # always overwrite file in fixture folder (fixtures are immutable per new name, but file path is distinct)
                    out_path.write_bytes(stored.read_bytes())
                    stored.unlink(missing_ok=True)

                note = ""
                body_text = res.content.decode("utf-8", errors="ignore")
                if any(p in body_text for p in SOFT_NO_ODDS_PATTERNS):
                    note = "soft_no_odds"
                elif any(p in body_text for p in SOFT_TEMP_UNAVAILABLE_PATTERNS):
                    note = "soft_temp_unavailable"

                expected = it.expect_http_status
                if expected is not None and res.http_status != expected:
                    note = (note + "; " if note else "") + f"unexpected_status(expected={expected})"

                if res.http_status < 400:
                    ok += 1
                else:
                    ng += 1

                w.writerow(
                    [
                        it.name,
                        str(out_path.as_posix()),
                        it.url,
                        res.fetched_at,
                        res.http_status,
                        sha256 or "",
                        res.content_type or "",
                        res.content_encoding or "",
                        res.elapsed_ms,
                        note,
                    ]
                )

        return DownloadSummary(total=len(items), ok=ok, ng=ng)
