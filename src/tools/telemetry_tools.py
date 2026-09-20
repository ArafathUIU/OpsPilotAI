from typing import Any

from simulator.engine import SimulationEngine, default_simulator
from src.tools.base import BaseTool


class QueryLogsTool(BaseTool):
    name = "query_logs"
    description = "Queries structured application logs filtered by service, time window, log level, and message pattern."
    required_role = "VIEWER"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(
        self,
        service: str | None = None,
        pattern: str | None = None,
        level: str | None = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> list[dict]:
        records = self.simulator.telemetry_store.query_logs(
            service=service,
            pattern=pattern,
            level=level,
            limit=limit,
        )
        return [r.model_dump(mode="json") for r in records]


class QueryMetricsTool(BaseTool):
    name = "query_metrics"
    description = "Queries time-series metric data points (latency, error rate, CPU, active connections) by metric name."
    required_role = "VIEWER"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(
        self,
        metric_name: str,
        service: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[dict]:
        data_points = self.simulator.telemetry_store.query_metrics(
            metric_name=metric_name,
            service=service,
            limit=limit,
        )
        return [p.model_dump(mode="json") for p in data_points]


class GetServiceHealthTool(BaseTool):
    name = "get_service_health"
    description = (
        "Returns current operational health status and dependency links for a given microservice."
    )
    required_role = "VIEWER"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, service: str, **kwargs: Any) -> dict:
        node = self.simulator.topology.get_service(service)
        if not node:
            return {"service": service, "status": "UNKNOWN", "dependencies": []}
        return {
            "service": node.name,
            "status": node.status,
            "tier": node.tier,
            "dependencies": node.dependencies,
            "upstream_dependents": self.simulator.topology.get_upstream_dependents(service),
            "version": node.version,
        }
