"""End-to-end integration test validating autonomous remediation and recovery verification."""

import pytest

from simulator.engine import default_simulator
from src.agents.code_analyst import CodeAnalystAgent
from src.agents.critic import CriticAgent
from src.agents.log_analyst import LogAnalystAgent
from src.agents.memory_analyst import IncidentMemoryAgent
from src.agents.metrics_analyst import MetricsAnalystAgent
from src.agents.rca import RCAAgent
from src.agents.remediation_agent import RemediationAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.verifier import VerificationAgent
from src.domain.state import IncidentState
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter
from src.orchestration.graph import IncidentWorkflow
from src.safety.execution_runner import ExecutionRunner


@pytest.mark.asyncio
async def test_full_remediation_and_verification_pipeline():
    # 1. Load the demonstration scenario
    alert = default_simulator.load_scenario("redis_pool_exhaustion")
    assert alert["service"] == "payment-service"

    # 2. Wire router and agents with mock provider
    router = ModelRouter([MockLLMProvider()])
    workflow = IncidentWorkflow(
        supervisor=SupervisorAgent(router=router),
        log_analyst=LogAnalystAgent(router=router),
        metrics_analyst=MetricsAnalystAgent(router=router),
        code_analyst=CodeAnalystAgent(router=router),
        memory_analyst=IncidentMemoryAgent(router=router),
        rca=RCAAgent(router=router),
        critic=CriticAgent(router=router),
        remediation_agent=RemediationAgent(router=router),
        verifier=VerificationAgent(router=router),
        execution_runner=ExecutionRunner(),
    )
    graph = workflow.build_graph()

    # 3. Create root state
    initial_state = IncidentState(
        incident_id="inc-redis-remediation-01",
        title=alert["title"],
        severity="SEV1",
        affected_services=[alert["service"]],
    )

    # 4. Run entire end-to-end workflow
    final_output = await graph.ainvoke(initial_state)

    # 5. Verify the incident was fully resolved
    assert final_output["current_stage"] == "RESOLVED"

    # Verify remediation plan was formulated with risk assessment
    plan = final_output["remediation_plan"]
    assert plan is not None
    assert len(plan.actions) > 0
    first_action = plan.actions[0]
    assert first_action.action_type == "rollback_deployment"
    assert first_action.risk_tier in ["HIGH", "CRITICAL"]
    assert first_action.idempotency_key != ""

    # Verify execution runner ran the action
    exec_results = final_output["execution_results"]
    assert len(exec_results) > 0
    assert exec_results[0].status == "SUCCESS"
    assert "rolled back" in exec_results[0].output.lower()

    # Verify post-remediation verification confirmed recovery
    verification = final_output["verification"]
    assert verification is not None
    assert verification.status == "RECOVERED"
    assert verification.rollback_recommended is False

    # Verify complete timeline transitions
    timeline = final_output["timeline"]
    stages = [t.stage for t in timeline]
    assert "PLANNING" in stages
    assert "INVESTIGATING" in stages
    assert "ANALYZING" in stages
    assert "CRITIQUING" in stages
    assert "REMEDIATION_PLANNING" in stages
    assert "EXECUTING" in stages
    assert "VERIFYING" in stages
