from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    build_refresh_cookie,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.schemas.auth import ClientCredentialsTokenRequest, TokenResponse
from app.services.oauth_client_service import OAuthClientService
from app.services.token_store import TokenStore
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserService(db)
        self.oauth_clients = OAuthClientService(db)
        self.tokens = TokenStore()

    def _token_response(self, token: str, expires_in: int, issued_at: dt.datetime) -> TokenResponse:
        return TokenResponse(access_token=token, expires_in=expires_in, issued_at=issued_at)

    def password_login(self, username: str, password: str) -> tuple[TokenResponse, str]:
        user = self.users.get_by_username(username)
        if user is None:
            raise AppError.unauthorized("invalid username or password")
        if not verify_password(password, user.password_hash):
            raise AppError.unauthorized("invalid username or password")

        access_token, expires_in, issued_at = create_access_token(
            subject=str(user.id),
            sub_type="user",
            role=user.role,
            scopes=[],
        )

        refresh_token, _ = create_refresh_token(subject=str(user.id))
        refresh_payload = decode_refresh_token(refresh_token)
        refresh_jti = refresh_payload.get("jti")
        if not refresh_jti:
            raise AppError.unauthorized("failed to create refresh token")

        ttl_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
        self.tokens.set_current_refresh_jti(str(user.id), refresh_jti, ttl_seconds=ttl_seconds)

        return self._token_response(access_token, expires_in, issued_at), build_refresh_cookie(refresh_token)

    def refresh(self, refresh_token: str) -> tuple[TokenResponse, str]:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise AppError.unauthorized("invalid refresh token")

        if self.tokens.is_refresh_revoked(jti):
            raise AppError.unauthorized("refresh token revoked")

        current = self.tokens.get_current_refresh_jti(user_id)
        if current is None:
            raise AppError.unauthorized("refresh token not recognized")
        if current != jti:
            # reuse or old token after rotation
            self.tokens.revoke_refresh_jti(jti, ttl_seconds=settings.refresh_token_expire_days * 24 * 60 * 60)
            raise AppError.unauthorized("refresh token rotated")

        user = self.users.get_by_id(int(user_id))
        if user is None:
            raise AppError.unauthorized("user not found")

        access_token, expires_in, issued_at = create_access_token(
            subject=str(user.id),
            sub_type="user",
            role=user.role,
            scopes=[],
        )

        new_refresh_token, _ = create_refresh_token(subject=str(user.id))
        new_payload = decode_refresh_token(new_refresh_token)
        new_jti = new_payload.get("jti")
        if not new_jti:
            raise AppError.unauthorized("failed to create refresh token")

        ttl_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
        self.tokens.revoke_refresh_jti(jti, ttl_seconds=ttl_seconds)
        self.tokens.set_current_refresh_jti(str(user.id), new_jti, ttl_seconds=ttl_seconds)

        return self._token_response(access_token, expires_in, issued_at), build_refresh_cookie(new_refresh_token)

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_refresh_token(refresh_token)
        except AppError:
            return
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id:
            self.tokens.clear_user_refresh(user_id)
        if jti:
            ttl_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
            self.tokens.revoke_refresh_jti(jti, ttl_seconds=ttl_seconds)

    def client_credentials_token(self, payload: ClientCredentialsTokenRequest) -> TokenResponse:
        if payload.grant_type != "client_credentials":
            raise AppError.bad_request("unsupported grant_type")

        client = self.oauth_clients.verify_client_secret(payload.client_id, payload.client_secret)
        if client is None:
            raise AppError.unauthorized("invalid client credentials")

        requested_scopes: list[str] = []
        if payload.scope:
            requested_scopes = [s for s in payload.scope.split(" ") if s]

        allowed_scopes = set(client.scopes or [])
        if requested_scopes:
            if any(s not in allowed_scopes for s in requested_scopes):
                raise AppError.forbidden("requested scope is not allowed")
            scopes = requested_scopes
        else:
            scopes = list(allowed_scopes)

        access_token, expires_in, issued_at = create_access_token(
            subject=client.client_id,
            sub_type="client",
            role=None,
            scopes=scopes,
        )
        return self._token_response(access_token, expires_in, issued_at)
