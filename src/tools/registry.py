"""Deterministic tool registry and authorization policy engine."""

import re
from typing import Any

from src.observability.logging import get_logger
from src.tools.base import BaseTool, ToolResult
from src.tools.code_tools import GetCommitDiffTool, GetRecentCommitsTool, GetRecentDeploymentsTool
from src.tools.memory_tools import SearchIncidentMemoryTool
from src.tools.telemetry_tools import GetServiceHealthTool, QueryLogsTool, QueryMetricsTool

logger = get_logger(__name__)

# RBAC Role hierarchy weights
ROLE_HIERARCHY = {
    "VIEWER": 1,
    "OPERATOR": 2,
    "ADMIN": 3,
}

SECRET_PARAM_PATTERN = re.compile(r"(?i)(password|secret|key|token|auth|credential)")


class ToolRegistry:
    """Central registry enforcing deterministic role permissions and parameter auditing."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.register(QueryLogsTool())
        self.register(QueryMetricsTool())
        self.register(GetServiceHealthTool())
        self.register(GetRecentDeploymentsTool())
        self.register(GetRecentCommitsTool())
        self.register(GetCommitDiffTool())
        self.register(SearchIncidentMemoryTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def _sanitize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Redacts sensitive arguments before logging."""
        sanitized: dict[str, Any] = {}
        for k, v in params.items():
            if SECRET_PARAM_PATTERN.search(k):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_params(v)
            else:
                sanitized[k] = v
        return sanitized

    async def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller_role: str = "OPERATOR",
        agent_name: str = "unknown_agent",
    ) -> ToolResult:
        """Invokes a tool after verifying caller authorization in deterministic application code."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                status="FAILED",
                error_message=f"Tool [{tool_name}] is not registered in ToolRegistry",
            )

        caller_weight = ROLE_HIERARCHY.get(caller_role.upper(), 0)
        required_weight = ROLE_HIERARCHY.get(tool.required_role.upper(), 99)

        # Deterministic RBAC Authorization Check
        if caller_weight < required_weight:
            logger.warning(
                f"Security: Agent [{agent_name}] with role [{caller_role}] denied access to [{tool_name}] "
                f"(requires [{tool.required_role}])"
            )
            return ToolResult(
                tool_name=tool_name,
                status="PERMISSION_DENIED",
                error_message=(
                    f"Access Denied: Tool [{tool_name}] requires role [{tool.required_role}], "
                    f"but caller has [{caller_role}]"
                ),
            )

        sanitized_args = self._sanitize_params(arguments)
        logger.info(
            f"Agent [{agent_name}] invoking tool [{tool_name}] with params {sanitized_args}"
        )

        result = await tool.execute(**arguments)
        return result


# Global default tool registry
default_registry = ToolRegistry()
