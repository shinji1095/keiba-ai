from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Venue(Base):
    __tablename__ = "venues"

    baba_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    venue_name: Mapped[str] = mapped_column(String(255), nullable=False)
