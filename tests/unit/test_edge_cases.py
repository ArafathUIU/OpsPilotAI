"""Comprehensive test suite covering critical edge cases across the platform."""

import asyncio
import json

import pytest

from apps.api.schemas.approval import ApprovalDecisionRequest
from apps.api.services.event_stream import EventBroker
from apps.api.services.incident_service import IncidentService
from src.domain.state import (
    Hypothesis,
    IncidentState,
    RemediationAction,
    RemediationPlan,
)
from src.memory.episodic import EpisodicMemoryManager
from src.reporting.postmortem import PostmortemGenerator
from src.safety.policy import RiskPolicyEngine


@pytest.mark.asyncio
async def test_sse_heartbeat_on_idle_stream():
    broker = EventBroker()
    incident_id = "inc-edge-heartbeat"

    # Set very fast heartbeat interval (0.05s) to trigger keepalive ping
    stream = broker.subscribe(incident_id, heartbeat_interval=0.05)

    # First event should be a heartbeat ping since no messages were published
    event = await asyncio.wait_for(anext(stream), timeout=0.5)
    assert event["event"] == "ping"
    data = json.loads(event["data"])
    assert "timestamp" in data


def test_double_approval_rejection():
    service = IncidentService()
    inc = service.create_incident(
        title="Double Approval Test",
        severity="SEV1",
        affected_services=["payment-service"],
    )

    state = service._incidents[inc.id]
    state.remediation_plan = RemediationPlan(
        incident_id=inc.id,
        hypothesis_id="HYP-01",
        actions=[
            RemediationAction(
                action_id="ACT-01",
                action_type="rollback_deployment",
                target_service="payment-service",
                description="Rollback",
                rationale="Fix pool",
                rollback_plan="None",
                risk_tier="HIGH",
                requires_approval=True,
            )
        ],
        summary="Rollback",
    )

    appr_req = ApprovalDecisionRequest(
        decision="APPROVED",
        approver_id="lead-sre@company.com",
        approver_role="OPERATOR",
        reason="Looks safe",
    )

    # First approval succeeds
    res1 = service.submit_approval(inc.id, "appr-ACT-01", appr_req)
    assert res1.status == "APPROVED"

    # Second approval attempt triggers error
    with pytest.raises(ValueError, match="was already APPROVED"):
        service.submit_approval(inc.id, "appr-ACT-01", appr_req)


def test_incident_list_filtering_and_pagination():
    service = IncidentService()
    # Create distinct incidents
    service.create_incident("Order Service Outage", "SEV1", ["order-service"])
    service.create_incident("Payment Timeout", "SEV2", ["payment-service"])
    service.create_incident("Auth Slowdown", "SEV3", ["auth-service"])

    # Filter by severity
    sev1_list = service.list_incidents(severity="SEV1")
    assert all(i.severity == "SEV1" for i in sev1_list)

    # Filter by service
    payment_list = service.list_incidents(service="payment-service")
    assert all("payment-service" in payment_list[0].affected_services for _ in payment_list)

    # Pagination limit
    paged = service.list_incidents(limit=2, offset=0)
    assert len(paged) <= 2


def test_preliminary_postmortem_for_in_progress_incident():
    generator = PostmortemGenerator()
    state = IncidentState(
        incident_id="inc-in-progress",
        title="Active Incident Investigation",
        severity="SEV1",
        affected_services=["payment-service"],
        current_stage="INVESTIGATING",
        selected_hypothesis=Hypothesis(
            id="HYP-01",
            title="Suspected Redis Pool Starvation",
            description="Initial signs point to connection timeouts.",
            confidence=0.6,
            supporting_evidence_ids=["EV-01"],
            reasoning_summary="Partial logs analyzed.",
        ),
    )

    report = generator.generate_report(state)
    assert report.status == "INVESTIGATING"
    assert report.resolved_at is None
    assert report.mttr_seconds == 0
    assert "currently in progress" in report.executive_summary.lower()


def test_destructive_payload_obfuscation_and_whitespace():
    policy = RiskPolicyEngine()

    # Whitespace with newline
    assert policy.detect_destructive_payload({"query": "DROP\nTABLE users;"})
    # Obfuscated tabs
    assert policy.detect_destructive_payload({"query": "TRUNCATE\t\tTABLE orders;"})
    # Destructive alter table
    assert policy.detect_destructive_payload({"cmd": "ALTER TABLE payments DROP COLUMN card_num"})
    # Normal queries
    assert not policy.detect_destructive_payload({"query": "SELECT * FROM users WHERE active = true"})


@pytest.mark.asyncio
async def test_empty_or_whitespace_memory_search():
    manager = EpisodicMemoryManager()

    assert await manager.search_similar_incidents("") == []
    assert await manager.search_similar_incidents("   \t\n  ") == []


def test_blast_radius_for_unknown_service():
    policy = RiskPolicyEngine()
    # Unregistered third party service
    radius = policy.calculate_blast_radius("third-party-stripe-gateway")
    assert radius == ["third-party-stripe-gateway"]
