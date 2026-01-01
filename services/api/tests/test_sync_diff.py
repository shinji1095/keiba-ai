from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import app.services.scrape_sync_service as sync_service
from app.services.scrape_sync_state import SyncEntry, SyncState, SyncStateStore


class DummyIngestClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []

    def post(self, path: str, payload: dict) -> None:
        self.posts.append((path, payload))


def _patch_sync_client(monkeypatch, dummy: DummyIngestClient) -> None:
    monkeypatch.setattr(
        sync_service.ScraperIngestClient,
        "from_settings",
        classmethod(lambda cls: dummy),
    )


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


def test_sync_uses_raw_fetch_log_sha_for_odds(
    client, monkeypatch, tmp_path: Path
) -> None:
    from app.db.models.odds import OddsItem as OddsItemModel
    from app.db.models.odds import OddsSnapshot as OddsSnapshotModel
    from app.db.models.race import Race as RaceModel
    from app.db.models.raw_fetch_log import RawFetchLog as RawFetchLogModel
    from app.db.session import SessionLocal

    dummy = DummyIngestClient()
    _patch_sync_client(monkeypatch, dummy)

    db = SessionLocal()
    try:
        race = RaceModel(
            race_date=date(2025, 12, 28),
            baba_code=5,
            race_no=7,
        )
        db.add(race)
        db.commit()
        db.refresh(race)

        captured_at = datetime(2025, 12, 28, 0, 0, tzinfo=timezone.utc)
        snapshot = OddsSnapshotModel(
            race_id=race.race_id,
            bet_type="tansho",
            snapshot_kind="t_minus_5m",
            captured_at=captured_at,
            source_url="https://example.invalid/odds",
            odds_flg=1,
            is_final=False,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        item = OddsItemModel(
            odds_snapshot_id=snapshot.odds_snapshot_id,
            legs=[1],
            is_ordered=False,
            odds_min=2.3,
            odds_max=None,
            popularity=1,
            raw_text=None,
        )
        db.add(item)

        log_sha = "0" * 64
        log = RawFetchLogModel(
            race_id=race.race_id,
            page_type=sync_service.ODDS_PAGE_BY_BET_TYPE["tansho"],
            url=snapshot.source_url,
            http_status=200,
            sha256=log_sha,
            storage_path=None,
            captured_at=captured_at,
            note=None,
        )
        db.add(log)
        db.commit()

        store = SyncStateStore(tmp_path / "sync_state.json")
        service = sync_service.ScrapeSyncService(db, store)
        service.run_sync(trigger="test")

        diff_key = sync_service._diff_key(
            page_type=sync_service.ODDS_PAGE_BY_BET_TYPE["tansho"],
            race_date=race.race_date.isoformat(),
            baba_code=race.baba_code,
            race_no=race.race_no,
            snapshot_kind=snapshot.snapshot_kind,
            odds_flg=snapshot.odds_flg,
        )
        state = store.load()
        assert state.items[diff_key].fingerprint == log_sha
    finally:
        db.close()
