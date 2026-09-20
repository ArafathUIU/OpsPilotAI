"""Scenario 3: Slow database query without index."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class SlowQueryScenario(BaseScenario):
    """Order search endpoint triggers full table scans on millions of rows
    due to a missing database index on `customer_uuid`.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="slow_query",
            name="Unindexed Database Sequential Scan",
            root_cause=(
                "Missing index on orders(customer_uuid) causing full sequential table scan on 2.5M rows, "
                "spiking DB CPU to 99% and order-service query latency to 12 seconds."
            ),
            affected_services=["order-service"],
            trigger_event="Batch customer history query volume spike",
            recommended_remediation="modify_configuration",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="log",
                    source="order-service",
                    key_pattern="duration: 12140.231 ms  statement: SELECT * FROM orders WHERE customer_uuid",
                    description="Slow query log entry showing 12s sequential scan",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="order-service",
                    key_pattern="database_query_duration_p95",
                    description="Query latency degradation to >10 seconds",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-SLOW-QUERY-03",
            "title": "Order Service Database Query P95 Latency > 10s",
            "severity": "SEV2",
            "service": "order-service",
            "timestamp": now.isoformat(),
            "metric_name": "db_query_duration_seconds",
            "threshold_value": 2.0,
            "current_value": 12.14,
            "description": "Database query duration exceeded 2s threshold",
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
                        "message": "Query executed using index idx_orders_customer_uuid in 4ms",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "WARN",
                        "service": "order-service",
                        "message": (
                            "PostgreSQL Slow Query: duration: 12140.231 ms statement: "
                            "SELECT * FROM orders WHERE customer_uuid = '9f8e7d6c-1122-3344-5566-778899aabbcc' "
                            "[Seq Scan on orders]"
                        ),
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"db_query_p95_ms": [], "db_cpu_percent": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["db_query_p95_ms"].append({"timestamp": ts, "value": 15.0})
                data["db_cpu_percent"].append({"timestamp": ts, "value": 22.0})
            else:
                data["db_query_p95_ms"].append({"timestamp": ts, "value": 12140.0})
                data["db_cpu_percent"].append({"timestamp": ts, "value": 98.4})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type == "modify_configuration"
            and "index" in parameters.get("action", "").lower()
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return (
                True,
                "Index idx_orders_customer_uuid created successfully; query planner normalized",
            )
        return False, f"Action {action_type} did not resolve slow query"
