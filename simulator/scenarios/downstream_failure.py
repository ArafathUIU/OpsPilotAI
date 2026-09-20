"""Scenario 6: Downstream service failure cascading upstream."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class DownstreamFailureScenario(BaseScenario):
    """Payment service crashes due to an unhandled exception, causing
    Order service checkouts to fail with HTTP 503 Bad Gateway.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="downstream_failure",
            name="Downstream Payment Service Outage",
            root_cause="Payment service crashed following a panic on null billing address, cascading HTTP 503 Bad Gateway failures into order-service checkout.",
            affected_services=["payment-service", "order-service"],
            trigger_event="Payment service process termination",
            recommended_remediation="restart_service",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="log",
                    source="order-service",
                    key_pattern="HTTPConnectionPool(host='payment-service', port=8083): Max retries exceeded",
                    description="Order service cannot reach payment service",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="order-service",
                    key_pattern="http_503_count",
                    description="Cascading 503 errors at order service",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-DOWNSTREAM-FAIL-06",
            "title": "Order Service HTTP 503 Error Rate > 20%",
            "severity": "SEV1",
            "service": "order-service",
            "timestamp": now.isoformat(),
            "metric_name": "http_requests_503_total",
            "threshold_value": 0.05,
            "current_value": 0.28,
            "description": "Order service failing to complete checkouts due to downstream payment failure",
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
                        "service": "order-service",
                        "message": "Payment token validated successfully from payment-service",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "order-service",
                        "message": "urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='payment-service', port=8083): Max retries exceeded with url: /api/v1/charge (Caused by NewConnectionError('<payment-service:8083>: Connection refused'))",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"order_http_503_rate": [], "payment_availability": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["order_http_503_rate"].append({"timestamp": ts, "value": 0.0})
                data["payment_availability"].append({"timestamp": ts, "value": 1.0})
            else:
                data["order_http_503_rate"].append({"timestamp": ts, "value": 28.5})
                data["payment_availability"].append({"timestamp": ts, "value": 0.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type == "restart_service"
            and parameters.get("target_service") == "payment-service"
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "payment-service restarted; downstream connectivity restored"
        return False, f"Action {action_type} failed to restore payment-service"
