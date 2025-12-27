from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Float

from app.db.base import Base


class RaceEntry(Base):
    __tablename__ = "race_entries"
    __table_args__ = (
        UniqueConstraint(
            "race_id", "horse_number", name="uq_race_entry_horse_number"
        ),
    )

    race_entry_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    race_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True
    )

    horse_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    post_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horse_number: Mapped[int] = mapped_column(Integer)
    horse_name: Mapped[str] = mapped_column(String(255))
    jockey_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trainer_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    handicap_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_weight_diff: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
