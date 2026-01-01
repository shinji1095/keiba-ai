from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawFetchLog(Base):
    __tablename__ = "raw_fetch_logs"

    raw_fetch_log_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    race_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("races.race_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_type: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2048))
    http_status: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
