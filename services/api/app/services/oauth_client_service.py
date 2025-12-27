from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import generate_client_secret, hash_password, verify_password
from app.db.models.oauth_client import OAuthClient
from app.schemas.admin import (
    OAuthClientCreateRequest,
    OAuthClientCreateResponse,
    OAuthClientListResponse,
    OAuthClientRotateSecretResponse,
    OAuthClientUpdateRequest,
    OAuthClientView,
    OAuthClientWithSecret,
)


class OAuthClientService:
    def __init__(self, db: Session):
        self.db = db

    def _to_view(self, c: OAuthClient) -> OAuthClientView:
        return OAuthClientView(
            client_id=c.client_id,
            name=c.name,
            scopes=list(c.scopes or []),
            is_active=bool(c.is_active),
            created_at=c.created_at,
            revoked_at=c.revoked_at,
        )

    def create_client(self, payload: OAuthClientCreateRequest) -> OAuthClientCreateResponse:
        existing = self.db.query(OAuthClient).filter(OAuthClient.name == payload.name).one_or_none()
        if existing is not None:
            raise AppError.conflict("client name already exists")

        client_id = uuid.uuid4().hex
        secret = generate_client_secret()

        c = OAuthClient(
            client_id=client_id,
            name=payload.name,
            client_secret_hash=hash_password(secret),
            scopes=list(payload.scopes),
            is_active=payload.is_active,
            created_at=dt.datetime.utcnow(),
            revoked_at=None,
        )
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)

        return OAuthClientCreateResponse(client=OAuthClientWithSecret(**self._to_view(c).model_dump(), client_secret=secret))

    def list_clients(self, page: int, page_size: int) -> OAuthClientListResponse:
        q = self.db.query(OAuthClient).order_by(OAuthClient.created_at.desc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return OAuthClientListResponse(items=[self._to_view(x) for x in items], page=page, page_size=page_size)

    def update_client(self, client_id: str, payload: OAuthClientUpdateRequest) -> OAuthClientView:
        c = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).one_or_none()
        if c is None:
            raise AppError.not_found("client not found")

        if payload.scopes is not None:
            c.scopes = list(payload.scopes)
        if payload.is_active is not None:
            c.is_active = bool(payload.is_active)
            if not c.is_active and c.revoked_at is None:
                c.revoked_at = dt.datetime.utcnow()

        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return self._to_view(c)

    def revoke_client(self, client_id: str) -> None:
        c = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).one_or_none()
        if c is None:
            raise AppError.not_found("client not found")
        c.is_active = False
        if c.revoked_at is None:
            c.revoked_at = dt.datetime.utcnow()
        self.db.add(c)
        self.db.commit()

    def rotate_secret(self, client_id: str) -> OAuthClientRotateSecretResponse:
        c = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).one_or_none()
        if c is None:
            raise AppError.not_found("client not found")
        secret = generate_client_secret()
        c.client_secret_hash = hash_password(secret)
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return OAuthClientRotateSecretResponse(client=OAuthClientWithSecret(**self._to_view(c).model_dump(), client_secret=secret))

    def verify_client_secret(self, client_id: str, client_secret: str) -> OAuthClient | None:
        c = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).one_or_none()
        if c is None or not c.is_active:
            return None
        if not verify_password(client_secret, c.client_secret_hash):
            return None
        return c
