from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class OAuthClientView(BaseModel):
    client_id: str
    name: str
    scopes: list[str]
    is_active: bool
    created_at: dt.datetime
    revoked_at: Optional[dt.datetime] = None


class OAuthClientWithSecret(OAuthClientView):
    client_secret: str = Field(description="Returned only once")


class OAuthClientCreateRequest(BaseModel):
    name: str
    scopes: list[str]
    is_active: bool = True


class OAuthClientCreateResponse(BaseModel):
    client: OAuthClientWithSecret


class OAuthClientRotateSecretResponse(BaseModel):
    client: OAuthClientWithSecret


class OAuthClientUpdateRequest(BaseModel):
    scopes: Optional[list[str]] = None
    is_active: Optional[bool] = None


class OAuthClientListResponse(BaseModel):
    items: list[OAuthClientView]
    page: int
    page_size: int
