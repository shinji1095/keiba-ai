from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Float

from app.db.base import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "race_id",
            "bet_type",
            "snapshot_kind",
            "captured_at",
            "odds_flg",
            name="uq_odds_snapshot_key",
        ),
    )

    odds_snapshot_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True
    )

    bet_type: Mapped[str] = mapped_column(String(50), index=True)
    snapshot_kind: Mapped[str] = mapped_column(String(50), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source_url: Mapped[str] = mapped_column(String(1024))
    odds_flg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)


class OddsItem(Base):
    __tablename__ = "odds_items"

    odds_item_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    odds_snapshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("odds_snapshots.odds_snapshot_id", ondelete="CASCADE"),
        index=True,
    )

    legs: Mapped[list[int]] = mapped_column(JSON)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    odds_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
