from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint(
            "race_id",
            "bet_type",
            "legs_key",
            "is_ordered",
            name="uq_payout_key",
        ),
    )

    payout_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True)

    bet_type: Mapped[str] = mapped_column(String(50), index=True)

    # Denormalized key for uniqueness + lookup. Example: "3", "3-7", "3-7-12".
    legs_key: Mapped[str] = mapped_column(String(255), index=True)

    legs: Mapped[list[int]] = mapped_column(JSON)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)
    payout_yen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
