from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class WinProbItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    horse_number: int = Field(..., ge=1)
    horse_name: str
    jockey_name: str | None = None
    trainer_name: str | None = None
    win_prob: float = Field(..., ge=0.0, le=1.0)


class WinProbResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    race_id: int
    model_name: str
    model_version: str
    model_stage: str
    items: list[WinProbItem]
