from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, SecurityScopes

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.db.models.user import User
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)

scraper_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "scrape:write": "Scraper can ingest/insert facts",
        "scrape:read": "Scraper can read back for verification",
    },
    auto_error=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[object, Depends(get_db)]


def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(bearer_scheme)],
    db=Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError.unauthorized("missing bearer token")

    payload = decode_access_token(credentials.credentials)

    if payload.get("sub_type") != "user":
        raise AppError.forbidden("token is not a user token")

    user_id = payload.get("sub")
    if not user_id:
        raise AppError.unauthorized("invalid token subject")

    svc = UserService(db)
    user = svc.get_by_id(int(user_id))
    if user is None:
        raise AppError.unauthorized("user not found")

    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise AppError.forbidden("admin role required")
    return user


class ScraperPrincipal:
    def __init__(self, client_id: str, scopes: list[str]):
        self.client_id = client_id
        self.scopes = scopes


def get_scraper_principal(
    security_scopes: SecurityScopes,
    token: Annotated[Optional[str], Security(scraper_oauth2, scopes=["scrape:write"])],
) -> ScraperPrincipal:
    if not token:
        raise AppError.unauthorized("missing bearer token")

    payload = decode_access_token(token)

    if payload.get("sub_type") != "client":
        raise AppError.forbidden("token is not a client token")

    token_scopes = payload.get("scp") or []
    if not isinstance(token_scopes, list):
        raise AppError.forbidden("invalid scopes in token")

    required = list(security_scopes.scopes)
    missing = [s for s in required if s not in token_scopes]
    if missing:
        raise AppError.forbidden(f"missing scope(s): {', '.join(missing)}")

    client_id = payload.get("sub")
    if not client_id:
        raise AppError.unauthorized("invalid token subject")

    return ScraperPrincipal(client_id=client_id, scopes=token_scopes)
