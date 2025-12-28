from __future__ import annotations

from scraper_service.keiba import constants as C
from scraper_service.keiba.urls import build_url, race_date_to_k_raceDate


def test_race_date_to_k_raceDate_plain():
    assert race_date_to_k_raceDate("2025-12-27") == "2025/12/27"


def test_build_url_encodes_slash_once():
    url = build_url(C.PAGE_RACE_LIST, device="pc", race_date="2025-12-27", baba_code=1, race_no=None, odds_flg=None)
    assert "k_raceDate=2025%2F12%2F27" in url
    assert "%252F" not in url


def test_constants_odds_pages_match_site_structure():
    # The project docs list OddsUmLenFuku / OddsUmLenTan as separate pages.
    assert C.PAGE_ODDS_UMAREN == "OddsUmLenFuku"
    assert C.PAGE_ODDS_UMATAN == "OddsUmLenTan"
