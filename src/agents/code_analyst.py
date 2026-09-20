"""Code & Deployment Agent inspecting commits, diffs, and deploy events."""

from src.agents.base import BaseAgent
from src.domain.state import AnalystAgentOutput, InvestigationTask
from src.llm.router import TaskTier
from src.tools.registry import ToolRegistry, default_registry

CODE_ANALYST_SYSTEM_PROMPT = """You are the Code & Deployment Agent for OpsPilot AI.
Your responsibility:
1. Query deployment history and recent commits for the affected service.
2. Inspect commit diffs and configuration changes (e.g. timeout settings, pool sizes, dependencies).
3. Determine whether any code or configuration change temporally correlates with incident onset.
4. Extract factual Evidence items detailing the exact diff and commit SHA.
"""


class CodeAnalystAgent(BaseAgent):
    """Investigates code changes and deployments to establish causation."""

    def __init__(self, registry: ToolRegistry | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.registry = registry or default_registry

    async def investigate(self, task: InvestigationTask) -> AnalystAgentOutput:
        # 1. Fetch recent deployments
        dep_res = await self.registry.invoke(
            "get_recent_deployments",
            {"service": task.target_service, "limit": 3},
            caller_role="VIEWER",
            agent_name="CodeAnalystAgent",
        )
        deployments = dep_res.data if dep_res.status == "SUCCESS" else []

        # 2. Fetch commit diff if deployment found
        diff_data = ""
        if deployments and len(deployments) > 0:
            commit_sha = deployments[0].get("commit_sha", "")
            if commit_sha:
                diff_res = await self.registry.invoke(
                    "get_commit_diff",
                    {"commit_sha": commit_sha},
                    caller_role="VIEWER",
                    agent_name="CodeAnalystAgent",
                )
                diff_data = diff_res.data.get("diff", "") if diff_res.status == "SUCCESS" else ""

        code_context = {
            "deployments": deployments,
            "latest_deployed_diff": diff_data,
        }

        quarantined = self.quarantine_telemetry(code_context)
        prompt = (
            f"Target Service: {task.target_service}\n"
            f"Query Intent: {task.query_intent}\n"
            f"Deployment & Git Telemetry:\n{quarantined}\n\n"
            "Analyze these code/config changes and extract structured Evidence items."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=CODE_ANALYST_SYSTEM_PROMPT,
            response_model=AnalystAgentOutput,
            tier=TaskTier.FAST,
        )
        return response.parsed
