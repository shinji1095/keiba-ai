from __future__ import annotations

import json
import os
import urllib.request

import pytest

SCRAPER_HEALTH_URL = os.getenv("SCRAPER_HEALTH_URL", "").strip()


@pytest.mark.integration
def test_scraper_health_from_pc() -> None:
    if not SCRAPER_HEALTH_URL:
        pytest.skip("SCRAPER_HEALTH_URL is not set")

    req = urllib.request.Request(SCRAPER_HEALTH_URL, method="GET")
    with urllib.request.urlopen(req, timeout=5) as res:
        status = res.getcode()
        body = res.read().decode("utf-8")

    assert status == 200
    assert json.loads(body) == {"status": "ok"}
