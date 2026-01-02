from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONValue


class RaceChange(Base):
    __tablename__ = "race_changes"

    race_change_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True
    )

    change_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONValue)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
