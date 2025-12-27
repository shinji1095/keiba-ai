from __future__ import annotations

from fastapi import APIRouter, Depends, Response, Cookie

from app.core.config import settings
from app.core.errors import AppError
from app.schemas.auth import (
    ClientCredentialsTokenRequest,
    PasswordLoginRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.api.deps import get_db

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: PasswordLoginRequest, response: Response, db=Depends(get_db)) -> TokenResponse:
    svc = AuthService(db)
    token, refresh_cookie = svc.password_login(payload.username, payload.password)
    response.headers.append("Set-Cookie", refresh_cookie)
    return token


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    db=Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise AppError.unauthorized("missing refresh_token cookie")

    svc = AuthService(db)
    token, refresh_cookie = svc.refresh(refresh_token)
    response.headers.append("Set-Cookie", refresh_cookie)
    return token


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    db=Depends(get_db),
) -> None:
    svc = AuthService(db)
    svc.logout(refresh_token)

    response.headers.append("Set-Cookie", settings.clear_refresh_cookie())
    return None


@router.post("/token", response_model=TokenResponse)
def token(payload: ClientCredentialsTokenRequest, db=Depends(get_db)) -> TokenResponse:
    svc = AuthService(db)
    return svc.client_credentials_token(payload)
