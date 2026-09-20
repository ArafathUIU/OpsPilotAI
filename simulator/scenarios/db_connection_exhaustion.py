"""Scenario 2: Database connection exhaustion."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class DBConnectionExhaustionScenario(BaseScenario):
    """Order service leaky transaction blocks fail to close DB sessions,
    exhausting PostgreSQL max_connections (100/100).
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="db_connection_exhaustion",
            name="Database Connection Pool Exhaustion",
            root_cause=(
                "Order service connection leak in checkout handler fails to release SQLAlchemy "
                "sessions upon unhandled checkout validation exceptions, saturating PostgreSQL max_connections."
            ),
            affected_services=["order-service"],
            trigger_event="Order-service checkout bug leading to unclosed session handles",
            recommended_remediation="restart_service",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="log",
                    source="order-service",
                    key_pattern="FATAL: remaining connection slots are reserved",
                    description="PostgreSQL error refusing client connections",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="order-service",
                    key_pattern="db_active_connections",
                    description="PostgreSQL active connections plateau at 100",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-DB-CONN-02",
            "title": "Order Service Database Connection Saturation",
            "severity": "SEV1",
            "service": "order-service",
            "timestamp": now.isoformat(),
            "metric_name": "postgres_active_connections",
            "threshold_value": 85.0,
            "current_value": 100.0,
            "description": "PostgreSQL database connections reached 100% capacity",
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
                        "trace_id": f"tr-ord-{int(cur.timestamp())}",
                        "message": "Order placed successfully. DB session closed.",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "order-service",
                        "trace_id": f"tr-ord-{int(cur.timestamp())}",
                        "message": "asyncpg.exceptions.TooManyConnectionsError: FATAL: remaining connection slots are reserved for non-replication superuser connections",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"db_active_connections": [], "http_500_rate": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["db_active_connections"].append({"timestamp": ts, "value": 24.0})
                data["http_500_rate"].append({"timestamp": ts, "value": 0.0})
            else:
                data["db_active_connections"].append({"timestamp": ts, "value": 100.0})
                data["http_500_rate"].append({"timestamp": ts, "value": 35.2})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if action_type == "restart_service" and parameters.get("target_service") == "order-service":
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "order-service successfully restarted; leaked connection pool purged"
        return False, f"Action {action_type} did not resolve database connection leak"
