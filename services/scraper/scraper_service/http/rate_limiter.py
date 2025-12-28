from __future__ import annotations

import random
import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class RateLimitConfig:
    min_interval_sec: float
    jitter_sec: float


class SimpleRateLimiter:
    """Process-wide rate limiter for a single host.

    This implementation is intentionally simple:
    - concurrency is controlled by the caller (we run sequentially by default)
    - the limiter enforces min interval between requests (+ random jitter)
    """

    def __init__(self, cfg: RateLimitConfig) -> None:
        self._cfg = cfg
        self._lock = Lock()
        self._last_ts: float | None = None

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._last_ts is None:
                self._last_ts = now
                return

            elapsed = now - self._last_ts
            target = self._cfg.min_interval_sec + random.uniform(0.0, self._cfg.jitter_sec)
            if elapsed < target:
                time.sleep(target - elapsed)
            self._last_ts = time.monotonic()
