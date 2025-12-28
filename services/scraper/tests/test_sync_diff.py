from __future__ import annotations

import pytest

from scraper_service.keiba import constants as C
from scraper_service.sync.diff import build_diff_key, build_scope_key, should_sync_by_fingerprint


def test_build_scope_key_today_top() -> None:
    assert (
        build_scope_key(page_type=C.PAGE_TODAY_TOP, race_date="2025-12-28", baba_code=None, race_no=None)
        == "2025-12-28"
    )


def test_build_scope_key_race_list() -> None:
    assert (
        build_scope_key(page_type=C.PAGE_RACE_LIST, race_date="2025-12-28", baba_code=20, race_no=None)
        == "2025-12-28:20"
    )


def test_build_scope_key_deba_table() -> None:
    assert (
        build_scope_key(page_type=C.PAGE_DEBA_TABLE, race_date="2025-12-28", baba_code=20, race_no=3)
        == "2025-12-28:20:3"
    )


def test_build_scope_key_odds_page() -> None:
    assert (
        build_scope_key(page_type=C.PAGE_ODDS_TANFUKU, race_date="2025-12-28", baba_code=20, race_no=3)
        == "2025-12-28:20:3"
    )


def test_build_scope_key_missing_baba_code() -> None:
    with pytest.raises(ValueError):
        build_scope_key(page_type=C.PAGE_RACE_LIST, race_date="2025-12-28", baba_code=None, race_no=None)


def test_build_scope_key_missing_race_no() -> None:
    with pytest.raises(ValueError):
        build_scope_key(page_type=C.PAGE_DEBA_TABLE, race_date="2025-12-28", baba_code=20, race_no=None)


def test_build_diff_key_includes_snapshot_and_odds_flg() -> None:
    assert build_diff_key(
        page_type=C.PAGE_ODDS_TANFUKU,
        race_date="2025-12-28",
        baba_code=20,
        race_no=3,
        snapshot_kind="t_minus_5m",
        odds_flg=4,
    ) == ("2025-12-28:20:3", C.PAGE_ODDS_TANFUKU, "t_minus_5m", 4)


def test_should_sync_by_fingerprint() -> None:
    assert should_sync_by_fingerprint("abc", "abc") is False
    assert should_sync_by_fingerprint("abc", "def") is True
    assert should_sync_by_fingerprint("abc", None) is True
    assert should_sync_by_fingerprint("abc", "") is True
