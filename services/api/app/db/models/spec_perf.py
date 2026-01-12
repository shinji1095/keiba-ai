from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class _PerfBase(Base):
    __abstract__ = True

    horse_id: Mapped[int] = mapped_column(Integer, ForeignKey("horse.horse_id"))
    first_cnt: Mapped[int] = mapped_column(Integer, nullable=False)
    second_cnt: Mapped[int] = mapped_column(Integer, nullable=False)
    third_cnt: Mapped[int] = mapped_column(Integer, nullable=False)
    out_cnt: Mapped[int] = mapped_column(Integer, nullable=False)


class SpecPerfTotal(_PerfBase):
    __tablename__ = "perf_total"
    __table_args__ = (UniqueConstraint("horse_id", name="uq_perf_total_horse"),)

    perf_total_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class SpecPerfDirtLeft(_PerfBase):
    __tablename__ = "perf_dirt_left"
    __table_args__ = (UniqueConstraint("horse_id", name="uq_perf_dirt_left_horse"),)

    perf_dirt_left_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class SpecPerfDirtRight(_PerfBase):
    __tablename__ = "perf_dirt_right"
    __table_args__ = (UniqueConstraint("horse_id", name="uq_perf_dirt_right_horse"),)

    perf_dirt_right_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class SpecPerfTrack(_PerfBase):
    __tablename__ = "perf_track"
    __table_args__ = (
        UniqueConstraint("horse_id", "baba_code", "surface", name="uq_perf_track_key"),
    )

    perf_track_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baba_code: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(String, nullable=False)


class SpecPerfDistance(_PerfBase):
    __tablename__ = "perf_distance"
    __table_args__ = (
        UniqueConstraint(
            "horse_id",
            "baba_code",
            "surface",
            "distance_m",
            name="uq_perf_distance_key",
        ),
    )

    perf_distance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baba_code: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(String, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)




