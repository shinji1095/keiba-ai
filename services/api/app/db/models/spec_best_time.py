from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecBestTime(Base):
    __tablename__ = "best_time"
    __table_args__ = (
        UniqueConstraint(
            "horse_id",
            "baba_code",
            "surface",
            "distance_m",
            name="uq_best_time_key",
        ),
    )

    best_time_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    horse_id: Mapped[int] = mapped_column(Integer, ForeignKey("horse.horse_id"))
    baba_code: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(String, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)

    best_time_sec: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    best_time_good_sec: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    best_time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    best_time_good_raw: Mapped[str | None] = mapped_column(String, nullable=True)




