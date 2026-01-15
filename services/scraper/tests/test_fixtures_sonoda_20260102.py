from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scraper_service.parsers.deba_table import parse_deba_table
from scraper_service.parsers.deba_table_normalized import parse_deba_table_normalized
from scraper_service.parsers.odds import parse_generic_odds_table, parse_odds_tanfuku, parse_odds_waku
from scraper_service.parsers.race_mark_table import parse_race_mark_table


FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"


def _fixture_path(*parts: str) -> Path:
    return FIXTURES_ROOT.joinpath(*parts)


def _read_fixture(*parts: str) -> bytes:
    return _fixture_path(*parts).read_bytes()


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.mark.parametrize(
    "race_no, filename, expected_sha256",
    [
        (1, "R01_debatable.html", "cb43d1e23999442a64243890e7e77cc3140b2198f63d9fb39594c23b0f93f669"),
        (2, "R02_debatable.html", "a2fd24de3e2be060fc63fda90d0503988561db30605eb598adc80278635cfce9"),
    ],
)
def test_debatable_fixtures_sha256(race_no: int, filename: str, expected_sha256: str) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/{filename}")
    assert _sha256(html) == expected_sha256


def test_race_mark_table_fixture_sha256() -> None:
    html = _read_fixture("27_2026-01-02_02R/R02_race_mark_table.html")
    assert _sha256(html) == "a36dd7be083aa6252bdcbb234d2901bed1a1a202cfe45eeb271634d3eae8b933"


@pytest.mark.parametrize(
    "race_no, expected_horse",
    [
        (1, (8, "トゥルーナイト")),
        (2, (6, "ニューアスラーダ")),
    ],
)
def test_parse_deba_table_fixtures_sonoda_20260102(race_no: int, expected_horse: tuple[int, str]) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_debatable.html")
    entries = parse_deba_table(html, race_date="2026-01-02", baba_code=27, race_no=race_no)
    assert len(entries) == 12
    by_no = {e.horse_number: e for e in entries}

    horse_no, horse_name = expected_horse
    assert by_no[horse_no].horse_name == horse_name
    assert any(e.jockey_name for e in entries)
    assert any(e.handicap_kg is not None for e in entries)


@pytest.mark.parametrize(
    "horse_no, win_odds, place_min, place_max",
    [
        (1, 67.9, 3.2, 7.0),
        (3, 2.2, 1.0, 1.3),
        (10, 4.4, 1.2, 2.2),
        (11, 2.2, 1.0, 1.4),
    ],
)
def test_parse_odds_tanfuku_fixture_sonoda_20260114(
    horse_no: int, win_odds: float, place_min: float, place_max: float
) -> None:
    html = _read_fixture("27_2026-01-14_01R/R01_tanfuku.html")
    parsed = parse_odds_tanfuku(html)
    tansho = parsed.get("tansho", [])
    fukusho = parsed.get("fukusho", [])
    assert len(tansho) == 12
    assert len(fukusho) == 12

    for it in tansho:
        if it.odds_min is not None and it.odds_max is not None:
            assert it.odds_min == it.odds_max
    for it in fukusho:
        if it.odds_min is not None and it.odds_max is not None:
            assert it.odds_min <= it.odds_max

    got_win = next(it for it in tansho if it.legs == [horse_no])
    assert got_win.odds_min == win_odds
    assert got_win.odds_max == win_odds

    got_place = next(it for it in fukusho if it.legs == [horse_no])
    assert got_place.odds_min == place_min
    assert got_place.odds_max == place_max


@pytest.mark.parametrize(
    "race_no, legs, odds, popularity",
    [
        (1, [6, 7], 1.2, 1),
        (2, [6, 8], 4.2, 1),
    ],
)
def test_parse_odds_wakuren_fixtures_sonoda_20260102(
    race_no: int, legs: list[int], odds: float, popularity: int
) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_wakuren.html")
    parsed = parse_odds_waku(html)
    wakuren = parsed.get("wakuren", [])
    assert len(wakuren) == 32

    got = next(it for it in wakuren if it.legs == legs)
    assert got.odds_min == odds
    assert got.odds_max == odds
    assert got.popularity == popularity


@pytest.mark.parametrize(
    "race_no, legs, odds",
    [
        (1, [8, 9], 1.3),
        (2, [1, 5], 5702.6),
    ],
)
def test_parse_odds_umaren_fixtures_sonoda_20260102(race_no: int, legs: list[int], odds: float) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_umarenfuku.html")
    items = parse_generic_odds_table(html, bet_type="umaren")
    assert len(items) == 66

    got = next(it for it in items if it.legs == legs)
    assert got.odds_min == odds
    assert got.odds_max == odds


@pytest.mark.parametrize(
    "race_no, legs, odds",
    [
        (1, [8, 9], 1.5),
        (2, [1, 5], 3370.6),
    ],
)
def test_parse_odds_umatan_fixtures_sonoda_20260102(race_no: int, legs: list[int], odds: float) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_umarentan.html")
    items = parse_generic_odds_table(html, bet_type="umatan")
    assert len(items) == 132

    got = next(it for it in items if it.legs == legs and it.is_ordered is True)
    assert got.odds_min == odds
    assert got.odds_max == odds


@pytest.mark.parametrize(
    "race_no, legs, odds_min, odds_max",
    [
        (1, [1, 9], 2.7, 4.0),
        (2, [2, 4], 5.9, 7.1),
    ],
)
def test_parse_odds_wide_fixtures_sonoda_20260102(
    race_no: int, legs: list[int], odds_min: float, odds_max: float
) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_waido.html")
    items = parse_generic_odds_table(html, bet_type="wide")
    assert len(items) == 66

    got = next(it for it in items if it.legs == legs)
    assert got.odds_min == odds_min
    assert got.odds_max == odds_max


