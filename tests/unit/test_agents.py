"""Unit tests for individual specialized agents."""

import pytest

from simulator.engine import default_simulator
from src.agents.code_analyst import CodeAnalystAgent
from src.agents.critic import CriticAgent
from src.agents.log_analyst import LogAnalystAgent
from src.agents.metrics_analyst import MetricsAnalystAgent
from src.agents.rca import RCAAgent
from src.agents.supervisor import SupervisorAgent
from src.domain.state import Evidence, Hypothesis, IncidentState, InvestigationTask
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter


@pytest.fixture(autouse=True)
def setup_scenario():
    default_simulator.load_scenario("redis_pool_exhaustion")


@pytest.mark.asyncio
async def test_supervisor_planning():
    router = ModelRouter([MockLLMProvider()])
    supervisor = SupervisorAgent(router=router)

    state = IncidentState(
        incident_id="inc-test-01",
        title="Payment latency increased to 2.8s",
        severity="SEV1",
        affected_services=["payment-service"],
    )

    plan = await supervisor.plan_investigation(state)
    assert plan.initial_severity == "SEV1"
    assert len(plan.tasks) >= 2
    task_types = [t.agent_type for t in plan.tasks]
    assert "log_analyst" in task_types
    assert "metrics_analyst" in task_types


@pytest.mark.asyncio
async def test_analyst_agents_produce_evidence():
    router = ModelRouter([MockLLMProvider()])
    log_agent = LogAnalystAgent(router=router)
    metrics_agent = MetricsAnalystAgent(router=router)
    code_agent = CodeAnalystAgent(router=router)

    task = InvestigationTask(
        task_id="t-1",
        agent_type="log_analyst",
        target_service="payment-service",
        query_intent="Find errors",
    )

    # Log Analyst
    log_out = await log_agent.investigate(task)
    assert len(log_out.evidence_items) > 0
    assert log_out.evidence_items[0].type == "log"

    # Metrics Analyst
    met_out = await metrics_agent.investigate(task)
    assert len(met_out.evidence_items) > 0
    assert met_out.evidence_items[0].type == "metric"

    # Code Analyst
    code_out = await code_agent.investigate(task)
    assert len(code_out.evidence_items) > 0
    assert code_out.evidence_items[0].type == "code"


@pytest.mark.asyncio
async def test_rca_and_critic_verification():
    router = ModelRouter([MockLLMProvider()])
    rca = RCAAgent(router=router)
    critic = CriticAgent(router=router)

    evidence_list = [
        Evidence(
            id="EV-LOG-REDIS-01",
            type="log",
            source="payment-service",
            observation="RedisTimeoutException: Connection pool exhausted",
            raw_reference="pool exhausted",
            relevance_score=0.95,
        ),
        Evidence(
            id="EV-MET-LATENCY-02",
            type="metric",
            source="payment-service",
            observation="P95 latency spiked to 2820ms",
            raw_reference="p95_latency=2.82s",
            relevance_score=0.92,
        ),
        Evidence(
            id="EV-CODE-DIFF-03",
            type="code",
            source="payment-service",
            observation="Commit reduced max_connections from 100 to 10",
            raw_reference="Commit c3a9f01b827e",
            relevance_score=0.98,
        ),
    ]

    rca_out = await rca.analyze("Payment P95 Latency Spike", evidence_list)
    assert len(rca_out.hypotheses) > 0
    hypo = rca_out.hypotheses[0]
    assert len(hypo.supporting_evidence_ids) > 0

    # Critic approves valid evidence
    critique = await critic.critique(hypo, evidence_list)
    assert critique.decision == "APPROVE"

    # Critic rejects when hypothesis cites nonexistent / hallucinated evidence IDs
    hallucinated_hypo = Hypothesis(
        id="HYP-FAKE",
        title="DDoS Attack",
        description="Botnet overwhelming gateway",
        confidence=0.99,
        supporting_evidence_ids=["EV-FAKE-ID-999"],  # Does not exist in evidence_list
        reasoning_summary="Unsupported guess",
    )
    fake_critique = await critic.critique(hallucinated_hypo, evidence_list)
    assert fake_critique.decision == "CHALLENGE"
    assert "hallucinated" in fake_critique.critique_notes.lower()
