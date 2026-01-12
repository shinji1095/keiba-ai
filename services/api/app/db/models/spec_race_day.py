from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecRaceDay(Base):
    __tablename__ = "race_day"

    race_date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    baba_code: Mapped[int] = mapped_column(
        Integer, ForeignKey("racecourse.baba_code"), primary_key=True
    )




