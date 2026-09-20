"""Unit tests validating API request and response schemas."""

import pytest
from pydantic import ValidationError

from apps.api.schemas.approval import ApprovalDecisionRequest
from apps.api.schemas.incident import IncidentCreateRequest
from apps.api.schemas.webhook import AlertWebhookPayload


def test_alert_webhook_payload_valid():
    payload = AlertWebhookPayload(
        source="prometheus",
        status="firing",
        alert_name="HighHttp5xxRate",
        service="payment-service",
        severity="SEV1",
        summary="HTTP 500 error rate exceeded 5%",
        description="Payment authorization failures spike on /api/v1/pay",
    )
    assert payload.alert_name == "HighHttp5xxRate"
    assert payload.service == "payment-service"
    assert payload.severity == "SEV1"
    assert payload.status == "firing"


def test_alert_webhook_payload_invalid_severity():
    with pytest.raises(ValidationError):
        AlertWebhookPayload(
            alert_name="TestAlert",
            service="auth-service",
            severity="SEV99",  # Invalid
            summary="Invalid severity test",
        )


def test_approval_decision_request_valid():
    req = ApprovalDecisionRequest(
        decision="APPROVED",
        approver_id="sre-lead@company.com",
        approver_role="OPERATOR",
        reason="Rollback verified safe against blast radius",
    )
    assert req.decision == "APPROVED"
    assert req.approver_role == "OPERATOR"


def test_approval_decision_request_modified():
    req = ApprovalDecisionRequest(
        decision="MODIFIED",
        approver_id="admin@company.com",
        approver_role="ADMIN",
        reason="Scaled to 5 replicas instead of 3",
        modified_parameters={"replicas": 5},
    )
    assert req.decision == "MODIFIED"
    assert req.modified_parameters == {"replicas": 5}


def test_incident_create_request_defaults():
    req = IncidentCreateRequest(
        title="High Latency on Order Service",
        severity="SEV2",
        affected_services=["order-service"],
    )
    assert req.auto_remediate is False
    assert req.symptoms == ""
