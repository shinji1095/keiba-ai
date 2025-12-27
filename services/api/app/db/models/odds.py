from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Float, JSON

from app.db.base import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "race_id",
            "bet_type",
            "snapshot_kind",
            "odds_flg",
            name="uq_odds_snapshot_key",
        ),
    )

    odds_snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True)

    bet_type: Mapped[str] = mapped_column(String(50), index=True)
    snapshot_kind: Mapped[str] = mapped_column(String(50), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source_url: Mapped[str] = mapped_column(String(1024))

    # Normalization for UNIQUE constraint semantics across DBs:
    # - API treats odds_flg as nullable
    # - DB stores NULL as -1 so that UNIQUE works even when odds_flg is omitted
    odds_flg: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)

    is_final: Mapped[bool] = mapped_column(Boolean, default=False)


class OddsItem(Base):
    __tablename__ = "odds_items"
    __table_args__ = (
        UniqueConstraint(
            "odds_snapshot_id",
            "legs_key",
            "is_ordered",
            name="uq_odds_item_key",
        ),
    )

    odds_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    odds_snapshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("odds_snapshots.odds_snapshot_id", ondelete="CASCADE"),
        index=True,
    )

    # Denormalized key for uniqueness + lookup. Example: "3", "3-7", "3-7-12".
    legs_key: Mapped[str] = mapped_column(String(255), index=True)

    legs: Mapped[list[int]] = mapped_column(JSON)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    odds_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
