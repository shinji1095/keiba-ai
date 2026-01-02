from __future__ import annotations

import os

import pytest

from scraper_service.config import Settings
from scraper_service.http.client import HttpClient
from scraper_service.ingest.store import IngestStore
from scraper_service.keiba import constants as C
from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.race_list import parse_race_list
from scraper_service.scheduler.runner import ScrapeRunner


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


@pytest.mark.integration
def test_live_scrape_baba32_20251228(tmp_path) -> None:
    """Live scrape test (network dependent).

    Target:
      - baba_code=32 (佐賀)
      - race_date=2025-12-28
    """

    if os.getenv("RUN_LIVE_SCRAPE_TEST") != "1":
        pytest.skip("RUN_LIVE_SCRAPE_TEST is not set (set to 1 to run live scraping)")

    require = os.getenv("REQUIRE_LIVE_SCRAPE_TEST") == "1"

    cfg = Settings(
        raw_html_dir=tmp_path / "raw_html",
        ingest_dir=tmp_path / "ingest",
        control_dir=tmp_path / "control",
        local_log_dir=tmp_path / "logs",
    )
    http = _build_http(cfg)
    runner = ScrapeRunner(
        settings=cfg, http=http, sync_store=IngestStore(cfg.ingest_dir)
    )

    try:
        html, _, _ = runner._fetch(
            C.PAGE_RACE_LIST,
            race_date="2025-12-28",
            baba_code=32,
            race_no=None,
            odds_flg=None,
        )
    except Exception as exc:
        if require:
            pytest.fail(f"live scrape failed: {exc}")
        pytest.skip(f"live scrape failed (skipping): {exc}")
        return

    races = parse_race_list(html, race_date="2025-12-28", baba_code=32)
    assert len(races) >= 10

    try:
        html_deba, _, _ = runner._fetch(
            C.PAGE_DEBA_TABLE,
            race_date="2025-12-28",
            baba_code=32,
            race_no=1,
            odds_flg=None,
        )
    except Exception as exc:
        if require:
            pytest.fail(f"live scrape (DebaTable) failed: {exc}")
        pytest.skip(f"live scrape (DebaTable) failed (skipping): {exc}")
        return

    entries = parse_deba_table(
        html_deba, race_date="2025-12-28", baba_code=32, race_no=1
    )
    assert entries
    assert any(e.jockey_name for e in entries)
    assert any(e.handicap_kg is not None for e in entries)


