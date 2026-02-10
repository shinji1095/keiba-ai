import datetime as dt

import pandas as pd

from pipeline_service.train_win_classifier import (
    FEATURE_CATEGORICAL,
    FEATURE_NUMERIC,
    FEATURES,
    LABEL_COL,
    RACE_DATE_COL,
    RACE_ID_COL,
    _build_model,
    _evaluate_split,
    _time_split,
)


def _make_df(*, days: int = 40, races_per_day: int = 2, horses_per_race: int = 6) -> pd.DataFrame:
    rows = []
    race_id = 1
    for day in range(days):
        race_date = dt.date(2025, 1, 1) + dt.timedelta(days=day)
        for race_no in range(1, races_per_day + 1):
            winner_horse_number = 1
            for horse_number in range(1, horses_per_race + 1):
                rows.append(
                    {
                        RACE_ID_COL: race_id,
                        RACE_DATE_COL: race_date,
                        "baba_code": 1,
                        "race_no": race_no,
                        "distance_m": 1600,
                        "course": "T",
                        "weather": "sunny",
                        "track_condition": "good",
                        "field_size": horses_per_race,
                        "horse_number": horse_number,
                        "post_position": horse_number,
                        "jockey_name": f"j{horse_number}",
                        "trainer_name": f"t{horse_number}",
                        "handicap_kg": 55.0,
                        "body_weight": 480,
                        "body_weight_diff": 0,
                        "race_month": race_date.month,
                        "race_dow": race_date.weekday(),
                        LABEL_COL: 1 if horse_number == winner_horse_number else 0,
                    }
                )
            race_id += 1
    return pd.DataFrame(rows)


def test_time_split_non_empty():
    df = _make_df()
    splits = _time_split(df, val_days=7, test_days=7)
    assert set(splits.keys()) == {"train", "val", "test"}
    assert len(splits["train"]) > 0
    assert len(splits["val"]) > 0
    assert len(splits["test"]) > 0


def test_model_fit_and_evaluate_smoke():
    df = _make_df()
    splits = _time_split(df, val_days=7, test_days=7)
    model = _build_model(random_state=0)

    # Ensure feature lists stay aligned with generated DF
    assert set(FEATURE_NUMERIC + FEATURE_CATEGORICAL) == set(FEATURES)
    assert set(FEATURES).issubset(set(df.columns))

    model.fit(splits["train"][FEATURES], splits["train"][LABEL_COL])
    prob_val = pd.Series(model.predict_proba(splits["val"][FEATURES])[:, 1])
    metrics = _evaluate_split(splits["val"], prob_val)
    assert metrics["rows"] == float(len(splits["val"]))
    assert "roc_auc" in metrics
