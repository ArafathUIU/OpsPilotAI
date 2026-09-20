"""Integration tests for FastAPI REST endpoints and incident lifecycle management."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.incident_service import default_incident_service
from src.domain.state import (
    Hypothesis,
    RemediationAction,
    RemediationPlan,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_webhook_alert_ingestion(client):
    payload = {
        "source": "prometheus",
        "status": "firing",
        "alert_name": "HighLatencyBreach",
        "service": "payment-service",
        "severity": "SEV1",
        "summary": "P95 latency breached 2500ms SLO threshold",
        "description": "Connection pool acquisition timed out",
    }
    response = client.post("/api/v1/webhooks/alerts", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ingested"
    assert "incident_id" in data
    assert data["incident_id"].startswith("inc-")


def test_webhook_alert_resolved_ignored(client):
    payload = {
        "source": "prometheus",
        "status": "resolved",
        "alert_name": "HighLatencyBreach",
        "service": "payment-service",
        "severity": "SEV1",
        "summary": "Alert resolved",
    }
    response = client.post("/api/v1/webhooks/alerts", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ignored"


def test_manual_incident_creation_and_listing(client):
    payload = {
        "title": "Manual Test Incident: DB Pool Exhaustion",
        "severity": "SEV2",
        "affected_services": ["order-service"],
        "symptoms": "Database queries taking > 5 seconds",
        "auto_remediate": False,
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    inc_id = created["id"]
    assert created["title"] == payload["title"]

    # Test listing
    list_res = client.get("/api/v1/incidents")
    assert list_res.status_code == 200
    incidents = list_res.json()
    assert any(i["id"] == inc_id for i in incidents)

    # Test get detail
    detail_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == inc_id


def test_incident_evidence_hypotheses_and_timeline(client):
    payload = {
        "title": "Inspection Test Incident",
        "severity": "SEV3",
        "affected_services": ["auth-service"],
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    inc_id = create_res.json()["id"]

    # Evidence query
    ev_res = client.get(f"/api/v1/incidents/{inc_id}/evidence")
    assert ev_res.status_code == 200
    assert isinstance(ev_res.json(), list)

    # Hypotheses query
    hyp_res = client.get(f"/api/v1/incidents/{inc_id}/hypotheses")
    assert hyp_res.status_code == 200
    assert isinstance(hyp_res.json(), list)

    # Timeline query
    tl_res = client.get(f"/api/v1/incidents/{inc_id}/timeline")
    assert tl_res.status_code == 200
    timeline = tl_res.json()
    assert len(timeline) >= 1
    assert timeline[0]["stage"] == "CREATED"


def test_human_approval_workflow(client):
    # Create incident and artificially populate a remediation plan awaiting approval
    payload = {
        "title": "Approval Gating Test",
        "severity": "SEV1",
        "affected_services": ["payment-service"],
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    inc_id = create_res.json()["id"]

    state = default_incident_service._incidents[inc_id]
    state.remediation_plan = RemediationPlan(
        incident_id=inc_id,
        hypothesis_id="HYP-01",
        actions=[
            RemediationAction(
                action_id="ACT-RB-01",
                action_type="rollback_deployment",
                target_service="payment-service",
                description="Rollback payment-service",
                rationale="Fix pool starvation",
                rollback_plan="Redeploy v2.4.1",
                risk_tier="HIGH",
                requires_approval=True,
            )
        ],
        summary="Rollback required",
    )

    # 1. Fetch pending approvals
    appr_list_res = client.get(f"/api/v1/incidents/{inc_id}/approvals")
    assert appr_list_res.status_code == 200
    approvals = appr_list_res.json()
    assert len(approvals) == 1
    appr_id = approvals[0]["id"]
    assert approvals[0]["status"] == "PENDING"

    # 2. Unauthorized role (VIEWER) attempt fails
    viewer_decision = {
        "decision": "APPROVED",
        "approver_id": "junior@company.com",
        "approver_role": "VIEWER",
        "reason": "Looks good",
    }
    deny_res = client.post(f"/api/v1/incidents/{inc_id}/approvals/{appr_id}", json=viewer_decision)
    assert deny_res.status_code == 403

    # 3. Authorized role (OPERATOR) approves
    operator_decision = {
        "decision": "APPROVED",
        "approver_id": "senior-sre@company.com",
        "approver_role": "OPERATOR",
        "reason": "Verified rollback version v2.4.0 is stable",
    }
    approve_res = client.post(f"/api/v1/incidents/{inc_id}/approvals/{appr_id}", json=operator_decision)
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "APPROVED"
    assert approved_data["approver_id"] == "senior-sre@company.com"


def test_postmortem_report_endpoints(client):
    payload = {
        "title": "Postmortem Endpoint Test",
        "severity": "SEV1",
        "affected_services": ["payment-service"],
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    inc_id = create_res.json()["id"]

    state = default_incident_service._incidents[inc_id]
    state.selected_hypothesis = Hypothesis(
        id="HYP-01",
        title="Redis Exhaustion",
        description="Pool cap at 10",
        confidence=0.94,
        supporting_evidence_ids=["EV-01"],
        reasoning_summary="Commit diff",
    )

    # GET report
    report_res = client.get(f"/api/v1/incidents/{inc_id}/report")
    assert report_res.status_code == 200
    data = report_res.json()
    assert data["incident_id"] == inc_id
    assert "Redis Exhaustion" in data["root_cause_analysis"]
    assert len(data["five_whys"]) == 5

    # POST report (generate and save)
    publish_res = client.post(f"/api/v1/incidents/{inc_id}/report")
    assert publish_res.status_code == 200
    assert "# Incident Postmortem:" in publish_res.json()["full_markdown"]
