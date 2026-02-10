from __future__ import annotations

import datetime as dt
import os
from zoneinfo import ZoneInfo

from prefect import flow, task

from pipeline_service.train_win_classifier import TrainConfig, train_and_register


@task
def example_step() -> str:
    return "ok"


@flow(name="keiba-ai-daily-train")
def daily_train_flow() -> dict[str, str]:
    # NOTE:
    # - まずは「1着になる/ならない」2値分類を end-to-end で回す。
    # - DATABASE_URL が無い環境（unit tests 等）では skip する。
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"status": "skipped", "reason": "DATABASE_URL not set"}

    tz = ZoneInfo(os.getenv("TZ", "Asia/Tokyo"))
    today = dt.datetime.now(tz).date()
    default_max_race_date = today - dt.timedelta(days=1)

    cfg = TrainConfig(
        database_url=database_url,
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"),
        experiment_name=os.getenv("MLFLOW_EXPERIMENT_NAME", "keiba-win-v1"),
        model_name=os.getenv("MLFLOW_MODEL_NAME", "keiba_win_classifier"),
        min_race_date=(
            dt.date.fromisoformat(os.getenv("TRAIN_MIN_RACE_DATE"))
            if os.getenv("TRAIN_MIN_RACE_DATE")
            else None
        ),
        max_race_date=(
            dt.date.fromisoformat(os.getenv("TRAIN_MAX_RACE_DATE"))
            if os.getenv("TRAIN_MAX_RACE_DATE")
            else default_max_race_date
        ),
        val_days=int(os.getenv("TRAIN_VAL_DAYS", "30")),
        test_days=int(os.getenv("TRAIN_TEST_DAYS", "30")),
        random_state=int(os.getenv("TRAIN_RANDOM_STATE", "42")),
        promote=os.getenv("TRAIN_PROMOTE", "false").lower() == "true",
        require_min_val_auc=float(os.getenv("TRAIN_REQUIRE_MIN_VAL_AUC", "0.55")),
    )

    _ = example_step()
    out = train_and_register(cfg)
    return {"status": "ok", **out}
