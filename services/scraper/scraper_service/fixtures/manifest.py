from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field

Device = Literal["pc", "sp"]
SnapshotKind = Literal["manual", "t_minus_5m", "t_minus_1m", "final"]


class RaceKey(BaseModel):
    race_date: str
    baba_code: int
    race_no: int


class ManifestItem(BaseModel):
    name: str
    race_key: RaceKey
    device: Device
    page_name: str
    url: str
    out: str

    odds_flg: Optional[int] = None
    snapshot_kind: SnapshotKind = "manual"
    expect_http_status: Optional[int] = Field(default=None, alias="expect.http_status")

    class Config:
        populate_by_name = True


def load_manifest(path: Path) -> list[ManifestItem]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("manifest.yml must be a list")
    out: list[ManifestItem] = []
    for raw in data:
        # allow nested expect.http_status style
        if isinstance(raw, dict) and "expect" in raw and isinstance(raw["expect"], dict) and "http_status" in raw["expect"]:
            raw = dict(raw)
            raw["expect.http_status"] = raw["expect"]["http_status"]
        out.append(ManifestItem.model_validate(raw))
    return out
