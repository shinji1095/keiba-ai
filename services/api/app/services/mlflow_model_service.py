from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings
from app.core.errors import AppError


@dataclass(frozen=True)
class LoadedModel:
    model: Any
    model_name: str
    model_version: str
    model_stage: str
    loaded_at_unix: float


_lock = threading.Lock()
_cache: LoadedModel | None = None


def load_production_model(*, force_reload: bool = False) -> LoadedModel:
    tracking_uri = settings.mlflow_tracking_uri
    if not tracking_uri:
        raise AppError.bad_gateway("MLFLOW_TRACKING_URI is not set")

    ttl = max(int(settings.mlflow_model_cache_ttl_sec), 0)
    now = time.time()

    with _lock:
        global _cache
        if (
            _cache is not None
            and not force_reload
            and ttl > 0
            and now - _cache.loaded_at_unix < ttl
        ):
            return _cache

        mlflow.set_tracking_uri(tracking_uri)

        model_name = settings.mlflow_model_name
        stage = settings.mlflow_model_stage

        client = MlflowClient()
        versions = client.get_latest_versions(model_name, stages=[stage])
        if not versions:
            raise AppError.not_found(
                f"model not found: name={model_name} stage={stage}"
            )

        # NOTE: get_latest_versions may return multiple versions for the stage.
        # Keep the highest version for determinism.
        latest = max(versions, key=lambda v: int(v.version))

        model_uri = f"models:/{model_name}/{stage}"
        try:
            model = mlflow.sklearn.load_model(model_uri)
        except Exception as e:
            raise AppError.bad_gateway("failed to load model from mlflow") from e

        _cache = LoadedModel(
            model=model,
            model_name=model_name,
            model_version=str(latest.version),
            model_stage=stage,
            loaded_at_unix=now,
        )
        return _cache
