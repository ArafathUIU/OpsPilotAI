"""Metrics Analyst Agent investigating time-series telemetry."""

from src.agents.base import BaseAgent
from src.domain.state import AnalystAgentOutput, InvestigationTask
from src.llm.router import TaskTier
from src.tools.registry import ToolRegistry, default_registry

METRICS_ANALYST_SYSTEM_PROMPT = """You are the Metrics Analyst Agent for OpsPilot AI.
Your responsibility:
1. Examine time-series metric data points (latency, error rates, connection pools, CPU/memory).
2. Compare baseline versus incident period values.
3. Quantify degradation ratios (e.g. latency +800%, connection saturation).
4. Return structured Evidence items referencing concrete metric queries and values.
"""


class MetricsAnalystAgent(BaseAgent):
    """Investigates metric anomalies and quantifies degradation."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def investigate(self, task: InvestigationTask) -> AnalystAgentOutput:
        # Query latency and connection metrics
        lat_res = await self.registry.invoke(
            "query_metrics",
            {"metric_name": "p95_latency_ms", "service": task.target_service, "limit": 20},
            caller_role="VIEWER",
            agent_name="MetricsAnalystAgent",
        )
        conn_res = await self.registry.invoke(
            "query_metrics",
            {
                "metric_name": "redis_active_connections",
                "service": task.target_service,
                "limit": 20,
            },
            caller_role="VIEWER",
            agent_name="MetricsAnalystAgent",
        )

        metrics_summary = {
            "p95_latency": lat_res.data if lat_res.status == "SUCCESS" else [],
            "connections": conn_res.data if conn_res.status == "SUCCESS" else [],
        }

        quarantined = self.quarantine_telemetry(metrics_summary)
        prompt = (
            f"Target Service: {task.target_service}\n"
            f"Query Intent: {task.query_intent}\n"
            f"Metrics Data:\n{quarantined}\n\n"
            "Analyze these metrics and extract structured Evidence items for abnormal thresholds."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=METRICS_ANALYST_SYSTEM_PROMPT,
            response_model=AnalystAgentOutput,
            tier=TaskTier.FAST,
        )
        return response.parsed
