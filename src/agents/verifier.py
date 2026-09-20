"""Post-remediation verification agent monitoring telemetry recovery and rollback triggers."""

from typing import Any

from src.agents.base import BaseAgent
from src.domain.state import VerificationAssessment
from src.llm.router import TaskTier
from src.tools.registry import ToolRegistry, default_registry

VERIFIER_SYSTEM_PROMPT = """You are the Post-Remediation Verification Agent for OpsPilot AI.
Your responsibility:
1. Compare post-remediation runtime metrics (p95 latency, error rates, active connections) against baseline and incident peak values.
2. Check service topology health status.
3. Determine empirical recovery status:
   - 'RECOVERED': Service health is HEALTHY, latency returned to normal baseline (<400ms), 0% error rate.
   - 'PARTIALLY_RECOVERED': Metrics improved substantially but remain above alert thresholds.
   - 'UNCHANGED': Anomalies persist without measurable recovery.
   - 'DEGRADED': Error rates or latencies exacerbated following the action.
4. If the system is DEGRADED, immediately set rollback_recommended=True and explain why.
"""


class VerificationAgent(BaseAgent):
    """Monitors telemetry following remediation execution to verify stabilization."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def verify_recovery(
        self,
        target_service: str,
        executed_action_id: str,
    ) -> VerificationAssessment:
        """Collects post-remediation telemetry and synthesizes empirical verification assessment."""
        # 1. Query latest service health
        health_res = await self.registry.invoke(
            "get_service_health",
            {"service": target_service},
            caller_role="VIEWER",
            agent_name="VerificationAgent",
        )
        service_health = health_res.data if health_res.status == "SUCCESS" else {}

        # 2. Query latest latency metrics
        metric_res = await self.registry.invoke(
            "query_metrics",
            {
                "service": target_service,
                "metric_name": "http_request_duration_p95_seconds",
                "time_window_minutes": 10,
            },
            caller_role="VIEWER",
            agent_name="VerificationAgent",
        )
        metric_data = metric_res.data if metric_res.status == "SUCCESS" else {}

        quarantined = self.quarantine_telemetry(
            {
                "target_service": target_service,
                "executed_action_id": executed_action_id,
                "service_health": service_health,
                "recent_metrics": metric_data,
            }
        )

        prompt = (
            f"Target Service: {target_service}\n"
            f"Executed Action ID: {executed_action_id}\n"
            f"Post-Action Telemetry Observation:\n{quarantined}\n\n"
            "Assess whether the service has empirically recovered and provide a structured VerificationAssessment."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            response_model=VerificationAssessment,
            tier=TaskTier.FAST,
        )
        return response.parsed
