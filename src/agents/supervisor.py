"""Supervisor Agent responsible for incident triage and targeted task delegation."""

from src.agents.base import BaseAgent
from src.domain.state import IncidentState, SupervisorPlan
from src.llm.router import TaskTier
from src.observability.logging import get_logger
from src.tools.registry import ToolRegistry, default_registry

logger = get_logger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """You are the Lead SRE Supervisor Agent for OpsPilot AI.
Your responsibility:
1. Receive an incoming incident alert and understand symptoms, severity, and affected services.
2. Determine which specialized investigators are required (Log Analyst, Metrics Analyst, Code & Deployment Analyst).
3. Construct a targeted investigation plan with concrete, focused tasks.
4. DO NOT unconditionally call every agent if the alert clearly does not require it.
5. Provide structured, disciplined reasoning.
"""


class SupervisorAgent(BaseAgent):
    """Orchestrates the initial investigation phase and delegates targeted tasks."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def plan_investigation(self, state: IncidentState) -> SupervisorPlan:
        # Check service health via tool
        health_result = await self.registry.invoke(
            "get_service_health",
            {"service": state.affected_services[0] if state.affected_services else "unknown"},
            caller_role="VIEWER",
            agent_name="SupervisorAgent",
        )
        health_context = health_result.data if health_result.status == "SUCCESS" else {}

        prompt = (
            f"Incident ID: {state.incident_id}\n"
            f"Title: {state.title}\n"
            f"Severity: {state.severity}\n"
            f"Affected Services: {state.affected_services}\n"
            f"Service Topology Context: {health_context}\n\n"
            "Build an investigation plan selecting the necessary specialized analyst agents."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            response_model=SupervisorPlan,
            tier=TaskTier.FAST,
        )
        return response.parsed
