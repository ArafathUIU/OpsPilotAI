"""Safe remediation execution runner enforcing idempotency and audit tracking."""

import time
from typing import Any

from src.domain.state import ActionExecutionResult, RemediationAction
from src.observability.logging import get_logger
from src.tools.registry import ToolRegistry, default_registry

logger = get_logger(__name__)


class ExecutionRunner:
    """Safely dispatches permitted remediation actions with idempotency guards and timing."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or default_registry
        self._executed_idempotency_keys: set[str] = set()

    async def execute_action(
        self,
        action: RemediationAction,
        caller_role: str = "OPERATOR",
    ) -> ActionExecutionResult:
        """Executes a remediation action through the deterministic tool registry."""
        # 1. Idempotency guard
        if action.idempotency_key and action.idempotency_key in self._executed_idempotency_keys:
            logger.warning(
                f"Action [{action.action_id}] skipped: idempotency key [{action.idempotency_key}] already executed"
            )
            return ActionExecutionResult(
                action_id=action.action_id,
                status="SUCCESS",
                output="Skipped: action was already executed idempotently.",
                duration_ms=0.0,
            )

        logger.info(
            f"Executing remediation action [{action.action_id}] ({action.action_type}) on service [{action.target_service}]"
        )
        start_time = time.perf_counter()

        # Map ActionType to registered tool name
        tool_name = action.action_type
        tool = self.registry.get_tool(tool_name)
        if not tool:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            return ActionExecutionResult(
                action_id=action.action_id,
                status="FAILED",
                output="",
                error_message=f"No executable tool found for action type '{tool_name}'",
                duration_ms=duration,
            )

        # Merge target_service into tool arguments
        tool_args: dict[str, Any] = {
            "target_service": action.target_service,
            **action.parameters,
        }

        # Invoke through registry to enforce RBAC and auditing
        tool_result = await self.registry.invoke(
            tool_name=tool_name,
            arguments=tool_args,
            caller_role=caller_role,
            agent_name="ExecutionRunner",
        )

        duration = round((time.perf_counter() - start_time) * 1000, 2)

        if tool_result.status == "SUCCESS":
            if action.idempotency_key:
                self._executed_idempotency_keys.add(action.idempotency_key)
            msg = tool_result.data.get("message", "Remediation action completed successfully")
            return ActionExecutionResult(
                action_id=action.action_id,
                status="SUCCESS",
                output=msg,
                duration_ms=duration,
            )
        else:
            return ActionExecutionResult(
                action_id=action.action_id,
                status="FAILED",
                output="",
                error_message=tool_result.error_message or "Tool execution failed",
                duration_ms=duration,
            )

    async def execute_rollback(
        self,
        action: RemediationAction,
        caller_role: str = "OPERATOR",
    ) -> ActionExecutionResult:
        """Applies compensatory rollback steps when verification detects worsening degradation."""
        logger.warning(
            f"Initiating compensation rollback for action [{action.action_id}]: {action.rollback_plan}"
        )
        start_time = time.perf_counter()

        # Execute rollback logic based on action type
        if action.action_type == "rollback_deployment":
            # If rolling back caused degradation, we redeploy previous stable version
            rollback_action = action.model_copy(
                update={"parameters": {"target_version": action.parameters.get("previous_version")}}
            )
            res = await self.execute_action(rollback_action, caller_role=caller_role)
            return res.model_copy(update={"status": "ROLLED_BACK"})

        elif action.action_type == "modify_configuration":
            # Revert configuration patch
            revert_action = action.model_copy(
                update={"parameters": action.parameters.get("rollback_config", {})}
            )
            res = await self.execute_action(revert_action, caller_role=caller_role)
            return res.model_copy(update={"status": "ROLLED_BACK"})

        # Default fallback restart
        restart_action = RemediationAction(
            action_id=f"rb-{action.action_id}",
            action_type="restart_service",
            target_service=action.target_service,
            description="Compensatory pod restart during rollback",
            rationale="Reset pod state following failed action",
            rollback_plan="None",
            risk_tier="HIGH",
        )
        res = await self.execute_action(restart_action, caller_role=caller_role)
        duration = round((time.perf_counter() - start_time) * 1000, 2)
        return ActionExecutionResult(
            action_id=action.action_id,
            status="ROLLED_BACK",
            output=f"Executed compensatory rollback: {res.output}",
            duration_ms=duration,
        )
