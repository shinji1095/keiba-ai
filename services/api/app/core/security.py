from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import secrets
import uuid
from typing import Any, Dict, Optional

import jwt

from app.core.config import settings
from app.core.errors import AppError


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ------------------------------
# Password hashing (PBKDF2-SHA256)
# ------------------------------
_PBKDF2_ITERATIONS = 260_000
_SALT_BYTES = 16
_DKLEN = 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
        dklen=_DKLEN,
    )
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(dk).decode("ascii").rstrip("="),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        alg, iters_s, salt_b64, dk_b64 = password_hash.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected = base64.urlsafe_b64decode(dk_b64 + "==")
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iters,
            dklen=len(expected),
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ------------------------------
# JWT
# ------------------------------
def create_access_token(
    *,
    subject: str,
    sub_type: str,
    role: Optional[str] = None,
    scopes: Optional[list[str]] = None,
) -> tuple[str, int, dt.datetime]:
    expires_delta = dt.timedelta(minutes=settings.access_token_expire_minutes)
    issued_at = _now_utc()
    exp = issued_at + expires_delta
    jti = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": subject,
        "sub_type": sub_type,
        "iat": int(issued_at.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
        "typ": "access",
    }
    if role:
        payload["role"] = role
    if scopes:
        payload["scp"] = scopes

    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, int(expires_delta.total_seconds()), issued_at


def create_refresh_token(*, subject: str) -> tuple[str, dt.datetime]:
    expires_delta = dt.timedelta(days=settings.refresh_token_expire_days)
    issued_at = _now_utc()
    exp = issued_at + expires_delta
    jti = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": subject,
        "sub_type": "user",
        "iat": int(issued_at.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
        "typ": "refresh",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, issued_at


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise AppError.unauthorized("token expired")
    except jwt.InvalidTokenError:
        raise AppError.unauthorized("invalid token")


def decode_access_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "access":
        raise AppError.unauthorized("not an access token")
    return payload


def decode_refresh_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("typ") != "refresh":
        raise AppError.unauthorized("not a refresh token")
    return payload


def build_refresh_cookie(refresh_token: str) -> str:
    parts = [
        f"refresh_token={refresh_token}",
        f"Path={settings.refresh_cookie_path}",
        "HttpOnly",
    ]
    if settings.refresh_cookie_domain:
        parts.append(f"Domain={settings.refresh_cookie_domain}")
    if settings.refresh_cookie_secure:
        parts.append("Secure")
    parts.append(f"SameSite={settings.refresh_cookie_samesite}")
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    parts.append(f"Max-Age={max_age}")
    return "; ".join(parts)


def generate_client_secret() -> str:
    return secrets.token_urlsafe(32)
