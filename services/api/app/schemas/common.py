from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
