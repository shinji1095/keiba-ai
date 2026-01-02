from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Float

from app.db.base import Base
from app.db.types import IntArray


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        # NOTE:
        # - 契約（docs/database/25_database_definition.md）:
        #   UNIQUE (race_id, bet_type, snapshot_kind, odds_flg)
        # - odds_flg は NULL 可だが一意キーに含めるため、NULL を sentinel 値へ寄せて UNIQUE を担保する。
        sa.Index(
            "uq_odds_snapshot_key",
            "race_id",
            "bet_type",
            "snapshot_kind",
            sa.func.coalesce(sa.column("odds_flg"), -1),
            unique=True,
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
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    source_url: Mapped[str] = mapped_column(String(1024))
    odds_flg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)


class OddsItem(Base):
    __tablename__ = "odds_items"
    __table_args__ = (
        sa.UniqueConstraint(
            "odds_snapshot_id",
            "legs",
            "is_ordered",
            name="uq_odds_item_key",
        ),
    )

    odds_item_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    odds_snapshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("odds_snapshots.odds_snapshot_id", ondelete="CASCADE"),
        index=True,
    )

    legs: Mapped[list[int]] = mapped_column(IntArray)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    odds_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
