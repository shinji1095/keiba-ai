from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Float

from app.db.base import Base


class RaceResult(Base):
    __tablename__ = "race_results"
    __table_args__ = (
        UniqueConstraint("race_id", "finish_position", name="uq_race_finish_position"),
        UniqueConstraint("race_id", "horse_number", name="uq_race_horse_number"),
    )

    race_result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(Integer, ForeignKey("races.race_id", ondelete="CASCADE"), index=True)

    finish_position: Mapped[int] = mapped_column(Integer)
    horse_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_str: Mapped[str | None] = mapped_column(String(50), nullable=True)
    margin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last3f: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    corner1: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corner2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corner3: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corner4: Mapped[str | None] = mapped_column(String(50), nullable=True)
