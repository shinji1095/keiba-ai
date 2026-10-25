from typing import Annotated

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import DbDep, bearer_scheme, get_current_user
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.models.oauth_client import OAuthClient


def _authorize(credentials, db, scope: str, allow_user: bool):
    if not credentials:
        raise AppError.unauthorized("missing bearer token")
    payload = decode_access_token(credentials.credentials)
    if payload.get("sub_type") == "user" and allow_user:
        return get_current_user(credentials, db)
    if payload.get("sub_type") != "client":
        raise AppError.forbidden("monitoring service token required")
    client = db.get(OAuthClient, payload.get("sub", ""))
    if not client or not client.is_active:
        raise AppError.forbidden("monitoring client is inactive")
    if scope not in (payload.get("scp") or []) or scope not in (
        client.scopes or []
    ):
        raise AppError.forbidden(f"missing scope: {scope}")
    return client


def monitoring_reader(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer_scheme)
    ],
    db: DbDep,
):
    return _authorize(credentials, db, "monitor:read", True)


def monitoring_writer(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer_scheme)
    ],
    db: DbDep,
):
    return _authorize(credentials, db, "monitor:write", False)
