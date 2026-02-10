from __future__ import annotations

import datetime as dt


def test_win_prob_race_not_found(client):
    r = client.get("/ml/win-prob/999999")
    assert r.status_code == 404


def test_win_prob_requires_mlflow_config(client):
    # Arrange: create a minimal race + entries (model is intentionally not configured in test env)
    from app.db.models.race import Race
    from app.db.models.race_entry import RaceEntry
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        race = Race(
            race_date=dt.date(2025, 1, 1),
            baba_code=1,
            race_no=1,
            start_time=None,
            distance_m=1600,
            course="T",
            weather="sunny",
            track_condition="good",
            race_name="test",
            field_size=2,
            status="scheduled",
        )
        db.add(race)
        db.flush()

        db.add_all(
            [
                RaceEntry(
                    race_id=race.race_id,
                    horse_id=None,
                    post_position=1,
                    horse_number=1,
                    horse_name="h1",
                    jockey_name="j1",
                    trainer_name="t1",
                    handicap_kg=55.0,
                    body_weight=480,
                    body_weight_diff=0,
                ),
                RaceEntry(
                    race_id=race.race_id,
                    horse_id=None,
                    post_position=2,
                    horse_number=2,
                    horse_name="h2",
                    jockey_name="j2",
                    trainer_name="t2",
                    handicap_kg=55.0,
                    body_weight=480,
                    body_weight_diff=0,
                ),
            ]
        )
        db.commit()
        race_id = race.race_id
    finally:
        db.close()

    # Act
    r = client.get(f"/ml/win-prob/{race_id}")

    # Assert
    assert r.status_code == 502
