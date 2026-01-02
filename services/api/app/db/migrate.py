from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path


def _service_root() -> Path:
    # /app/app/db/migrate.py -> /app
    return Path(__file__).resolve().parents[2]


def default_migrations_dir() -> Path:
    # docs/scraper/02_database_design.md の方針に合わせ、サービスルート配下に置く
    # services/api/db/migrations/sql -> /app/db/migrations/sql
    return _service_root() / "db" / "migrations" / "sql"


def list_sql_migrations(migrations_dir: Path) -> list[Migration]:
    if not migrations_dir.exists():
        raise RuntimeError(f"migrations_dir not found: {migrations_dir}")
    files = sorted(p for p in migrations_dir.glob("*.sql") if p.is_file())
    return [Migration(version=p.stem, path=p) for p in files]


def _ensure_schema_migrations(conn) -> None:
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version text PRIMARY KEY,
          applied_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def _fetch_applied_versions(conn) -> set[str]:
    rows = conn.execute(text("SELECT version FROM schema_migrations")).all()
    return {r[0] for r in rows if r and r[0]}


def apply_sql_migrations(
    engine: Engine,
    *,
    migrations_dir: Path | None = None,
    allowed_dialects: Iterable[str] = ("postgresql",),
) -> list[str]:
    """Apply SQL migrations and return applied versions.

    - 本番想定: PostgreSQL（docs の方針）
    - テスト: SQLite は create_all を使うため、本関数は呼ばない前提
    """

    if engine.dialect.name not in set(allowed_dialects):
        return []

    migrations_dir = migrations_dir or default_migrations_dir()
    migrations = list_sql_migrations(migrations_dir)

    applied: list[str] = []
    with engine.begin() as conn:
        _ensure_schema_migrations(conn)
        already = _fetch_applied_versions(conn)

    for m in migrations:
        if m.version in already:
            continue

        sql = m.path.read_text(encoding="utf-8")
        if not sql.strip():
            continue

        # Apply per-migration in its own transaction to keep partial progress.
        with engine.begin() as conn:
            _ensure_schema_migrations(conn)
            conn.exec_driver_sql(sql)
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v)"),
                {"v": m.version},
            )
        applied.append(m.version)
        already.add(m.version)

    return applied


