from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class DiskMetric(BaseModel):
    path: str = Field(max_length=512)
    label: str = Field(max_length=120)
    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)
    percent: float = Field(ge=0, le=100, allow_inf_nan=False)


class MetricSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    host_id: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=120)
    scope: Literal["host", "vm", "container"]
    boot_id: str = Field(min_length=1, max_length=120)
    sequence: int = Field(ge=0)
    sampled_at: AwareDatetime
    uptime_sec: float = Field(ge=0, allow_inf_nan=False)
    cpu_count: int = Field(ge=1, le=4096)
    cpu_percent: float | None = Field(
        default=None, ge=0, le=100, allow_inf_nan=False
    )
    cpu_per_core: list[
        Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)] | None
    ] = Field(default_factory=list, max_length=4096)
    memory_total_bytes: int = Field(ge=1)
    memory_available_bytes: int = Field(ge=0)
    memory_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    swap_total_bytes: int = Field(ge=0)
    swap_used_bytes: int = Field(ge=0)
    disks: list[DiskMetric] = Field(default_factory=list, max_length=64)
    net_rx_bytes_sec: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    net_tx_bytes_sec: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    disk_read_bytes_sec: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    disk_write_bytes_sec: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    temperature_c: float | None = Field(default=None, allow_inf_nan=False)
    temperature_sensor: str | None = Field(default=None, max_length=120)
    network_interfaces: list[str] = Field(default_factory=list, max_length=64)
    errors: list[str] = Field(default_factory=list, max_length=100)


class MonitoringEventView(BaseModel):
    id: str
    resource: str
    level: str
    message: str
    started_at: datetime
    resolved_at: datetime | None


class MetricThresholds(BaseModel):
    cpu: list[float]
    memory: list[float]
    disk: list[float]


class MetricStatus(BaseModel):
    status: Literal[
        "ok", "unknown", "stale", "unavailable", "warning", "critical"
    ]
    sample: MetricSample | None
    age_sec: float | None
    alerts: list[MonitoringEventView]
    server_time: datetime
    received_at: datetime | None = None
    thresholds: MetricThresholds


class HistoryPoint(BaseModel):
    at: datetime
    values: dict[str, float]
    max_values: dict[str, float]
    sample_counts: dict[str, int]


class MetricHistory(BaseModel):
    host_id: str | None
    start: datetime
    end: datetime
    resolution_sec: int
    points: list[HistoryPoint]


class MetricEventList(BaseModel):
    items: list[MonitoringEventView]


class MetricReceipt(BaseModel):
    accepted: bool
    duplicate: bool
