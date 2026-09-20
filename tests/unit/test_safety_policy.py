"""Unit tests for safety policy, blast radius calculation, and risk scoring."""


from simulator.services.topology import ServiceTopology
from src.domain.state import RemediationAction
from src.safety.policy import RiskPolicyEngine


def test_blast_radius_calculation():
    topology = ServiceTopology()
    policy = RiskPolicyEngine(topology=topology)

    # In topology: auth-service has api-gateway as dependent
    blast_radius = policy.calculate_blast_radius("auth-service")
    assert "auth-service" in blast_radius
    assert "api-gateway" in blast_radius


def test_destructive_payload_detection():
    policy = RiskPolicyEngine()

    assert policy.detect_destructive_payload({"command": "DROP TABLE users;"})
    assert policy.detect_destructive_payload({"script": "rm -rf /var/data"})
    assert policy.detect_destructive_payload({"query": "TRUNCATE transactions;"})
    assert not policy.detect_destructive_payload({"max_connections": 100})
    assert not policy.detect_destructive_payload({"target_version": "v2.4.0"})


def test_assess_action_risk_low_and_high():
    policy = RiskPolicyEngine()

    # Clear cache on notification-service has low risk
    low_action = RemediationAction(
        action_id="ACT-01",
        action_type="clear_cache",
        target_service="notification-service",
        parameters={"cache_type": "transient"},
        description="Clear transient notification cache",
        rationale="Flush backlog",
        rollback_plan="None",
    )
    assessed_low = policy.assess_action_risk(low_action)
    assert assessed_low.risk_tier in ["LOW", "MEDIUM"]
    assert assessed_low.idempotency_key != ""

    # Rollback deployment on payment-service has high risk
    high_action = RemediationAction(
        action_id="ACT-02",
        action_type="rollback_deployment",
        target_service="payment-service",
        parameters={"target_version": "v2.4.0"},
        description="Rollback payment-service",
        rationale="Revert defective commit",
        rollback_plan="Redeploy v2.4.1",
    )
    assessed_high = policy.assess_action_risk(high_action)
    assert assessed_high.risk_tier in ["HIGH", "CRITICAL"]
    assert assessed_high.requires_approval is True


def test_assess_action_risk_destructive_escalation():
    policy = RiskPolicyEngine()

    destructive_action = RemediationAction(
        action_id="ACT-03",
        action_type="run_query",
        target_service="payment-service",
        parameters={"query": "DROP TABLE accounts CASCADE;"},
        description="Dangerous maintenance",
        rationale="None",
        rollback_plan="None",
    )
    assessed = policy.assess_action_risk(destructive_action)
    assert assessed.risk_tier == "CRITICAL"
    assert assessed.risk_score == 1.0
    assert assessed.requires_approval is True


def test_authorize_approval_rbac():
    policy = RiskPolicyEngine()

    action_crit = RemediationAction(
        action_id="ACT-CRIT",
        action_type="run_query",
        target_service="payment-service",
        description="Critical DB change",
        rationale="Fix corruption",
        rollback_plan="Restore backup",
        risk_tier="CRITICAL",
    )

    action_high = RemediationAction(
        action_id="ACT-HIGH",
        action_type="rollback_deployment",
        target_service="payment-service",
        description="Rollback service",
        rationale="Fix bug",
        rollback_plan="Redeploy",
        risk_tier="HIGH",
    )

    # VIEWER cannot approve anything
    ok, msg = policy.authorize_approval(action_high, "VIEWER")
    assert not ok

    # OPERATOR cannot approve CRITICAL
    ok, msg = policy.authorize_approval(action_crit, "OPERATOR")
    assert not ok

    # ADMIN can approve CRITICAL
    ok, msg = policy.authorize_approval(action_crit, "ADMIN")
    assert ok

    # OPERATOR can approve HIGH
    ok, msg = policy.authorize_approval(action_high, "OPERATOR")
    assert ok
