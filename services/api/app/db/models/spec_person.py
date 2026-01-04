from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpecPerson(Base):
    __tablename__ = "person"

    person_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    # NOTE: migration allows NULL, but we store empty string to make lookups deterministic.
    affiliation: Mapped[str] = mapped_column(String, nullable=False, default="")


