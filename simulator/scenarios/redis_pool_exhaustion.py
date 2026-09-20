"""Scenario 1: Redis connection pool exhaustion."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class RedisPoolExhaustionScenario(BaseScenario):
    """Payment service deployment v2.4.1 reduced max_connections from 100 to 10.
    Under moderate load, thread pools starve waiting for free Redis connections,
    causing P95 latency to skyrocket from 280ms to 2.8s and RedisTimeoutExceptions.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="redis_pool_exhaustion",
            name="Redis Connection Pool Exhaustion",
            root_cause=(
                "Payment service v2.4.1 deployment accidentally reduced Redis connection pool size "
                "from 100 to 10 in configuration, causing thread pool starvation and timeout errors."
            ),
            affected_services=["payment-service", "api-gateway"],
            trigger_event="Deployment of payment-service:v2.4.1 5 minutes prior to alert",
            recommended_remediation="rollback_deployment",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="metric",
                    source="payment-service",
                    key_pattern="active_connections",
                    description="Redis connection pool active connections saturated at 10/10",
                ),
                ExpectedEvidence(
                    evidence_type="log",
                    source="payment-service",
                    key_pattern="RedisTimeoutException",
                    description="High frequency of RedisTimeoutException: pool exhausted",
                ),
                ExpectedEvidence(
                    evidence_type="code",
                    source="payment-service",
                    key_pattern="max_connections",
                    description="Commit diff showing max_connections reduced from 100 to 10",
                ),
                ExpectedEvidence(
                    evidence_type="metric",
                    source="payment-service",
                    key_pattern="p95_latency",
                    description="P95 latency spike from 280ms to 2800ms",
                ),
            ],
            forbidden_claims=[
                "Network partition between AWS and Redis cluster",
                "Redis server out of memory (OOM)",
                "DDoS attack on payment-service",
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-REDIS-POOL-01",
            "title": "Payment API P95 latency increased from 280ms to 2.8s",
            "severity": "SEV1",
            "service": "payment-service",
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "metric_name": "http_request_duration_p95_seconds",
            "threshold_value": 0.5,
            "current_value": 2.82,
            "description": "Payment Service P95 latency breached critical threshold (2.82s > 0.50s)",
        }

    def generate_logs(self, start_time: datetime, end_time: datetime) -> list[dict]:
        logs = []
        cur = start_time
        while cur <= end_time:
            # Baseline logs
            if self.is_remediated:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "INFO",
                        "service": "payment-service",
                        "trace_id": f"tr-{int(cur.timestamp())}-01",
                        "message": "Payment token authorization completed in 32ms",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "payment-service",
                        "trace_id": f"tr-{int(cur.timestamp())}-88",
                        "message": (
                            "RedisTimeoutException: Connection pool exhausted [active=10, max=10, "
                            "wait_queue=48]. Failed to acquire Redis connection after 2000ms"
                        ),
                        "exception_class": "redis.exceptions.ConnectionError",
                    }
                )
                logs.append(
                    {
                        "timestamp": (cur + timedelta(seconds=2)).isoformat(),
                        "level": "WARN",
                        "service": "api-gateway",
                        "trace_id": f"tr-{int(cur.timestamp())}-88",
                        "message": "Upstream /api/v1/payments call took 2840ms, approaching gateway timeout",
                    }
                )
            cur += timedelta(seconds=15)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {
            "p95_latency_ms": [],
            "error_rate_percent": [],
            "redis_active_connections": [],
            "redis_pool_wait_queue": [],
        }
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["p95_latency_ms"].append({"timestamp": ts, "value": 265.0})
                data["error_rate_percent"].append({"timestamp": ts, "value": 0.05})
                data["redis_active_connections"].append({"timestamp": ts, "value": 22.0})
                data["redis_pool_wait_queue"].append({"timestamp": ts, "value": 0.0})
            else:
                data["p95_latency_ms"].append({"timestamp": ts, "value": 2820.0})
                data["error_rate_percent"].append({"timestamp": ts, "value": 14.8})
                data["redis_active_connections"].append({"timestamp": ts, "value": 10.0})
                data["redis_pool_wait_queue"].append({"timestamp": ts, "value": 52.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "commit_sha": "c3a9f01b827e",
                "service": "payment-service",
                "author": "dev-engineer@company.internal",
                "message": "perf: optimize redis client parameters and connection limits",
                "timestamp": (now - timedelta(minutes=15)).isoformat(),
                "changed_files": ["config/redis.yaml", "src/client.py"],
                "diff": (
                    "--- a/config/redis.yaml\n"
                    "+++ b/config/redis.yaml\n"
                    "@@ -8,3 +8,3 @@\n"
                    "   host: redis-cluster.internal\n"
                    "   port: 6379\n"
                    "-  max_connections: 100\n"
                    "+  max_connections: 10\n"
                ),
            },
            {
                "commit_sha": "a17c8e4209bb",
                "service": "payment-service",
                "author": "lead@company.internal",
                "message": "feat: add stripe webhook verification signature",
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "changed_files": ["src/webhook.py"],
                "diff": "--- a/src/webhook.py\n+++ b/src/webhook.py\n@@ -1,1 +1,2 @@\n",
            },
        ]

    def get_deployments(self) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "deployment_id": "dep-payment-994",
                "service": "payment-service",
                "version": "v2.4.1",
                "previous_version": "v2.4.0",
                "timestamp": (now - timedelta(minutes=12)).isoformat(),
                "deployed_by": "ci-cd-pipeline@gitlab",
                "status": "SUCCESS",
                "commit_sha": "c3a9f01b827e",
                "config_changes": {"max_connections": 10},
            }
        ]

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type == "rollback_deployment"
            and parameters.get("target_service") == "payment-service"
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "payment-service successfully rolled back from v2.4.1 to v2.4.0"
        elif action_type == "modify_configuration" and parameters.get("max_connections", 0) >= 50:
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "payment-service redis max_connections scaled back to 100"
        elif (
            action_type == "restart_service"
            and parameters.get("target_service") == "payment-service"
        ):
            # Temporary reboot without config fix does not permanently solve pool limit
            return True, "payment-service restarted, but configuration max_connections=10 remains"
        return False, f"Remediation action {action_type} failed or target service invalid"
