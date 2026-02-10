from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query

from app.api.deps import DbDep
from app.core.errors import AppError
from app.db.models.race import Race as RaceModel
from app.db.models.race_entry import RaceEntry as RaceEntryModel
from app.schemas.ml import WinProbItem, WinProbResponse
from app.services.mlflow_model_service import load_production_model

router = APIRouter()


@router.get(
    "/ml/win-prob/{race_id}",
    response_model=WinProbResponse,
)
def get_win_prob(
    race_id: int,
    db: DbDep,
    force_reload: bool = Query(False, description="Force reload MLflow model (debug)"),
) -> WinProbResponse:
    race = (
        db.query(RaceModel)
        .filter(RaceModel.race_id == race_id)
        .one_or_none()
    )
    if race is None:
        raise AppError.not_found("race not found")

    entries = (
        db.query(RaceEntryModel)
        .filter(RaceEntryModel.race_id == race_id)
        .order_by(RaceEntryModel.horse_number.asc())
        .all()
    )
    if not entries:
        raise AppError.not_found("race entries not found")

    loaded = load_production_model(force_reload=force_reload)

    rows: list[dict] = []
    for e in entries:
        rows.append(
            {
                "baba_code": race.baba_code,
                "race_no": race.race_no,
                "distance_m": race.distance_m,
                "course": race.course,
                "weather": race.weather,
                "track_condition": race.track_condition,
                "field_size": race.field_size,
                "horse_number": e.horse_number,
                "post_position": e.post_position,
                "jockey_name": e.jockey_name,
                "trainer_name": e.trainer_name,
                "handicap_kg": e.handicap_kg,
                "body_weight": e.body_weight,
                "body_weight_diff": e.body_weight_diff,
                "race_month": race.race_date.month,
                "race_dow": race.race_date.weekday(),
            }
        )

    X = pd.DataFrame(rows)
    try:
        prob = loaded.model.predict_proba(X)[:, 1]
    except Exception as e:
        raise AppError.internal("model predict_proba failed") from e

    items: list[WinProbItem] = []
    for e, p in zip(entries, prob, strict=True):
        items.append(
            WinProbItem(
                horse_number=e.horse_number,
                horse_name=e.horse_name,
                jockey_name=e.jockey_name,
                trainer_name=e.trainer_name,
                win_prob=float(p),
            )
        )

    return WinProbResponse(
        race_id=race_id,
        model_name=loaded.model_name,
        model_version=loaded.model_version,
        model_stage=loaded.model_stage,
        items=items,
    )
