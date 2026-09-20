"""Scenario 9: Upstream API Timeout."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class APITimeoutScenario(BaseScenario):
    """External payment processor (e.g. Stripe/Adyen sandbox) experiencing
    latency degradation, causing payment-service outbound HTTP client timeouts (504).
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="api_timeout",
            name="External Payment Provider Timeout",
            root_cause="Third-party payment processor API degraded, exceeding payment-service 5000ms HTTP timeout threshold on card charge requests.",
            affected_services=["payment-service"],
            trigger_event="Upstream provider latency incident",
            recommended_remediation="modify_configuration",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="log",
                    source="payment-service",
                    key_pattern="httpx.ReadTimeout: The read operation timed out after 5.0 seconds",
                    description="Outbound HTTP timeout log",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="payment-service",
                    key_pattern="outbound_timeout_rate",
                    description="Outbound timeout rate spike to 40%",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-API-TIMEOUT-09",
            "title": "Payment Service Outbound API Timeout Spike > 30%",
            "severity": "SEV2",
            "service": "payment-service",
            "timestamp": now.isoformat(),
            "metric_name": "http_client_timeout_ratio",
            "threshold_value": 0.05,
            "current_value": 0.38,
            "description": "Outbound HTTP requests to payment provider timing out",
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
                        "service": "payment-service",
                        "message": "Payment processed through fallback secondary provider in 180ms",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "payment-service",
                        "message": "httpx.ReadTimeout: The read operation timed out after 5.0 seconds while calling https://api.processor.internal/v1/charges",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"timeout_rate": [], "provider_p95_latency": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["timeout_rate"].append({"timestamp": ts, "value": 0.01})
                data["provider_p95_latency"].append({"timestamp": ts, "value": 180.0})
            else:
                data["timeout_rate"].append({"timestamp": ts, "value": 38.0})
                data["provider_p95_latency"].append({"timestamp": ts, "value": 5200.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if action_type == "modify_configuration" and parameters.get("provider_failover"):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "payment-service routed traffic to secondary backup payment provider"
        return False, f"Action {action_type} failed to switch payment provider route"
