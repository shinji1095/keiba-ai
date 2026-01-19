from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime

import pytest

from scraper_service.config import Settings
from scraper_service.ingest.store import IngestStore
from scraper_service.keiba.models import PayoutUpsert, RaceKey, RaceUpsert
from scraper_service.scheduler.runner import ScrapeRunner


class _FixedDateTime(datetime):
    """datetime replacement for runner module (monkeypatch target)."""

    _fixed: datetime

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        if tz is not None:
            return cls._fixed.astimezone(tz)
        return cls._fixed


class _DummyHttp:
    def get_html(self, *args, **kwargs):  # pragma: no cover
        raise RuntimeError("network disabled in unit tests")


class _DummyCard:
    def __init__(self, *, post_time: str | None):
        self.race = SimpleNamespace(
            post_time=post_time,
            distance_m=None,
            direction=None,
            weather=None,
            track_condition=None,
            race_name=None,
        )

    def model_dump(self, mode: str = "json"):
        return {"race": {"post_time": self.race.post_time}}


def test_run_once_fetches_refund_using_deba_post_time_when_racelist_missing_start_time(
    tmp_path, monkeypatch
) -> None:
    """TR-033: RaceList start_time欠損でも、DebaTable post_timeでlast_start_dtを更新しRefundMoneyListを取得する。"""

    # Import the module to patch its module-level symbols (datetime / parsers).
    import scraper_service.scheduler.runner as runner_mod

    # Fixed time: after last race post_time by >= 90 minutes.
    _FixedDateTime._fixed = datetime.fromisoformat("2026-01-02T14:00:00+09:00")
    monkeypatch.setattr(runner_mod, "datetime", _FixedDateTime)

    cfg = Settings(
        raw_html_dir=tmp_path / "raw_html",
        ingest_dir=tmp_path / "ingest",
        control_dir=tmp_path / "control",
        local_log_dir=tmp_path / "logs",
        same_url_cooldown_sec=0.0,
        manual_min_interval_sec=0.0,
        manual_jitter_sec=0.0,
    )
    store = IngestStore(cfg.ingest_dir)
    runner = ScrapeRunner(settings=cfg, http=_DummyHttp(), sync_store=store)

    calls: list[tuple[str, int | None]] = []

    def fake_fetch(page_name: str, *, race_date: str, baba_code: int | None, race_no: int | None, odds_flg: int | None):
        calls.append((page_name, race_no))
        return (b"<html/>", "http://example.invalid", "")

    monkeypatch.setattr(runner, "_fetch", fake_fetch)

    # RaceList parser: start_time is missing for all races.
    def fake_parse_race_list(_html: bytes, *, race_date: str, baba_code: int):
        return [
            RaceUpsert(race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=1), start_time=None),
            RaceUpsert(race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=12), start_time=None),
        ]

    # DebaTable normalized parser: post_time exists (last race has the latest).
    def fake_parse_deba_table(_html: bytes, *, race_date: str, baba_code: int, race_no: int):
        return []

    def fake_parse_deba_table_normalized(_html: bytes, *, race_date: str, baba_code: int, race_no: int):
        if race_no == 12:
            return _DummyCard(post_time="12:00")
        return _DummyCard(post_time="10:00")

    def fake_parse_race_mark_table(_html: bytes, *, race_date: str, baba_code: int, race_no: int):
        return []

    def fake_parse_refund_money_list(_html: bytes, *, race_date: str, baba_code: int):
        return [
            PayoutUpsert(
                race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=12),
                bet_type="tansho",
                legs=[8],
                is_ordered=False,
                payout_yen=110,
                popularity=1,
            )
        ]

    # Avoid odds scraping (not part of this test).
    monkeypatch.setattr(runner, "_scrape_odds_for_race", lambda **kwargs: None)

    monkeypatch.setattr(runner_mod, "parse_race_list", fake_parse_race_list)
    monkeypatch.setattr(runner_mod, "parse_deba_table", fake_parse_deba_table)
    monkeypatch.setattr(runner_mod, "parse_deba_table_normalized", fake_parse_deba_table_normalized)
    monkeypatch.setattr(runner_mod, "parse_race_mark_table", fake_parse_race_mark_table)
    monkeypatch.setattr(runner_mod, "parse_refund_money_list", fake_parse_refund_money_list)

    runner.run_once(race_date="2026-01-02", baba_codes=[27], race_no=None)

    # RefundMoneyList should be fetched at least once.
    assert any(name == "RefundMoneyList" for (name, _rn) in calls)

    # And payouts should be appended to ingest store.
    payouts = store.list_latest(kind="payouts", race_date="2026-01-02", baba_code=27)
    assert payouts, "expected payouts to be saved via RefundMoneyList"



