from __future__ import annotations

import time
from typing import Optional

import redis

from app.core.config import settings


class TokenStore:
    """Refresh token rotation store.

    - When Redis is enabled, store current refresh JTI per user and revoked JTIs.
    - When Redis is disabled or unavailable, fall back to in-memory store (dev only).
    """

    def __init__(self):
        self._enabled = settings.redis_enabled
        self._client: Optional[redis.Redis] = None
        self._mem_current: dict[str, str] = {}
        self._mem_revoked: dict[str, float] = {}

        if self._enabled:
            try:
                self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                # ping once (lazy failures are painful)
                self._client.ping()
            except Exception:
                # fall back to memory store
                self._client = None
                self._enabled = False

    def _cleanup_mem(self) -> None:
        now = time.time()
        expired = [k for k, exp in self._mem_revoked.items() if exp <= now]
        for k in expired:
            del self._mem_revoked[k]

    def get_current_refresh_jti(self, user_id: str) -> Optional[str]:
        if self._enabled and self._client is not None:
            return self._client.get(f"user_refresh_jti:{user_id}")
        return self._mem_current.get(user_id)

    def set_current_refresh_jti(self, user_id: str, jti: str, ttl_seconds: int) -> None:
        if self._enabled and self._client is not None:
            self._client.setex(f"user_refresh_jti:{user_id}", ttl_seconds, jti)
            return
        self._mem_current[user_id] = jti

    def revoke_refresh_jti(self, jti: str, ttl_seconds: int) -> None:
        if self._enabled and self._client is not None:
            self._client.setex(f"revoked_refresh:{jti}", ttl_seconds, "1")
            return
        self._cleanup_mem()
        self._mem_revoked[jti] = time.time() + ttl_seconds

    def is_refresh_revoked(self, jti: str) -> bool:
        if self._enabled and self._client is not None:
            return self._client.exists(f"revoked_refresh:{jti}") == 1
        self._cleanup_mem()
        exp = self._mem_revoked.get(jti)
        return exp is not None and exp > time.time()

    def clear_user_refresh(self, user_id: str) -> None:
        if self._enabled and self._client is not None:
            self._client.delete(f"user_refresh_jti:{user_id}")
            return
        self._mem_current.pop(user_id, None)
