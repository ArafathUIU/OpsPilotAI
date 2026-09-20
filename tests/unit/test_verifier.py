"""Unit tests for VerificationAgent recovery monitoring."""

import pytest

from simulator.engine import SimulationEngine
from src.agents.verifier import VerificationAgent
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter
from src.tools.registry import ToolRegistry
from src.tools.remediation_tools import RollbackDeploymentTool
from src.tools.telemetry_tools import GetServiceHealthTool, QueryMetricsTool


@pytest.mark.asyncio
async def test_verification_agent_evaluation():
    simulator = SimulationEngine()
    simulator.load_scenario("redis_pool_exhaustion")

    registry = ToolRegistry()
    registry.register(GetServiceHealthTool(simulator=simulator))
    registry.register(QueryMetricsTool(simulator=simulator))
    registry.register(RollbackDeploymentTool(simulator=simulator))

    provider = MockLLMProvider()
    router = ModelRouter([provider])

    verifier = VerificationAgent(registry=registry, router=router)

    # Perform remediation
    rollback = RollbackDeploymentTool(simulator=simulator)
    await rollback.execute(target_service="payment-service", target_version="v2.4.0")

    # Run verification
    assessment = await verifier.verify_recovery(
        target_service="payment-service",
        executed_action_id="ACT-ROLLBACK-01",
    )

    assert assessment.status == "RECOVERED"
    assert assessment.rollback_recommended is False
    assert "HEALTHY" in assessment.service_statuses.get("payment-service", "")
