from __future__ import annotations

import time

from scraper_service.http.rate_limiter import RateLimitConfig, SimpleRateLimiter


def test_rate_limiter_min_interval():
    rl = SimpleRateLimiter(RateLimitConfig(min_interval_sec=0.05, jitter_sec=0.0))
    rl.wait()
    t0 = time.monotonic()
    rl.wait()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.045  # allow small scheduling jitter
