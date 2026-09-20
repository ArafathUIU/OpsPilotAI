"""Standardized base classes and result types for agent tool invocations."""

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.observability.logging import get_logger

logger = get_logger(__name__)


class ToolResult(BaseModel):
    """Standardized output returned by every tool invocation."""

    tool_name: str
    status: Literal["SUCCESS", "FAILED", "PERMISSION_DENIED"]
    data: Any = None
    error_message: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseTool(ABC):
    """Abstract base class for all OpsPilot investigation and remediation tools."""

    name: str
    description: str
    required_role: str = "OPERATOR"  # VIEWER, OPERATOR, ADMIN

    @abstractmethod
    async def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Concrete tool implementation logic."""
        pass

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes the tool with deterministic timing, error capture, and auditing."""
        start_time = time.perf_counter()
        try:
            output_data = await self._run(**kwargs)
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            return ToolResult(
                tool_name=self.name,
                status="SUCCESS",
                data=output_data,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Tool [{self.name}] execution failed: {exc}", exc_info=True)
            return ToolResult(
                tool_name=self.name,
                status="FAILED",
                error_message=str(exc),
                duration_ms=duration,
            )
