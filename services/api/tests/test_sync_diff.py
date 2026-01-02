from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import app.services.scrape_sync_service as sync_service
from app.services.scrape_sync_state import SyncEntry, SyncState, SyncStateStore


class DummyExportClient:
    def __init__(self, responses: dict[str, list[dict]] | None = None) -> None:
        self.responses = responses or {}

    def post_json(self, path: str, payload: dict) -> dict:
        return {"items": self.responses.get(path, [])}


def _patch_sync_client(monkeypatch, dummy: DummyExportClient) -> None:
    monkeypatch.setattr(
        sync_service.ScraperControlClient,
        "from_settings",
        classmethod(lambda cls: dummy),
    )


class DummyScrapeService:
    total_odds_calls = 0

    def __init__(self, db=None) -> None:
        _ = db

    def upsert_races(self, payload) -> None:
        _ = payload

    def upsert_entries(self, payload) -> None:
        _ = payload

    def upsert_results(self, payload) -> None:
        _ = payload

    def upsert_payouts(self, payload) -> None:
        _ = payload

    def insert_race_changes(self, payload) -> None:
        _ = payload

    def upsert_odds_snapshot(self, payload) -> None:
        _ = payload
        DummyScrapeService.total_odds_calls += 1


def test_build_scope_key_by_page_type() -> None:
    scope = sync_service._build_scope_key(
        page_type=sync_service.PAGE_RACE_LIST,
        race_date="2025-12-28",
        baba_code=5,
        race_no=None,
    )
    assert scope == "2025-12-28:5"

    scope = sync_service._build_scope_key(
        page_type=sync_service.PAGE_REFUND_MONEY_LIST,
        race_date="2025-12-28",
        baba_code=5,
        race_no=None,
    )
    assert scope == "2025-12-28:5"

    scope = sync_service._build_scope_key(
        page_type=sync_service.PAGE_DEBA_TABLE,
        race_date="2025-12-28",
        baba_code=5,
        race_no=7,
    )
    assert scope == "2025-12-28:5:7"

    with pytest.raises(ValueError):
        sync_service._build_scope_key(
            page_type=sync_service.PAGE_RACE_LIST,
            race_date=None,
            baba_code=5,
            race_no=None,
        )


def test_diff_key_includes_snapshot_fields() -> None:
    page_type = sync_service.ODDS_PAGE_BY_BET_TYPE["tansho"]
    diff_key = sync_service._diff_key(
        page_type=page_type,
        race_date="2025-12-28",
        baba_code=5,
        race_no=7,
        snapshot_kind="t_minus_5m",
        odds_flg=1,
    )
    assert diff_key == "2025-12-28:5:7|OddsTanFuku|t_minus_5m|1"


def test_should_sync_checks_fingerprint_and_flag() -> None:
    now = datetime.now(timezone.utc)
    state = SyncState(items={"key": SyncEntry(fingerprint="abc", updated_at=now)})

    assert sync_service._should_sync(state, "key", "abc", diff_enabled=True) is False
    assert sync_service._should_sync(state, "key", "def", diff_enabled=True) is True
    assert sync_service._should_sync(state, "key", "abc", diff_enabled=False) is True
    assert sync_service._should_sync(state, "new", "abc", diff_enabled=True) is True


def test_fingerprint_payload_is_deterministic() -> None:
    payload_a = {"b": 1, "a": 2}
    payload_b = {"a": 2, "b": 1}
    assert (
        sync_service._fingerprint_payload(payload_a)
        == sync_service._fingerprint_payload(payload_b)
    )


def test_sync_skips_same_odds_payload(
    client, monkeypatch, tmp_path: Path
) -> None:
    dummy = DummyExportClient(
        responses={
            "/control/export/odds-snapshots": [
                {
                    "race_key": {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7},
                    "bet_type": "tansho",
                    "snapshot_kind": "t_minus_5m",
                    "captured_at": "2025-12-28T00:00:00+00:00",
                    "source_url": "https://example.invalid/odds",
                    "odds_flg": 1,
                    "is_final": False,
                    "items": [
                        {"legs": [1], "is_ordered": False, "odds_min": 2.3, "odds_max": None, "popularity": 1}
                    ],
                }
            ],
        }
    )
    _patch_sync_client(monkeypatch, dummy)
    monkeypatch.setattr(sync_service, "ScrapeService", DummyScrapeService)
    DummyScrapeService.total_odds_calls = 0

    store = SyncStateStore(tmp_path / "sync_state.json")
    service = sync_service.ScrapeSyncService(db=None, state_store=store)

    service.run_sync(trigger="test")
    first_count = DummyScrapeService.total_odds_calls

    service.run_sync(trigger="test")
    assert DummyScrapeService.total_odds_calls == first_count
