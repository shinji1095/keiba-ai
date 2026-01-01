from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="Keiba AI API", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    jwt_issuer: str = Field(default="keiba-ai", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="keiba-ai", alias="JWT_AUDIENCE")

    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=30, alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    refresh_cookie_secure: bool = Field(
        default=False, alias="REFRESH_COOKIE_SECURE"
    )
    refresh_cookie_samesite: str = Field(
        default="lax", alias="REFRESH_COOKIE_SAMESITE"
    )
    refresh_cookie_domain: Optional[str] = Field(
        default=None, alias="REFRESH_COOKIE_DOMAIN"
    )
    refresh_cookie_path: str = Field(default="/", alias="REFRESH_COOKIE_PATH")

    database_url: str = Field(
        default="sqlite:///./app.db", alias="DATABASE_URL"
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL"
    )
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="adminpass", alias="ADMIN_PASSWORD")
    admin_role: str = Field(default="admin", alias="ADMIN_ROLE")

    cors_allow_origins: List[str] = Field(
        default_factory=lambda: ["*"], alias="CORS_ALLOW_ORIGINS"
    )

    scraper_forward_enabled: bool = Field(
        default=False, alias="SCRAPER_FORWARD_ENABLED"
    )
    scraper_control_base_url: Optional[str] = Field(
        default=None, alias="SCRAPER_CONTROL_BASE_URL"
    )
    scraper_forward_timeout_sec: float = Field(
        default=5.0, alias="SCRAPER_FORWARD_TIMEOUT_SEC"
    )
    scraper_mtls_cert: Optional[str] = Field(
        default=None, alias="SCRAPER_MTLS_CERT"
    )
    scraper_mtls_key: Optional[str] = Field(
        default=None, alias="SCRAPER_MTLS_KEY"
    )
    scraper_mtls_ca_cert: Optional[str] = Field(
        default=None, alias="SCRAPER_MTLS_CA_CERT"
    )

    def clear_refresh_cookie(self) -> str:
        parts = [
            "refresh_token=",
            f"Path={self.refresh_cookie_path}",
            "HttpOnly",
            "Max-Age=0",
        ]
        if self.refresh_cookie_domain:
            parts.append(f"Domain={self.refresh_cookie_domain}")
        if self.refresh_cookie_secure:
            parts.append("Secure")
        parts.append(f"SameSite={self.refresh_cookie_samesite}")
        return "; ".join(parts)


settings = Settings()
