"""Synthetic telemetry generator producing realistic logs, metrics, and traces."""

from datetime import datetime, timedelta

from simulator.scenarios.base import BaseScenario
from simulator.telemetry.store import LogRecord, MetricDataPoint, TelemetryStore


class TelemetryGenerator:
    """Generates synthetic background telemetry and injects incident scenario data."""

    def __init__(self, store: TelemetryStore) -> None:
        self.store = store

    def generate_background_traffic(
        self, start_time: datetime, end_time: datetime, step_seconds: int = 30
    ) -> None:
        """Generates baseline healthy traffic across standard microservices."""
        services = [
            "api-gateway",
            "auth-service",
            "order-service",
            "payment-service",
            "notification-service",
        ]
        cur = start_time
        logs = []
        metrics = []

        while cur <= end_time:
            ts = cur
            for svc in services:
                # Baseline metrics
                metrics.append(
                    MetricDataPoint(
                        timestamp=ts,
                        metric_name="http_request_duration_p95_seconds",
                        service=svc,
                        value=0.25,
                    )
                )
                metrics.append(
                    MetricDataPoint(
                        timestamp=ts,
                        metric_name="process_cpu_percent",
                        service=svc,
                        value=20.0,
                    )
                )
                metrics.append(
                    MetricDataPoint(
                        timestamp=ts,
                        metric_name="memory_usage_percent",
                        service=svc,
                        value=35.0,
                    )
                )
                # Baseline info logs
                logs.append(
                    LogRecord(
                        timestamp=ts,
                        level="INFO",
                        service=svc,
                        message=f"{svc} processing health heartbeat [status=UP, p95=25ms]",
                        trace_id=f"tr-base-{int(ts.timestamp())}-{svc[:4]}",
                    )
                )
            cur += timedelta(seconds=step_seconds)

        self.store.add_logs(logs)
        self.store.add_metrics(metrics)

    def inject_scenario_telemetry(
        self, scenario: BaseScenario, start_time: datetime, end_time: datetime
    ) -> None:
        """Translates scenario-specific raw telemetry into standard store format."""
        raw_logs = scenario.generate_logs(start_time, end_time)
        parsed_logs = []
        for l_item in raw_logs:
            parsed_logs.append(
                LogRecord(
                    timestamp=datetime.fromisoformat(l_item["timestamp"]),
                    level=l_item.get("level", "INFO"),
                    service=l_item.get("service", "unknown"),
                    message=l_item.get("message", ""),
                    trace_id=l_item.get("trace_id"),
                    metadata=l_item,
                )
            )
        self.store.add_logs(parsed_logs)

        raw_metrics = scenario.generate_metrics(start_time, end_time)
        parsed_metrics = []
        for m_name, points in raw_metrics.items():
            for p in points:
                parsed_metrics.append(
                    MetricDataPoint(
                        timestamp=datetime.fromisoformat(p["timestamp"]),
                        metric_name=m_name,
                        service=scenario.ground_truth.affected_services[0],
                        value=float(p["value"]),
                    )
                )
        self.store.add_metrics(parsed_metrics)
