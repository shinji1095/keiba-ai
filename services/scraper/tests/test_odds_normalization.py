from __future__ import annotations

from scraper_service.parsers.common import parse_odds_range


def test_parse_odds_range_single():
    lo, hi = parse_odds_range("2.3")
    assert lo == 2.3
    assert hi == 2.3


def test_parse_odds_range_range_variants():
    for s in ["3.1-4.5", "3.1 - 4.5", "3.1〜4.5", "4.5～3.1", "3.1–4.5"]:
        lo, hi = parse_odds_range(s)
        assert lo == 3.1
        assert hi == 4.5


def test_parse_odds_range_missing():
    for s in ["", "-", "—", "発売なし"]:
        lo, hi = parse_odds_range(s)
        assert lo is None
        assert hi is None
