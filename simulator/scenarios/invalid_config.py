"""Scenario 8: Invalid configuration causing auth failure."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class InvalidConfigScenario(BaseScenario):
    """Auth service configuration change updated JWT signing key in auth-service
    without updating public key validation in API gateway, breaking all authentication (401).
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="invalid_config",
            name="JWT Secret Mismatch Configuration Error",
            root_cause="Configuration update rotated JWT private key on auth-service without propagating matching public key to API Gateway.",
            affected_services=["auth-service", "api-gateway"],
            trigger_event="Configmap update on auth-service",
            recommended_remediation="rollback_deployment",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="log",
                    source="api-gateway",
                    key_pattern="InvalidSignatureError: Signature verification failed",
                    description="Token signature verification failure in gateway",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="api-gateway",
                    key_pattern="http_401_rate",
                    description="401 Unauthorized spike to 95%",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-INVALID-CONFIG-08",
            "title": "Global HTTP 401 Unauthorized Spike > 90%",
            "severity": "SEV1",
            "service": "api-gateway",
            "timestamp": now.isoformat(),
            "metric_name": "http_requests_401_ratio",
            "threshold_value": 0.05,
            "current_value": 0.94,
            "description": "API Gateway rejecting user requests with 401 Unauthorized",
        }

    def generate_logs(self, start_time: datetime, end_time: datetime) -> list[dict]:
        logs = []
        cur = start_time
        while cur <= end_time:
            if self.is_remediated:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "INFO",
                        "service": "api-gateway",
                        "message": "JWT token validated. Subject: user-9842",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "WARN",
                        "service": "api-gateway",
                        "message": "jwt.exceptions.InvalidSignatureError: Signature verification failed with key_id 'key-2026-v2'",
                    }
                )
            cur += timedelta(seconds=15)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"http_401_percent": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            data["http_401_percent"].append(
                {
                    "timestamp": ts,
                    "value": 0.1 if self.is_remediated else 94.2,
                }
            )
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if action_type in ["rollback_deployment", "modify_configuration"]:
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "JWT signing keys synchronized between auth-service and api-gateway"
        return False, f"Action {action_type} failed to synchronize JWT configuration"
