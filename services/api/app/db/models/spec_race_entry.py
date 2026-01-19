from __future__ import annotations

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecRaceEntry(Base):
    __tablename__ = "race_entry"
    __table_args__ = (
        ForeignKeyConstraint(
            ["race_id"],
            ["race.race_id"],
            name="fk_spec_entry_race",
            ondelete="CASCADE",
        ),
    )

    race_id: Mapped[str] = mapped_column(String, primary_key=True)
    horse_no: Mapped[int] = mapped_column(Integer, primary_key=True)

    waku: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horse_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("horse.horse_id"), nullable=True
    )

    burden_weight_display: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    apprentice_allowance_symbol: Mapped[str | None] = mapped_column(
        String(1), nullable=True
    )
    apprentice_allowance_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burden_weight_base: Mapped[float | None] = mapped_column(
        Numeric(4, 1), nullable=True
    )

    body_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_weight_diff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_odds: Mapped[float | None] = mapped_column(Numeric(8, 1), nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    jockey_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("person.person_id"), nullable=True
    )
    trainer_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("person.person_id"), nullable=True
    )
    owner_person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("person.person_id"), nullable=True
    )

    perf_total_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("perf_total.perf_total_id"), nullable=True
    )
    perf_dirt_left_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("perf_dirt_left.perf_dirt_left_id"), nullable=True
    )
    perf_dirt_right_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("perf_dirt_right.perf_dirt_right_id"), nullable=True
    )
    perf_track_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("perf_track.perf_track_id"), nullable=True
    )
    perf_distance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("perf_distance.perf_distance_id"), nullable=True
    )
    best_time_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("best_time.best_time_id"), nullable=True
    )






