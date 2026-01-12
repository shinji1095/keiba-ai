from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, ForeignKeyConstraint, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecRace(Base):
    __tablename__ = "race"
    __table_args__ = (
        UniqueConstraint("race_date", "baba_code", "race_no", name="uq_spec_race_key"),
        ForeignKeyConstraint(
            ["race_date", "baba_code"],
            ["race_day.race_date", "race_day.baba_code"],
            name="fk_spec_race_day",
        ),
    )

    race_id: Mapped[str] = mapped_column(String, primary_key=True)
    race_date: Mapped[dt.date] = mapped_column(Date, index=True)
    baba_code: Mapped[int] = mapped_column(Integer, index=True)
    race_no: Mapped[int] = mapped_column(Integer, index=True)

    post_time: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    race_name: Mapped[str] = mapped_column(String, nullable=False)
    surface: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str | None] = mapped_column(String, nullable=True)
    weather: Mapped[str | None] = mapped_column(String, nullable=True)
    track_condition: Mapped[str | None] = mapped_column(String, nullable=True)




