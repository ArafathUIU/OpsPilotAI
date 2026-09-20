"""End-to-end integration test of the LangGraph multi-agent investigation workflow."""

import pytest

from simulator.engine import default_simulator
from src.agents.code_analyst import CodeAnalystAgent
from src.agents.critic import CriticAgent
from src.agents.log_analyst import LogAnalystAgent
from src.agents.memory_analyst import IncidentMemoryAgent
from src.agents.metrics_analyst import MetricsAnalystAgent
from src.agents.rca import RCAAgent
from src.agents.supervisor import SupervisorAgent
from src.domain.state import IncidentState
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter
from src.orchestration.graph import IncidentWorkflow


@pytest.mark.asyncio
async def test_full_investigation_workflow_on_redis_pool_exhaustion():
    # 1. Load the demonstration scenario into the simulator
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
    )
    graph = workflow.build_graph()

    # 3. Initialize root LangGraph state
    initial_state = IncidentState(
        incident_id="inc-redis-test-01",
        title=alert["title"],
        severity="SEV1",
        affected_services=[alert["service"]],
    )

    # 4. Execute the LangGraph state machine
    final_output = await graph.ainvoke(initial_state)

    # 5. Assertions on completed state
    assert final_output["current_stage"] == "RESOLVED"

    # Parallel evidence gathered from logs, metrics, and code diffs
    evidence = final_output["evidence"]
    assert len(evidence) >= 3
    evidence_types = {e.type for e in evidence}
    assert "log" in evidence_types
    assert "metric" in evidence_types
    assert "code" in evidence_types
    assert "memory" in evidence_types

    # RCA generated hypotheses citing valid evidence IDs
    hypotheses = final_output["hypotheses"]
    assert len(hypotheses) > 0
    selected_hypo = final_output["selected_hypothesis"]
    assert selected_hypo is not None
    assert "Redis" in selected_hypo.title
    assert len(selected_hypo.supporting_evidence_ids) >= 2

    # Verify all cited evidence IDs exist in state evidence
    state_evidence_ids = {e.id for e in evidence}
    for cited_id in selected_hypo.supporting_evidence_ids:
        assert cited_id in state_evidence_ids

    # Critic successfully approved the verified hypothesis
    critique = final_output["critique"]
    assert critique is not None
    assert critique.decision == "APPROVE"
    assert len(critique.critique_notes) > 20

    # Timeline captured transitions across stages
    timeline = final_output["timeline"]
    assert len(timeline) >= 5
    stages = [t.stage for t in timeline]
    assert "PLANNING" in stages
    assert "INVESTIGATING" in stages
    assert "ANALYZING" in stages
    assert "CRITIQUING" in stages
