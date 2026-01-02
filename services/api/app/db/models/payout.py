from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import IntArray


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        sa.UniqueConstraint(
            "race_id",
            "bet_type",
            "legs",
            "is_ordered",
            name="uq_payout_key",
        ),
    )

    payout_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True
    )

    bet_type: Mapped[str] = mapped_column(String(50), index=True)
    legs: Mapped[list[int]] = mapped_column(IntArray)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    payout_yen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
