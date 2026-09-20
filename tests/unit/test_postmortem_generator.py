"""Unit tests for PostmortemGenerator and episodic memory auto-indexing."""

import pytest

from src.domain.state import (
    Hypothesis,
    IncidentState,
    RemediationAction,
    RemediationPlan,
)
from src.memory.episodic import EpisodicMemoryManager
from src.memory.vector_store import InMemoryVectorStore
from src.reporting.postmortem import PostmortemGenerator


@pytest.mark.asyncio
async def test_postmortem_report_generation():
    state = IncidentState(
        incident_id="inc-test-pm-01",
        title="Redis Connection Exhaustion on Payment Service",
        severity="SEV1",
        affected_services=["payment-service"],
        current_stage="RESOLVED",
        selected_hypothesis=Hypothesis(
            id="HYP-01",
            title="Redis Connection Pool Starvation",
            description="Max connections capped at 10 caused worker timeouts.",
            confidence=0.95,
            supporting_evidence_ids=["EV-LOG-01", "EV-MET-02"],
            reasoning_summary="Commit diff decreased pool limit.",
        ),
        remediation_plan=RemediationPlan(
            incident_id="inc-test-pm-01",
            hypothesis_id="HYP-01",
            actions=[
                RemediationAction(
                    action_id="ACT-01",
                    action_type="rollback_deployment",
                    target_service="payment-service",
                    description="Rollback to v2.4.0",
                    rationale="Restores pool",
                    rollback_plan="None",
                )
            ],
            summary="Deployment rollback executed",
            prevention_recommendations=["Add pre-commit schema linting"],
        ),
    )

    vector_store = InMemoryVectorStore()
    memory_manager = EpisodicMemoryManager(vector_store=vector_store)
    generator = PostmortemGenerator(memory_manager=memory_manager)

    report = generator.generate_report(state)
    assert report.incident_id == "inc-test-pm-01"
    assert report.severity == "SEV1"
    assert "Redis Connection Pool Starvation" in report.root_cause_analysis
    assert "EV-LOG-01" in report.supporting_evidence_ids
    assert len(report.five_whys) == 5
    assert "# Incident Postmortem:" in report.full_markdown

    # Auto-index into episodic memory
    await generator.auto_index_to_memory(report)
    assert len(vector_store.documents) == 1
    assert vector_store.documents[0].id == "PM-inc-test-pm-01"
