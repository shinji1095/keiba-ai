from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import create_engine, text

LABEL_COL = "label_win"
RACE_ID_COL = "race_id"
RACE_DATE_COL = "race_date"

FEATURE_NUMERIC = [
    "baba_code",
    "race_no",
    "distance_m",
    "field_size",
    "horse_number",
    "post_position",
    "handicap_kg",
    "body_weight",
    "body_weight_diff",
    "race_month",
    "race_dow",
]

FEATURE_CATEGORICAL = [
    "course",
    "weather",
    "track_condition",
    "jockey_name",
    "trainer_name",
]

FEATURES = FEATURE_NUMERIC + FEATURE_CATEGORICAL


@dataclass(frozen=True)
class TrainConfig:
    database_url: str
    tracking_uri: str
    experiment_name: str
    model_name: str
    min_race_date: dt.date | None
    max_race_date: dt.date | None
    val_days: int
    test_days: int
    random_state: int
    promote: bool
    require_min_val_auc: float


def _git_sha() -> str | None:
    try:
        s = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None
    return s or None


def _parse_date(s: str | None) -> dt.date | None:
    if s is None or s == "":
        return None
    return dt.date.fromisoformat(s)


def _load_labeled_entries(cfg: TrainConfig) -> pd.DataFrame:
    sql = text(
        """
        SELECT
          r.race_id,
          r.race_date,
          r.baba_code,
          r.race_no,
          r.distance_m,
          r.course,
          r.weather,
          r.track_condition,
          r.field_size,
          e.horse_number,
          e.post_position,
          e.jockey_name,
          e.trainer_name,
          e.handicap_kg,
          e.body_weight,
          e.body_weight_diff,
          CASE WHEN res.finish_position = 1 THEN 1 ELSE 0 END AS label_win
        FROM race_entries e
        JOIN races r ON r.race_id = e.race_id
        JOIN race_results res
          ON res.race_id = e.race_id
         AND res.horse_number = e.horse_number
        WHERE (:min_race_date IS NULL OR r.race_date >= :min_race_date)
          AND (:max_race_date IS NULL OR r.race_date <= :max_race_date)
        """
    )

    engine = create_engine(cfg.database_url, pool_pre_ping=True)
    df = pd.read_sql_query(
        sql,
        con=engine,
        params={
            "min_race_date": cfg.min_race_date,
            "max_race_date": cfg.max_race_date,
        },
        parse_dates=[RACE_DATE_COL],
    )
    if df.empty:
        raise ValueError("no training rows (check DB / date range)")

    # Feature engineering (leak-safe: only from race/entry tables + race_date derivations)
    df[RACE_DATE_COL] = pd.to_datetime(df[RACE_DATE_COL]).dt.date
    df["race_month"] = pd.to_datetime(df[RACE_DATE_COL]).dt.month
    df["race_dow"] = pd.to_datetime(df[RACE_DATE_COL]).dt.weekday

    expected = {RACE_ID_COL, RACE_DATE_COL, LABEL_COL, *FEATURES}
    unexpected = sorted(set(df.columns) - expected)
    if unexpected:
        raise ValueError(f"unexpected columns detected (possible leakage): {unexpected}")

    missing = sorted(expected - set(df.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    df[LABEL_COL] = df[LABEL_COL].astype(int)
    if not set(df[LABEL_COL].unique()).issubset({0, 1}):
        raise ValueError("label must be 0/1")

    # Basic integrity checks
    dup = df.duplicated(subset=[RACE_ID_COL, "horse_number"]).any()
    if dup:
        raise ValueError("duplicated (race_id, horse_number) detected")

    return df


def _time_split(df: pd.DataFrame, *, val_days: int, test_days: int) -> dict[str, pd.DataFrame]:
    if val_days <= 0 or test_days <= 0:
        raise ValueError("val_days/test_days must be >= 1")

    unique_dates = sorted({d for d in df[RACE_DATE_COL].unique().tolist() if d is not None})
    if not unique_dates:
        raise ValueError("race_date is empty")

    max_date: dt.date = max(unique_dates)
    test_start = max_date - dt.timedelta(days=test_days - 1)
    val_start = test_start - dt.timedelta(days=val_days)

    train_df = df[df[RACE_DATE_COL] < val_start].copy()
    val_df = df[(df[RACE_DATE_COL] >= val_start) & (df[RACE_DATE_COL] < test_start)].copy()
    test_df = df[df[RACE_DATE_COL] >= test_start].copy()

    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError(
            "time split produced empty split; adjust val_days/test_days or widen date range"
        )
    return {"train": train_df, "val": val_df, "test": test_df}


def _build_model(random_state: int) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, FEATURE_NUMERIC),
            ("cat", categorical_transformer, FEATURE_CATEGORICAL),
        ]
    )

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=1,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("clf", clf)])