@pytest.mark.parametrize(
    "race_no, expected",
    [
        (
            1,
            {
                "race_name": "Ｃ３三４歳以上",
                "post_time": "10:40",
                "surface": "ダート",
                "distance_m": 1400,
                "direction": "右",
                "weather": "晴",
                "track_condition": "良",
                "spot_horse_no": 8,
                "spot_horse_key": "horse:トゥルーナイト",
                "spot_win_odds": 1.1,
                "spot_popularity": 1,
            },
        ),
        (
            2,
            {
                "race_name": "３歳未勝利二３歳二",
                "post_time": "11:10",
                "surface": "ダート",
                "distance_m": 820,
                "direction": "右",
                "weather": "晴",
                "track_condition": "良",
                "spot_horse_no": 6,
                "spot_horse_key": "horse:ニューアスラーダ",
                "spot_win_odds": 6.9,
                "spot_popularity": 4,
            },
        ),
    ],
)
def test_parse_deba_table_normalized_fixtures_sonoda_20260102(
    race_no: int, expected: dict[str, object]
) -> None:
    html = _read_fixture(f"27_2026-01-02_{race_no:02d}R/R{race_no:02d}_debatable.html")
    card = parse_deba_table_normalized(
        html,
        race_date="2026-01-02",
        baba_code=27,
        race_no=race_no,
    )

    assert card.race.race_id == f"27_2026-01-02_{race_no:02d}"
    assert card.race.post_time == expected["post_time"]
    assert card.race.race_name == expected["race_name"]
    assert card.race.surface == expected["surface"]
    assert card.race.distance_m == expected["distance_m"]
    assert card.race.direction == expected["direction"]
    assert card.race.weather == expected["weather"]
    assert card.race.track_condition == expected["track_condition"]

    assert len(card.race_entries) == 12
    assert len(card.horses) == 12

    horse_keys = {h.horse_key for h in card.horses}
    assert {e.horse_key for e in card.race_entries} == horse_keys

    perf_total_keys = {p.perf_key for p in card.perf_total}
    perf_left_keys = {p.perf_key for p in card.perf_dirt_left}
    perf_right_keys = {p.perf_key for p in card.perf_dirt_right}
    perf_track_keys = {p.perf_key for p in card.perf_track}
    perf_distance_keys = {p.perf_key for p in card.perf_distance}
    best_time_keys = {b.best_time_key for b in card.best_time}

    assert len(perf_total_keys) == 12
    assert len(perf_left_keys) == 12
    assert len(perf_right_keys) == 12
    assert len(perf_track_keys) == 12
    assert len(perf_distance_keys) == 12
    assert len(best_time_keys) == 12

    for p in card.perf_total + card.perf_dirt_left + card.perf_dirt_right + card.perf_track + card.perf_distance:
        assert p.starts == p.first_cnt + p.second_cnt + p.third_cnt + p.out_cnt
        assert p.horse_key in horse_keys

    for e in card.race_entries:
        assert e.perf_total_key in perf_total_keys
        assert e.perf_dirt_left_key in perf_left_keys
        assert e.perf_dirt_right_key in perf_right_keys
        assert e.perf_track_key in perf_track_keys
        assert e.perf_distance_key in perf_distance_keys
        assert e.best_time_key in best_time_keys

    spot_horse_no = int(expected["spot_horse_no"])
    spot_entry = next(it for it in card.race_entries if it.horse_no == spot_horse_no)
    assert spot_entry.horse_key == expected["spot_horse_key"]
    assert spot_entry.win_odds == expected["spot_win_odds"]
    assert spot_entry.popularity == expected["spot_popularity"]

    # Spot-check last5 (horse 1, most recent) for 1R.
    if race_no == 1:
        last1 = next(it for it in card.last5 if it.horse_no == 1 and it.order_in_last5 == 1)
        assert last1.finish_pos == 4
        assert last1.past_race_date == "2025-12-17"
        assert last1.track_condition == "良"
        assert last1.runners == 10
        assert last1.place == "園田"
        assert last1.direction == "右"
        assert last1.distance_m == 1400
        assert last1.horse_no_in_race == 9
        assert last1.popularity == 3
        assert last1.body_weight == 457
        assert last1.jockey_name == "廣瀬航"
        assert last1.burden_weight == 55.0
        assert last1.time_raw == "1:36.0"
        assert last1.time_sec == 96.0
        assert last1.passing_order_raw == "6-6-5-7"
        assert last1.passing_order_arr == [6, 6, 5, 7]
        assert last1.last3f == 40.9
        assert last1.time_diff == 0.8
        assert last1.winner_name == "イッシン"


def test_parse_race_mark_table_fixtures_sonoda_20260102_02r() -> None:
    html = _read_fixture("27_2026-01-02_02R/R02_race_mark_table.html")
    results = parse_race_mark_table(
        html, race_date="2026-01-02", baba_code=27, race_no=2
    )
    assert len(results) == 12

    # finish positions 1..12
    assert [r.finish_position for r in results] == list(range(1, 13))

    # horse numbers should be unique and match the table (2R)
    expected_horse_nos = [9, 12, 11, 6, 2, 10, 7, 5, 1, 8, 4, 3]
    assert [r.horse_number for r in results] == expected_horse_nos
    assert len({r.horse_number for r in results if r.horse_number is not None}) == 12

    # spot check: 1st place time
    assert results[0].time_str == "0:52.2"

    # corner passing (race-level) should be present at least for 3/4 corners on this race
    assert results[0].corner3 is not None
    assert results[0].corner4 is not None
