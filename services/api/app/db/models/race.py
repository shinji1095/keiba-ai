from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Race(Base):
    __tablename__ = "races"
    __table_args__ = (
        UniqueConstraint(
            "race_date", "baba_code", "race_no", name="uq_race_key"
        ),
    )

    race_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    race_date: Mapped[dt.date] = mapped_column(Date, index=True)
    baba_code: Mapped[int] = mapped_column(Integer, index=True)
    race_no: Mapped[int] = mapped_column(Integer, index=True)

    start_time: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    course: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weather: Mapped[str | None] = mapped_column(String(50), nullable=True)
    track_condition: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    race_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
