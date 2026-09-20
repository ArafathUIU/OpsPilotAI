"""Scenario 5: CPU saturation."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class CPUSaturationScenario(BaseScenario):
    """Notification service template rendering contains an unoptimized regex
    that enters catastrophic polynomial backtracking, pegging all CPU cores at 100%.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="cpu_saturation",
            name="Catastrophic Backtracking CPU Saturation",
            root_cause="Notification service email template parser contains an unanchored regex pattern suffering from ReDoS, consuming 100% CPU on all worker threads.",
            affected_services=["notification-service"],
            trigger_event="Batch promotional email dispatch containing nested HTML formatting",
            recommended_remediation="restart_service",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="metric",
                    source="notification-service",
                    key_pattern="cpu_usage_percent",
                    description="CPU utilization pinned at 100%",
                ),
                ExpectedEvidence(
                    evidence_type="log",
                    source="notification-service",
                    key_pattern="ThreadBlockedWarning",
                    description="Thread watchdog reporting worker loop blocked",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-CPU-SAT-05",
            "title": "Notification Service CPU Utilization > 95%",
            "severity": "SEV1",
            "service": "notification-service",
            "timestamp": now.isoformat(),
            "metric_name": "process_cpu_seconds_total",
            "threshold_value": 0.80,
            "current_value": 0.99,
            "description": "Notification service worker process locked at 99.4% CPU",
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
                        "service": "notification-service",
                        "message": "Template rendered in 1.2ms. CPU load 12%",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "notification-service",
                        "message": "ThreadBlockedWarning: WorkerThread-4 unresponsive for 45000ms evaluating template regex parser",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"cpu_usage_percent": [], "dispatch_rate": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["cpu_usage_percent"].append({"timestamp": ts, "value": 14.0})
                data["dispatch_rate"].append({"timestamp": ts, "value": 450.0})
            else:
                data["cpu_usage_percent"].append({"timestamp": ts, "value": 99.8})
                data["dispatch_rate"].append({"timestamp": ts, "value": 2.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type == "restart_service"
            and parameters.get("target_service") == "notification-service"
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "notification-service restarted; CPU utilization dropped to 14%"
        return False, f"Action {action_type} failed to remediate CPU saturation"
