"""Queryable in-memory telemetry store for logs, metrics, and traces."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    timestamp: datetime
    level: str
    service: str
    message: str
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricDataPoint(BaseModel):
    timestamp: datetime
    metric_name: str
    service: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


class TelemetryStore:
    """Provides high-performance query methods for log and metric analyst agents."""

    def __init__(self) -> None:
        self.logs: list[LogRecord] = []
        self.metrics: list[MetricDataPoint] = []

    def clear(self) -> None:
        self.logs.clear()
        self.metrics.clear()

    def add_logs(self, logs: list[LogRecord]) -> None:
        self.logs.extend(logs)
        self.logs.sort(key=lambda x: x.timestamp)

    def add_metrics(self, metrics: list[MetricDataPoint]) -> None:
        self.metrics.extend(metrics)
        self.metrics.sort(key=lambda x: x.timestamp)

    def query_logs(
        self,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        pattern: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[LogRecord]:
        results = self.logs
        if service:
            results = [r for r in results if r.service == service]
        if level:
            results = [r for r in results if r.level == level.upper()]
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]
        if pattern:
            pat_lower = pattern.lower()
            results = [r for r in results if pat_lower in r.message.lower()]
        return results[-limit:]

    def query_metrics(
        self,
        metric_name: str,
        service: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[MetricDataPoint]:
        results = [m for m in self.metrics if m.metric_name == metric_name]
        if service:
            results = [m for m in results if m.service == service]
        if start_time:
            results = [m for m in results if m.timestamp >= start_time]
        if end_time:
            results = [m for m in results if m.timestamp <= end_time]
        return results[-limit:]
