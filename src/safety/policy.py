"""Deterministic risk assessment, blast radius estimation, and safety policy engine."""

import hashlib
import json
import re
from typing import Any

from simulator.services.topology import ServiceTopology
from src.core.config import get_settings
from src.domain.state import ActionType, RemediationAction, RiskTier
from src.observability.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

DESTRUCTIVE_PATTERNS = re.compile(
    r"(?i)\b(drop\s+(?:table|database|schema|view|index)|truncate(?:\s+table)?|delete\s+from|rm\s+-(?:r|f|rf|fr)\b|format\s+[a-z]:|flushall|flushdb|alter\s+table\s+\S+\s+drop)\b"
)

BASE_ACTION_RISK: dict[ActionType, float] = {
    "clear_cache": 0.20,
    "scale_replicas": 0.30,
    "modify_configuration": 0.45,
    "restart_service": 0.65,
    "rollback_deployment": 0.70,
    "run_query": 0.85,
}


class RiskPolicyEngine:
    """Evaluates blast radius, calculates risk scores, and enforces governance policies."""

    def __init__(self, topology: ServiceTopology | None = None) -> None:
        self.topology = topology or ServiceTopology()

    def calculate_blast_radius(self, target_service: str) -> list[str]:
        """Identifies all upstream and downstream services affected if target service degrades."""
        dependents = self.topology.get_upstream_dependents(target_service)
        dependencies = self.topology.get_downstream_dependencies(target_service)
        combined = list(dict.fromkeys([target_service, *dependents, *dependencies]))
        return combined

    def detect_destructive_payload(self, parameters: dict[str, Any]) -> bool:
        """Scans parameters for catastrophic or destructive commands."""
        def _extract_strings(val: Any) -> list[str]:
            strings: list[str] = []
            if isinstance(val, str):
                strings.append(val)
            elif isinstance(val, dict):
                for k, v in val.items():
                    strings.append(str(k))
                    strings.extend(_extract_strings(v))
            elif isinstance(val, (list, tuple, set)):
                for item in val:
                    strings.extend(_extract_strings(item))
            return strings

        for s in _extract_strings(parameters):
            if DESTRUCTIVE_PATTERNS.search(s):
                return True

        raw_dump = json.dumps(parameters)
        return bool(DESTRUCTIVE_PATTERNS.search(raw_dump))

    def generate_idempotency_key(
        self,
        incident_id: str,
        action_type: str,
        target_service: str,
        parameters: dict[str, Any],
    ) -> str:
        """Generates a reproducible SHA256 idempotency key to prevent double execution."""
        serialized_params = json.dumps(parameters, sort_keys=True)
        raw_key = f"{incident_id}:{action_type}:{target_service}:{serialized_params}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:32]

    def assess_action_risk(
        self,
        action: RemediationAction,
        incident_id: str = "inc-default",
    ) -> RemediationAction:
        """Computes empirical risk score, tier, blast radius, and approval requirement."""
        base_risk = BASE_ACTION_RISK.get(action.action_type, 0.50)

        # 1. Check for dangerous destructive commands
        is_destructive = self.detect_destructive_payload(action.parameters)
        if is_destructive:
            base_risk = 1.0

        # 2. Factor in blast radius (downstream dependent services)
        blast_radius = self.calculate_blast_radius(action.target_service)
        blast_penalty = min(0.20, len(blast_radius) * 0.05)
        total_score = min(1.0, base_risk + blast_penalty)

        # 3. Categorize into risk tier
        risk_tier: RiskTier
        if total_score < 0.35:
            risk_tier = "LOW"
        elif total_score < 0.60:
            risk_tier = "MEDIUM"
        elif total_score < 0.85:
            risk_tier = "HIGH"
        else:
            risk_tier = "CRITICAL"

        # 4. Enforce approval gating policy
        # Only LOW risk actions can be auto-approved, and only if explicit config flag is enabled
        auto_remediate_enabled = getattr(settings, "auto_remediate_low_risk", False)
        requires_approval = True
        if risk_tier == "LOW" and auto_remediate_enabled and not is_destructive:
            requires_approval = False

        idempotency_key = self.generate_idempotency_key(
            incident_id=incident_id,
            action_type=action.action_type,
            target_service=action.target_service,
            parameters=action.parameters,
        )

        return action.model_copy(
            update={
                "risk_score": round(total_score, 3),
                "risk_tier": risk_tier,
                "requires_approval": requires_approval,
                "idempotency_key": idempotency_key,
            }
        )

    def authorize_approval(self, action: RemediationAction, approver_role: str) -> tuple[bool, str]:
        """Validates whether the approving identity possesses sufficient RBAC privileges."""
        role = approver_role.upper()
        if role not in ["VIEWER", "OPERATOR", "ADMIN"]:
            return False, f"Unknown approver role '{approver_role}'"

        if role == "VIEWER":
            return False, "VIEWER role has read-only access and cannot approve remediation actions"

        if action.risk_tier == "CRITICAL" and role != "ADMIN":
            return False, "CRITICAL risk remediation actions strictly require ADMIN role approval"

        if action.risk_tier == "HIGH" and role not in ["ADMIN", "OPERATOR"]:
            return False, "HIGH risk remediation actions require at least OPERATOR role approval"

        return True, "Authorized"
