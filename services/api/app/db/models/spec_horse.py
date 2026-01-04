from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecHorse(Base):
    __tablename__ = "horse"

    horse_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    nar_horse_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_md_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    coat: Mapped[str | None] = mapped_column(String, nullable=True)

    sire: Mapped[str | None] = mapped_column(String, nullable=True)
    dam: Mapped[str | None] = mapped_column(String, nullable=True)
    dam_sire: Mapped[str | None] = mapped_column(String, nullable=True)
    breeder: Mapped[str | None] = mapped_column(String, nullable=True)


