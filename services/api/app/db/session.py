from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.migrate import apply_sql_migrations


def _ensure_sqlite_dir(db_url: str) -> None:
    if not db_url.startswith("sqlite:////"):
        return
    filepath = db_url.replace("sqlite:////", "/")
    p = Path(filepath).parent
    p.mkdir(parents=True, exist_ok=True)


def _engine():
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        _ensure_sqlite_dir(settings.database_url)
    return create_engine(
        settings.database_url, connect_args=connect_args, pool_pre_ping=True
    )


engine = _engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    # NOTE:
    # - SQLite（tests/dev）: SQLAlchemy の create_all を利用（高速・依存最小）。
    # - PostgreSQL（本番）: docs 方針に従い SQL マイグレーションを適用する。
    if settings.database_url.startswith("sqlite"):
        # Import models to register metadata
        from app.db import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
    else:
        apply_sql_migrations(engine)

    # Bootstrap admin user
    from app.services.user_service import UserService

    db = SessionLocal()
    try:
        svc = UserService(db)
        svc.ensure_bootstrap_admin()
        db.commit()
    finally:
        db.close()
