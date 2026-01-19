from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, ForeignKeyConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class SpecEntryLast5Race(Base):
    __tablename__ = "entry_last5_race"
    __table_args__ = (
        ForeignKeyConstraint(
            ["race_id", "horse_no"],
            ["race_entry.race_id", "race_entry.horse_no"],
            name="fk_spec_last5_entry",
            ondelete="CASCADE",
        ),
    )

    race_id: Mapped[str] = mapped_column(String, primary_key=True)
    horse_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_in_last5: Mapped[int] = mapped_column(Integer, primary_key=True)

    finish_pos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    past_race_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    track_condition: Mapped[str | None] = mapped_column(String, nullable=True)
    runners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place: Mapped[str | None] = mapped_column(String, nullable=True)
    direction: Mapped[str | None] = mapped_column(String, nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)

    horse_no_in_race: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jockey_name: Mapped[str | None] = mapped_column(String, nullable=True)

    burden_weight: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    time_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    time_sec: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    passing_order_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    # NOTE: migration uses INT[] on PostgreSQL; SQLite doesn't support arrays.
    # We store JSON array for SQLite tests and keep API-level semantics.
    passing_order_arr: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    last3f: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    time_diff: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    winner_name: Mapped[str | None] = mapped_column(String, nullable=True)

    note: Mapped[str | None] = mapped_column(String, nullable=True)






