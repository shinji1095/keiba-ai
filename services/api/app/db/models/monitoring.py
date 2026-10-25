from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import JSONValue


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(String(120), index=True)
    sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONValue)


class MetricMinute(Base):
    __tablename__ = "system_metric_minutes"
    __table_args__ = (
        Index("ix_metric_minute_host_time", "host_id", "sampled_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(String(120))
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(Integer)
    # Per-series sums, maxima and counts. Null observations are not averaged as zero.
    data: Mapped[dict] = mapped_column(JSONValue)


class MonitoringAlarm(Base):
    __tablename__ = "system_monitoring_alarms"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(String(120), index=True)
    resource: Mapped[str] = mapped_column(String(600))
    level: Mapped[str] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONValue)


class MonitoringEvent(Base):
    __tablename__ = "system_monitoring_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    host_id: Mapped[str] = mapped_column(String(120), index=True)
    resource: Mapped[str] = mapped_column(String(600))
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(1000))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
