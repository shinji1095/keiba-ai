from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from scraper_service.http.rate_limiter import RateLimitConfig, SimpleRateLimiter


class FetchError(Exception):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    page_type: str
    http_status: int
    captured_at: str
    elapsed_ms: int
    sha256: Optional[str]
    storage_path: Optional[str]
    content_type: Optional[str]
    content_encoding: Optional[str]
    content: bytes


def _utc_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _should_retry(status: int) -> bool:
    return status in {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(
        self,
        *,
        user_agent: str,
        accept_language: str,
        min_interval_sec: float,
        jitter_sec: float,
        max_retries: int,
        backoff_base_sec: float,
        backoff_max_sec: float,
        timeout_sec: float = 20.0,
    ) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": accept_language,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "keep-alive",
            }
        )
        self._limiter = SimpleRateLimiter(RateLimitConfig(min_interval_sec=min_interval_sec, jitter_sec=jitter_sec))
        self._timeout_sec = timeout_sec
        self._max_retries = max_retries
        self._backoff_base_sec = backoff_base_sec
        self._backoff_max_sec = backoff_max_sec

    def get_html(self, url: str, *, page_type: str, save_dir: Optional[Path] = None) -> FetchResult:
        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self._max_retries:
            self._limiter.wait()
            attempt += 1
            t0 = time.monotonic()
            try:
                resp = self._session.get(url, timeout=self._timeout_sec, allow_redirects=True)
            except requests.RequestException as e:
                last_exc = e
                self._sleep_backoff(attempt)
                continue

            elapsed_ms = int((time.monotonic() - t0) * 1000)
            content = resp.content or b""
            sha256 = _sha256_bytes(content) if content else None
            storage_path = None
            if save_dir is not None and content:
                save_dir.mkdir(parents=True, exist_ok=True)
                fp = save_dir / f"{sha256}.html"
                fp.write_bytes(content)
                storage_path = str(fp.as_posix())

            if resp.status_code < 400:
                return FetchResult(
                    url=url,
                    final_url=str(resp.url),
                    page_type=page_type,
                    http_status=resp.status_code,
                    captured_at=_utc_iso(),
                    elapsed_ms=elapsed_ms,
                    sha256=sha256,
                    storage_path=storage_path,
                    content_type=resp.headers.get("Content-Type"),
                    content_encoding=resp.headers.get("Content-Encoding"),
                    content=content,
                )

            if _should_retry(resp.status_code) and attempt <= self._max_retries:
                self._sleep_backoff(attempt)
                continue

            return FetchResult(
                url=url,
                final_url=str(resp.url),
                page_type=page_type,
                http_status=resp.status_code,
                captured_at=_utc_iso(),
                elapsed_ms=elapsed_ms,
                sha256=sha256,
                storage_path=storage_path,
                content_type=resp.headers.get("Content-Type"),
                content_encoding=resp.headers.get("Content-Encoding"),
                content=content,
            )

        raise FetchError(f"failed to fetch {url}: {last_exc}")

    def _sleep_backoff(self, attempt: int) -> None:
        sec = min(self._backoff_base_sec * (2 ** (attempt - 1)), self._backoff_max_sec)
        time.sleep(sec)
