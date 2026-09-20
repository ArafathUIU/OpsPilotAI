"""Historical Incident Memory Agent querying episodic postmortems and lessons learned."""

from typing import Any

from src.agents.base import BaseAgent
from src.domain.state import AnalystAgentOutput, InvestigationTask
from src.llm.router import TaskTier
from src.tools.registry import ToolRegistry, default_registry

MEMORY_ANALYST_SYSTEM_PROMPT = """You are the Incident Memory & Knowledge Agent for OpsPilot AI.
Your responsibility:
1. Search historical incident postmortems using semantic similarity to the current failure.
2. Identify whether this incident matches recurring failure modes (e.g. pool exhaustion, memory leaks, misconfigurations).
3. Extract proven remediations and prevention measures previously applied.
4. Synthesize factual Evidence items (type='memory') documenting previous incident IDs, similarity, and verified fixes.
"""


class IncidentMemoryAgent(BaseAgent):
    """Retrieves and analyzes past incident postmortems from episodic memory."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def investigate(self, task: InvestigationTask) -> AnalystAgentOutput:
        # Query episodic memory via ToolRegistry
        mem_res = await self.registry.invoke(
            "search_incident_memory",
            {
                "query": task.query_intent,
                "service": task.target_service,
                "limit": 3,
            },
            caller_role="VIEWER",
            agent_name="IncidentMemoryAgent",
        )

        matches = mem_res.data.get("matches", []) if mem_res.status == "SUCCESS" else []
        formatted_context = (
            mem_res.data.get("formatted_context", "") if mem_res.status == "SUCCESS" else ""
        )

        quarantined = self.quarantine_telemetry(
            {
                "query": task.query_intent,
                "matches": matches,
                "formatted_context": formatted_context,
            }
        )

        prompt = (
            f"Target Service: {task.target_service}\n"
            f"Query Intent: {task.query_intent}\n"
            f"Retrieved Historical Postmortems:\n{quarantined}\n\n"
            "Analyze these past incidents and extract structured Evidence items (type='memory') "
            "highlighting similar past root causes and effective remediations."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=MEMORY_ANALYST_SYSTEM_PROMPT,
            response_model=AnalystAgentOutput,
            tier=TaskTier.FAST,
        )
        return response.parsed
