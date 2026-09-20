"""Unit tests for remediation tools and ExecutionRunner idempotency."""

import pytest

from simulator.engine import SimulationEngine
from src.domain.state import RemediationAction
from src.safety.execution_runner import ExecutionRunner
from src.tools.registry import ToolRegistry
from src.tools.remediation_tools import (
    ClearCacheTool,
    ModifyConfigurationTool,
    RestartServiceTool,
    RollbackDeploymentTool,
    ScaleReplicasTool,
)


@pytest.mark.asyncio
async def test_remediation_tools_execution():
    simulator = SimulationEngine()
    simulator.load_scenario("redis_pool_exhaustion")

    # 1. Test RestartServiceTool
    restart_tool = RestartServiceTool(simulator=simulator)
    res = await restart_tool.execute(target_service="payment-service")
    assert res.status == "SUCCESS"
    assert "restarted" in res.data["message"].lower()

    # 2. Test RollbackDeploymentTool
    rollback_tool = RollbackDeploymentTool(simulator=simulator)
    res = await rollback_tool.execute(target_service="payment-service", target_version="v2.4.0")
    assert res.status == "SUCCESS"
    assert "rolled back" in res.data["message"].lower()
    assert simulator.active_scenario.is_remediated is True

    # 3. Test ScaleReplicasTool
    scale_tool = ScaleReplicasTool(simulator=simulator)
    res = await scale_tool.execute(target_service="payment-service", replicas=3)
    assert res.status == "SUCCESS"

    # 4. Test ModifyConfigurationTool
    config_tool = ModifyConfigurationTool(simulator=simulator)
    res = await config_tool.execute(target_service="payment-service", max_connections=100)
    assert res.status == "SUCCESS"

    # 5. Test ClearCacheTool
    cache_tool = ClearCacheTool(simulator=simulator)
    res = await cache_tool.execute(target_service="payment-service")
    assert res.status == "SUCCESS"


@pytest.mark.asyncio
async def test_execution_runner_idempotency_and_tracking():
    simulator = SimulationEngine()
    simulator.load_scenario("redis_pool_exhaustion")

    registry = ToolRegistry()
    registry.register(RollbackDeploymentTool(simulator=simulator))
    runner = ExecutionRunner(registry=registry)

    action = RemediationAction(
        action_id="ACT-ROLLBACK-01",
        action_type="rollback_deployment",
        target_service="payment-service",
        parameters={"target_version": "v2.4.0"},
        description="Rollback payment-service",
        rationale="Fix pool starvation",
        rollback_plan="Redeploy v2.4.1",
        idempotency_key="key-idemp-12345",
    )

    # First execution succeeds
    res1 = await runner.execute_action(action, caller_role="OPERATOR")
    assert res1.status == "SUCCESS"
    assert "rolled back" in res1.output.lower()

    # Second execution with same idempotency key is skipped idempotently
    res2 = await runner.execute_action(action, caller_role="OPERATOR")
    assert res2.status == "SUCCESS"
    assert "already executed idempotently" in res2.output
