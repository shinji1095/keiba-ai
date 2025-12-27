from __future__ import annotations

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PasswordLoginRequest(BaseModel):
    username: str
    password: str


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class ClientCredentialsTokenRequest(BaseModel):
    grant_type: Literal["client_credentials"]
    client_id: str
    client_secret: str
    scope: Optional[str] = Field(default=None, description="Space separated scopes (optional)")


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    issued_at: Optional[dt.datetime] = None
