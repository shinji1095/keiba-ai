from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = "http://localhost/api"
    api_access_token: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None

    keiba_device: Literal["pc", "sp"] = "pc"
    user_agent: str = "scraper-service/0.1 (+https://example.invalid)"
    accept_language: str = "ja"
    raw_html_dir: Path = Path("./data/raw_html")
    local_log_dir: Path = Path("./data/logs")

    # Load control (C2 fixed)
    min_interval_sec: float = 1.5
    jitter_sec: float = 0.25
    max_retries: int = 3
    backoff_base_sec: float = 0.8
    backoff_max_sec: float = 8.0

    # Additional load control
    # Avoid hitting the exact same URL within this window. This is used
    # by the scheduler loop (daemon mode) to defer tasks if needed.
    same_url_cooldown_sec: float = 30.0

    # Scheduler
    tick_sec: float = 10.0


settings = Settings()
