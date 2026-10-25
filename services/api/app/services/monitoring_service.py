import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.errors import AppError
from app.db.models.monitoring import (
    MetricMinute,
    MonitoringAlarm,
    MonitoringEvent,
    SystemMetric,
)
from app.schemas.monitoring import MetricSample

SERIES = (
    "cpu_percent",
    "memory_percent",
    "disk_percent",
    "net_rx_bytes_sec",
    "net_tx_bytes_sec",
    "disk_read_bytes_sec",
    "disk_write_bytes_sec",
)


def aware(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=UTC)
        if value.tzinfo is None
        else value.astimezone(UTC)
    )


def key(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def series_values(data: dict) -> dict:
    return {
        **{name: data.get(name) for name in SERIES},
        "disk_percent": max(
            (d["percent"] for d in data.get("disks", [])), default=None
        ),
    }


class MonitoringService:
    def __init__(self, db):
        self.db = db

    def latest_row(self, host_id=None):
        query = select(SystemMetric)
        if host_id:
            query = query.where(SystemMetric.host_id == host_id)
        return self.db.scalar(
            query.order_by(SystemMetric.sampled_at.desc()).limit(1)
        )

    def ingest(self, sample: MetricSample, now=None):
        now = now or datetime.now(UTC)
        at = sample.sampled_at.astimezone(UTC)
        if (
            sample.memory_available_bytes > sample.memory_total_bytes
            or sample.swap_used_bytes > sample.swap_total_bytes
        ):
            raise AppError.bad_request(
                "available/used memory exceeds total capacity"
            )
        if at > now + timedelta(seconds=30) or at < now - timedelta(
            minutes=15
        ):
            raise AppError.bad_request(
                "sample clock is outside the accepted 15-minute buffer / 30-second future window"
            )
        sample_id = key(sample.host_id, sample.boot_id, sample.sequence)
        if self.db.get(SystemMetric, sample_id):
            return {"accepted": False, "duplicate": True}
        latest = self.latest_row(sample.host_id)
        data = sample.model_dump(mode="json")
        self.db.add(
            SystemMetric(
                id=sample_id,
                host_id=sample.host_id,
                sampled_at=at,
                received_at=now,
                data=data,
            )
        )
        minute = at.replace(second=0, microsecond=0)
        bucket_id = key(sample.host_id, minute.isoformat())
        bucket = self.db.get(MetricMinute, bucket_id)
        if bucket is None:
            bucket = MetricMinute(
                id=bucket_id,
                host_id=sample.host_id,
                sampled_at=minute,
                count=0,
                data={},
            )
            self.db.add(bucket)
        aggregates = dict(bucket.data)
        for name, value in series_values(data).items():
            if value is None:
                continue
            prev = aggregates.get(name, {"sum": 0, "count": 0, "max": value})
            aggregates[name] = {
                "sum": prev["sum"] + value,
                "count": prev["count"] + 1,
                "max": max(prev["max"], value),
            }
        bucket.count += 1
        bucket.data = aggregates
        if latest is None or at > aware(latest.sampled_at):
            self._alarms(sample, at)
        # Retention uses server time, so buffered samples cannot extend retention.
        if now.second < 10:
            self.db.execute(
                delete(SystemMetric)
                .where(SystemMetric.sampled_at < now - timedelta(days=1))
                .execution_options(synchronize_session=False)
            )
            self.db.execute(
                delete(MetricMinute)
                .where(MetricMinute.sampled_at < now - timedelta(days=7))
                .execution_options(synchronize_session=False)
            )
            self.db.execute(
                delete(MonitoringEvent)
                .where(MonitoringEvent.resolved_at < now - timedelta(days=30))
                .execution_options(synchronize_session=False)
            )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if self.db.get(SystemMetric, sample_id):
                return {"accepted": False, "duplicate": True}
            raise AppError.conflict("concurrent metrics update; retry sample")
        return {"accepted": True, "duplicate": False}

    def _alarms(self, sample, at):
        rules = [
            (
                "CPU",
                sample.cpu_percent,
                settings.monitor_cpu_warning,
                settings.monitor_cpu_critical,
                300,
            ),
            (
                "メモリ",
                sample.memory_percent,
                settings.monitor_memory_warning,
                settings.monitor_memory_critical,
                300,
            ),
        ]
        rules.extend(
            (
                f"ディスク: {d.path}",
                d.percent,
                settings.monitor_disk_warning,
                settings.monitor_disk_critical,
                0,
            )
            for d in sample.disks
        )
        for resource, value, warning, critical, duration in rules:
            for level, threshold in (
                ("warning", warning),
                ("critical", critical),
            ):
                self._alarm(
                    sample.host_id,
                    resource,
                    level,
                    value,
                    threshold,
                    duration,
                    at,
                )
        if settings.monitor_disk_min_free_bytes:
            for disk in sample.disks:
                shortage = max(
                    0,
                    settings.monitor_disk_min_free_bytes
                    - disk.available_bytes,
                )
                self._alarm(
                    sample.host_id,
                    f"空き容量: {disk.path}",
                    "critical",
                    shortage,
                    1,
                    0,
                    at,
                    message=f"{disk.path} の空き容量が {settings.monitor_disk_min_free_bytes:,} bytes 未満",
                )

    def _alarm(
        self,
        host_id,
        resource,
        level,
        value,
        threshold,
        duration,
        at,
        message=None,
    ):
        alarm_id = key(host_id, resource, level)
        alarm = self.db.get(MonitoringAlarm, alarm_id)
        if alarm is None:
            alarm = MonitoringAlarm(
                id=alarm_id,
                host_id=host_id,
                resource=resource,
                level=level,
                updated_at=at,
                data={},
            )
            self.db.add(alarm)
        state = dict(alarm.data)
        if (at - aware(alarm.updated_at)).total_seconds() > 30:
            state.pop("since", None)
            state.pop("below_since", None)
        alarm.updated_at = at
        if value is None:
            state.pop("since", None)
            state.pop("below_since", None)
        elif value >= threshold:
            state.pop("below_since", None)
            state.setdefault("since", at.isoformat())
            if (
                not state.get("event_id")
                and (
                    at - datetime.fromisoformat(state["since"])
                ).total_seconds()
                >= duration
            ):
                event_id = uuid.uuid4().hex
                message = (
                    message
                    or f"{resource} が閾値 {threshold:g}% 以上"
                    + (f"で{duration // 60}分継続" if duration else "")
                )
                self.db.add(
                    MonitoringEvent(
                        id=event_id,
                        host_id=host_id,
                        resource=resource,
                        level=level,
                        message=message,
                        started_at=at,
                        resolved_at=None,
                    )
                )
                state["event_id"] = event_id
        else:
            state.pop("since", None)
            if state.get("event_id"):
                state.setdefault("below_since", at.isoformat())
                if (
                    at - datetime.fromisoformat(state["below_since"])
                ).total_seconds() >= 60:
                    event = self.db.get(MonitoringEvent, state["event_id"])
                    if event:
                        event.resolved_at = at
                    state = {}
        alarm.data = state

    def latest(self, host_id=None, now=None):
        now = now or datetime.now(UTC)
        row = self.latest_row(host_id)
        if not row:
            return {
                "status": "unknown",
                "sample": None,
                "age_sec": None,
                "alerts": [],
                "server_time": now,
                "thresholds": self.thresholds(),
            }
        age = max(0, (now - aware(row.sampled_at)).total_seconds())
        alerts = self.events(row.host_id, active_only=True)["items"]
        status = (
            "unavailable"
            if age >= 60
            else "stale"
            if age >= 30
            else "critical"
            if any(a["level"] == "critical" for a in alerts)
            else "warning"
            if alerts or row.data.get("errors")
            else "ok"
        )
        return {
            "status": status,
            "sample": row.data,
            "age_sec": age,
            "alerts": alerts,
            "server_time": now,
            "received_at": aware(row.received_at),
            "thresholds": self.thresholds(),
        }

    @staticmethod
    def thresholds():
        return {
            "cpu": [
                settings.monitor_cpu_warning,
                settings.monitor_cpu_critical,
            ],
            "memory": [
                settings.monitor_memory_warning,
                settings.monitor_memory_critical,
            ],
            "disk": [
                settings.monitor_disk_warning,
                settings.monitor_disk_critical,
            ],
        }

    def history(self, hours, host_id=None, now=None):
        now = now or datetime.now(UTC)
        latest = self.latest_row(host_id)
        host_id = host_id or (latest.host_id if latest else None)
        start = now - timedelta(hours=hours)
        resolution = 10 if hours == 1 else 120 if hours == 24 else 600
        points = {}
        model = SystemMetric if hours == 1 else MetricMinute
        rows = self.db.scalars(
            select(model)
            .where(
                model.host_id == host_id,
                model.sampled_at >= start,
                model.sampled_at <= now,
            )
            .order_by(model.sampled_at)
        ).all()
        for row in rows:
            timestamp = (
                int(aware(row.sampled_at).timestamp())
                // resolution
                * resolution
            )
            point = points.setdefault(timestamp, {})
            values = (
                {
                    name: {"sum": value, "count": 1, "max": value}
                    for name, value in series_values(row.data).items()
                    if value is not None
                }
                if hours == 1
                else row.data
            )
            for name, value in values.items():
                acc = point.setdefault(
                    name, {"sum": 0, "count": 0, "max": value["max"]}
                )
                acc["sum"] += value["sum"]
                acc["count"] += value["count"]
                acc["max"] = max(acc["max"], value["max"])
        result = [
            {
                "at": datetime.fromtimestamp(timestamp, UTC),
                "values": {
                    name: value["sum"] / value["count"]
                    for name, value in point.items()
                },
                "max_values": {
                    name: value["max"] for name, value in point.items()
                },
                "sample_counts": {
                    name: value["count"] for name, value in point.items()
                },
            }
            for timestamp, point in sorted(points.items())
        ]
        return {
            "host_id": host_id,
            "start": start,
            "end": now,
            "resolution_sec": resolution,
            "points": result,
        }

    def events(self, host_id=None, active_only=False, limit=100):
        if not host_id:
            row = self.latest_row()
            host_id = row.host_id if row else None
        query = select(MonitoringEvent).where(
            MonitoringEvent.host_id == host_id
        )
        if active_only:
            query = query.where(MonitoringEvent.resolved_at.is_(None))
        rows = self.db.scalars(
            query.order_by(MonitoringEvent.started_at.desc()).limit(limit)
        ).all()
        return {
            "items": [
                {
                    "id": r.id,
                    "resource": r.resource,
                    "level": r.level,
                    "message": r.message,
                    "started_at": aware(r.started_at),
                    "resolved_at": aware(r.resolved_at)
                    if r.resolved_at
                    else None,
                }
                for r in rows
            ]
        }