def _safe_metric(fn, *args, **kwargs) -> float | None:
    try:
        return float(fn(*args, **kwargs))
    except Exception:
        return None


def _race_top1_accuracy(df: pd.DataFrame, prob: pd.Series) -> float:
    tmp = df[[RACE_ID_COL, LABEL_COL]].copy()
    tmp["prob"] = prob.to_numpy()
    idx = tmp.groupby(RACE_ID_COL)["prob"].idxmax()
    return float(tmp.loc[idx, LABEL_COL].mean())


def _evaluate_split(df: pd.DataFrame, prob_pos: pd.Series) -> dict[str, float | None]:
    y_true = df[LABEL_COL].astype(int).to_numpy()
    y_prob = prob_pos.to_numpy()
    y_pred = (y_prob >= 0.5).astype(int)

    return {
        "rows": float(len(df)),
        "positive_rate": float(y_true.mean()) if len(y_true) else None,
        "roc_auc": _safe_metric(roc_auc_score, y_true, y_prob),
        "pr_auc": _safe_metric(average_precision_score, y_true, y_prob),
        "log_loss": _safe_metric(log_loss, y_true, y_prob, labels=[0, 1]),
        "brier": _safe_metric(brier_score_loss, y_true, y_prob),
        "accuracy": _safe_metric(accuracy_score, y_true, y_pred),
        "precision": _safe_metric(precision_score, y_true, y_pred, zero_division=0),
        "recall": _safe_metric(recall_score, y_true, y_pred, zero_division=0),
        "race_top1_acc": _safe_metric(_race_top1_accuracy, df, prob_pos),
    }


def _register_and_maybe_promote(
    *,
    run_id: str,
    model_name: str,
    promote: bool,
    require_min_val_auc: float,
    val_auc: float | None,
) -> dict[str, Any]:
    client = MlflowClient()
    model_uri = f"runs:/{run_id}/model"
    mv = mlflow.register_model(model_uri=model_uri, name=model_name)

    # Wait until READY (async in many backends)
    deadline = time.time() + 60
    while time.time() < deadline:
        got = client.get_model_version(name=model_name, version=mv.version)
        if got.status == "READY":
            break
        time.sleep(1)

    promoted = False
    promote_reason = "skipped"
    if promote:
        if val_auc is None:
            promote_reason = "val_auc_missing"
        elif val_auc < require_min_val_auc:
            promote_reason = f"val_auc<{require_min_val_auc}"
        else:
            client.transition_model_version_stage(
                name=model_name,
                version=mv.version,
                stage="Production",
                archive_existing_versions=True,
            )
            promoted = True
            promote_reason = "ok"

    return {
        "model_name": model_name,
        "model_version": mv.version,
        "promoted": promoted,
        "promote_reason": promote_reason,
    }


