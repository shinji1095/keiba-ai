from __future__ import annotations

from app.db.session import SessionLocal
from app.db.models.venue import Venue
from app.services.spec_race_card_ingest_service import SpecRaceCardIngestService


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_spec_race_card_ingest_and_get(client):
    # Login as bootstrap admin (created at startup)
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # The spec ingest reads from venues table; seed one row.
    db = SessionLocal()
    try:
        if db.query(Venue).filter(Venue.baba_code == 27).first() is None:
            db.add(Venue(baba_code=27, venue_name="園田"))
            db.commit()
    finally:
        db.close()

    payload = {
        "race_key": {"race_date": "2026-01-02", "baba_code": 27, "race_no": 1},
        "race": {
            "race_id": "27_2026-01-02_01",
            "race_date": "2026-01-02",
            "baba_code": 27,
            "race_no": 1,
            "post_time": "10:40",
            "race_name": "Ｃ３三４歳以上",
            "surface": "ダート",
            "distance_m": 1400,
            "direction": "右",
            "weather": "晴",
            "track_condition": "良",
        },
        "persons": [
            {"person_key": "jockey:吉村智:兵庫", "role": "jockey", "name": "吉村智", "affiliation": "兵庫"},
            {"person_key": "trainer:岡田利:兵庫", "role": "trainer", "name": "岡田利", "affiliation": "兵庫"},
            {"person_key": "owner:細川勝也", "role": "owner", "name": "細川勝也", "affiliation": ""},
        ],
        "horses": [
            {
                "horse_key": "horse:カヤコ",
                "horse_name": "カヤコ",
                "sex": "牝",
                "age": 7,
                "coat": "芦毛",
                "birth_month": 3,
                "birth_day": 2,
                "birth_md_raw": "03.02",
                "sire": "クリエイター２",
                "dam": "アートオブビーン",
                "dam_sire": "アグネスデジタル",
                "breeder": "岡田牧場",
            }
        ],
        "perf_total": [
            {"perf_key": "x", "horse_key": "horse:カヤコ", "first_cnt": 1, "second_cnt": 5, "third_cnt": 4, "out_cnt": 8, "starts": 18}
        ],
        "perf_dirt_left": [
            {"perf_key": "x", "horse_key": "horse:カヤコ", "first_cnt": 0, "second_cnt": 0, "third_cnt": 0, "out_cnt": 0, "starts": 0}
        ],
        "perf_dirt_right": [
            {"perf_key": "x", "horse_key": "horse:カヤコ", "first_cnt": 1, "second_cnt": 5, "third_cnt": 4, "out_cnt": 8, "starts": 18}
        ],
        "perf_track": [
            {"perf_key": "x", "horse_key": "horse:カヤコ", "first_cnt": 1, "second_cnt": 5, "third_cnt": 4, "out_cnt": 8, "starts": 18}
        ],
        "perf_distance": [
            {"perf_key": "x", "horse_key": "horse:カヤコ", "first_cnt": 1, "second_cnt": 5, "third_cnt": 4, "out_cnt": 8, "starts": 18}
        ],
        "best_time": [
            {
                "best_time_key": "x",
                "horse_key": "horse:カヤコ",
                "baba_code": 27,
                "surface": "ダート",
                "distance_m": 1400,
                "best_time_raw": "1:32.9",
                "best_time_sec": 92.9,
                "best_time_good_raw": "1:32.9",
                "best_time_good_sec": 92.9,
            }
        ],
        "race_entries": [
            {
                "race_id": "27_2026-01-02_01",
                "horse_no": 1,
                "waku": 1,
                "horse_key": "horse:カヤコ",
                "burden_weight": 55.0,
                "burden_mark": "",
                "body_weight": 458,
                "body_weight_diff": 1,
                "win_odds": 17.2,
                "popularity": 3,
                "jockey_person_key": "jockey:吉村智:兵庫",
                "trainer_person_key": "trainer:岡田利:兵庫",
                "owner_person_key": "owner:細川勝也",
                "perf_total_key": "x",
                "perf_dirt_left_key": "x",
                "perf_dirt_right_key": "x",
                "perf_track_key": "x",
                "perf_distance_key": "x",
                "best_time_key": "x",
            }
        ],
        "last5": [
            {
                "race_id": "27_2026-01-02_01",
                "horse_no": 1,
                "order_in_last5": 1,
                "finish_pos": 4,
                "past_race_date": "2025-12-17",
                "track_condition": "良",
                "runners": 10,
                "place": "園田",
                "direction": "右",
                "distance_m": 1400,
                "horse_no_in_race": 1,
                "popularity": 3,
                "body_weight": 457,
                "jockey_name": "廣瀬航",
                "burden_weight": 55.0,
                "time_raw": "1:36.0",
                "time_sec": 96.0,
                "passing_order_raw": "4-4-3-2",
                "passing_order_arr": [4, 4, 3, 2],
                "last3f": 42.4,
                "time_diff": 0.8,
                "winner_name": "イッシン",
            }
        ],
        "captured_at": "2026-01-04T00:00:00+09:00",
        "source_url": "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?k_raceDate=2026%2f01%2f02&k_raceNo=1&k_babaCode=27",
    }

    db2 = SessionLocal()
    try:
        svc = SpecRaceCardIngestService(db2)
        svc.upsert_race_card(payload)
        db2.commit()
    finally:
        db2.close()

    r2 = client.get(
        "/spec/race-cards/27/2026-01-02/1",
        headers=_auth_headers(token),
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["race"]["race_id"] == "27_2026-01-02_01"
    assert len(body["persons"]) == 3
    assert len(body["horses"]) == 1
    assert len(body["race_entries"]) == 1
    assert len(body["perf_total"]) == 1
    assert len(body["best_time"]) == 1
    assert len(body["last5"]) == 1


