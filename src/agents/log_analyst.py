"""Log Analyst Agent specialized in log parsing, error rate spikes, and stack trace isolation."""

from src.agents.base import BaseAgent
from src.domain.state import AnalystAgentOutput, InvestigationTask
from src.llm.router import TaskTier
from src.tools.registry import ToolRegistry, default_registry

LOG_ANALYST_SYSTEM_PROMPT = """You are the Log Analyst Agent for OpsPilot AI.
Your responsibility:
1. Examine application logs returned by tool queries.
2. Identify repeated exceptions, sudden frequency spikes, and relevant error messages.
3. Transform factual findings into structured Evidence items.
4. Assign relevance scores (0.0 to 1.0) and include raw references.
5. Do NOT invent logs that do not exist in the telemetry.
"""


class LogAnalystAgent(BaseAgent):
    """Investigates application logs to extract discrete evidence items."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def investigate(self, task: InvestigationTask) -> AnalystAgentOutput:
        tool_res = await self.registry.invoke(
            "query_logs",
            {"service": task.target_service, "limit": 40},
            caller_role="VIEWER",
            agent_name="LogAnalystAgent",
        )
        logs = tool_res.data if tool_res.status == "SUCCESS" else []

        quarantined_logs = self.quarantine_telemetry(logs)
        prompt = (
            f"Target Service: {task.target_service}\n"
            f"Query Intent: {task.query_intent}\n"
            f"Application Logs:\n{quarantined_logs}\n\n"
            "Analyze these logs and produce structured Evidence items for any anomalies or exceptions."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=LOG_ANALYST_SYSTEM_PROMPT,
            response_model=AnalystAgentOutput,
            tier=TaskTier.FAST,
        )
        return response.parsed
