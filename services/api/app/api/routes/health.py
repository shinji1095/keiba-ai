from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")
