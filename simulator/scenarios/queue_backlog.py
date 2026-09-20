"""Scenario 10: Asynchronous message queue backlog."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class QueueBacklogScenario(BaseScenario):
    """Notification service consumer workers crash due to unhandled message schema,
    causing message queue backlog to surge past 150,000 unconsumed messages.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="queue_backlog",
            name="Message Queue Consumer Stoppage Backlog",
            root_cause="Notification consumer pod workers crashed on malformed event payload, leaving queue unconsumed and backing up 150k messages.",
            affected_services=["notification-service"],
            trigger_event="Batch marketing trigger publishing legacy event schema",
            recommended_remediation="restart_service",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="metric",
                    source="notification-service",
                    key_pattern="queue_depth_messages",
                    description="Queue backlog accumulation past 150k messages",
                ),
                ExpectedEvidence(
                    evidence_type="log",
                    source="notification-service",
                    key_pattern="ConsumerCrashException: Unhandled serialization format",
                    description="Consumer crash logs with poison pill message",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-QUEUE-BACKLOG-10",
            "title": "Notification Queue Depth > 100,000 Messages",
            "severity": "SEV2",
            "service": "notification-service",
            "timestamp": now.isoformat(),
            "metric_name": "rabbitmq_queue_messages_unacknowledged",
            "threshold_value": 10000.0,
            "current_value": 154200.0,
            "description": "Notification service queue depth exceeded critical operating limit",
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
                        "message": "Consumer worker-1 consumed 500 messages/sec. Backlog clearing.",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "notification-service",
                        "message": "ConsumerCrashException: Unhandled serialization format in message_id='msg-99214'. Worker terminated abnormally.",
                    }
                )
            cur += timedelta(seconds=20)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"queue_depth_messages": [], "consumption_rate": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["queue_depth_messages"].append({"timestamp": ts, "value": 1200.0})
                data["consumption_rate"].append({"timestamp": ts, "value": 480.0})
            else:
                data["queue_depth_messages"].append({"timestamp": ts, "value": 154200.0})
                data["consumption_rate"].append({"timestamp": ts, "value": 0.0})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        return []

    def get_deployments(self) -> list[dict]:
        return []

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type in ["restart_service", "clear_cache"]
            and parameters.get("target_service") == "notification-service"
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "notification-service consumers restarted with dead-letter queue routing"
        return False, f"Action {action_type} failed to resume queue consumption"