def train_and_register(cfg: TrainConfig) -> dict[str, Any]:
    df = _load_labeled_entries(cfg)
    splits = _time_split(df, val_days=cfg.val_days, test_days=cfg.test_days)

    model = _build_model(cfg.random_state)

    X_train = splits["train"][FEATURES]
    y_train = splits["train"][LABEL_COL].astype(int)
    model.fit(X_train, y_train)

    prob_val = pd.Series(model.predict_proba(splits["val"][FEATURES])[:, 1])
    prob_test = pd.Series(model.predict_proba(splits["test"][FEATURES])[:, 1])

    metrics_val = _evaluate_split(splits["val"], prob_val)
    metrics_test = _evaluate_split(splits["test"], prob_test)

    mlflow.set_tracking_uri(cfg.tracking_uri)
    mlflow.set_experiment(cfg.experiment_name)

    git_sha = _git_sha()
    with mlflow.start_run(run_name="win_classifier") as run:
        tags = {
            "task": "binary_classification",
            "label": "finish_position==1",
            "split": f"time(val_days={cfg.val_days},test_days={cfg.test_days})",
        }
        if git_sha:
            tags["git_sha"] = git_sha
        if cfg.min_race_date:
            tags["min_race_date"] = cfg.min_race_date.isoformat()
        if cfg.max_race_date:
            tags["max_race_date"] = cfg.max_race_date.isoformat()
        mlflow.set_tags(tags)

        mlflow.log_params(
            {
                "model": "LogisticRegression(class_weight=balanced)",
                "val_days": cfg.val_days,
                "test_days": cfg.test_days,
                "random_state": cfg.random_state,
                "features_numeric": json.dumps(FEATURE_NUMERIC, ensure_ascii=False),
                "features_categorical": json.dumps(
                    FEATURE_CATEGORICAL, ensure_ascii=False
                ),
            }
        )

        for k, v in metrics_val.items():
            if v is not None:
                mlflow.log_metric(f"val_{k}", v)
        for k, v in metrics_test.items():
            if v is not None:
                mlflow.log_metric(f"test_{k}", v)

        # Dataset profile artifact
        profile = {
            "rows_total": int(len(df)),
            "rows_train": int(len(splits["train"])),
            "rows_val": int(len(splits["val"])),
            "rows_test": int(len(splits["test"])),
            "race_date_min": str(df[RACE_DATE_COL].min()),
            "race_date_max": str(df[RACE_DATE_COL].max()),
            "positive_rate_total": float(df[LABEL_COL].mean()),
        }
        tmpdir = Path("/tmp/pipeline_service")
        tmpdir.mkdir(parents=True, exist_ok=True)
        profile_path = tmpdir / "dataset_profile.json"
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
        mlflow.log_artifact(str(profile_path))

        mlflow.sklearn.log_model(model, artifact_path="model")

        reg = _register_and_maybe_promote(
            run_id=run.info.run_id,
            model_name=cfg.model_name,
            promote=cfg.promote,
            require_min_val_auc=cfg.require_min_val_auc,
            val_auc=metrics_val.get("roc_auc"),
        )
        mlflow.set_tags(
            {
                "registry.model_name": reg["model_name"],
                "registry.model_version": str(reg["model_version"]),
                "registry.promoted": str(reg["promoted"]),
                "registry.promote_reason": reg["promote_reason"],
            }
        )

        return {
            "run_id": run.info.run_id,
            "val": metrics_val,
            "test": metrics_test,
            **reg,
        }


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train win/not-win classifier and register to MLflow.")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    p.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    p.add_argument("--experiment-name", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "keiba-win-v1"))
    p.add_argument("--model-name", default=os.getenv("MLFLOW_MODEL_NAME", "keiba_win_classifier"))
    p.add_argument("--min-race-date", default=None)
    p.add_argument("--max-race-date", default=None)
    p.add_argument("--val-days", type=int, default=30)
    p.add_argument("--test-days", type=int, default=30)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--promote", action="store_true")
    p.add_argument("--require-min-val-auc", type=float, default=0.55)
    return p


def main() -> None:
    args = _build_argparser().parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required (env or --database-url)")

    cfg = TrainConfig(
        database_url=args.database_url,
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        model_name=args.model_name,
        min_race_date=_parse_date(args.min_race_date),
        max_race_date=_parse_date(args.max_race_date),
        val_days=args.val_days,
        test_days=args.test_days,
        random_state=args.random_state,
        promote=bool(args.promote),
        require_min_val_auc=float(args.require_min_val_auc),
    )
    out = train_and_register(cfg)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
