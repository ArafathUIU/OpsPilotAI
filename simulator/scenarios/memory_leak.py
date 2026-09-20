"""Scenario 4: Memory leak in auth-service."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class MemoryLeakScenario(BaseScenario):
    """Auth service token cache does not evict expired sessions,
    growing memory consumption monotonically until container limit (95%).
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="memory_leak",
            name="Session Cache Memory Leak",
            root_cause="Auth service in-memory session cache missing TTL eviction, causing monotonic RAM leak towards OOM limit.",
            affected_services=["auth-service"],
            trigger_event="High traffic login campaign accumulating unevicted session dictionaries",
            recommended_remediation="restart_service",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="metric",
                    source="auth-service",
                    key_pattern="memory_usage_percent",
                    description="Memory consumption ramping monotonically to 94%",
                ),
                ExpectedEvidence(
                    evidence_type="log",
                    source="auth-service",
                    key_pattern="OutOfMemoryWarning",
                    description="GC warning regarding heap memory pressure",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-MEM-LEAK-04",
            "title": "Auth Service Memory Usage > 90%",
            "severity": "SEV1",
            "service": "auth-service",
            "timestamp": now.isoformat(),
            "metric_name": "container_memory_usage_bytes",
            "threshold_value": 0.90,
            "current_value": 0.94,
            "description": "Auth service memory limit breach approaching OOMKilled",
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
                        "service": "auth-service",
                        "message": "Heap memory stable at 240MB / 2048MB",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "WARN",
                        "service": "auth-service",
                        "message": "OutOfMemoryWarning: Heap memory pressure high (1920MB / 2048MB, 93.75%). GC pause 480ms",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"memory_usage_percent": [], "gc_pause_ms": []}
        cur = start_time
        val = 70.0
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["memory_usage_percent"].append({"timestamp": ts, "value": 25.0})
                data["gc_pause_ms"].append({"timestamp": ts, "value": 5.0})
            else:
                val = min(94.5, val + 2.0)
                data["memory_usage_percent"].append({"timestamp": ts, "value": val})
                data["gc_pause_ms"].append({"timestamp": ts, "value": 480.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if action_type == "restart_service" and parameters.get("target_service") == "auth-service":
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "auth-service restarted successfully; resident heap cleared to 25%"
        return False, f"Action {action_type} failed to remediate memory leak"
