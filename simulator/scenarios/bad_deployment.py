"""Scenario 7: Bad deployment breaking routing."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario, ExpectedEvidence, GroundTruth


class BadDeploymentScenario(BaseScenario):
    """API gateway v2.2.0 deployment introduced invalid regex in routing table,
    dropping all incoming /api/v1 traffic with 404 Not Found.
    """

    def __init__(self) -> None:
        truth = GroundTruth(
            scenario_id="bad_deployment",
            name="Corrupted Route Config Deployment",
            root_cause="API Gateway v2.2.0 deployment contained a malformed route prefix in routes.yaml, breaking route matching for all microservices.",
            affected_services=["api-gateway"],
            trigger_event="Deployment of api-gateway:v2.2.0",
            recommended_remediation="rollback_deployment",
            expected_evidence=[
                ExpectedEvidence(
                    evidence_type="code",
                    source="api-gateway",
                    key_pattern="routes.yaml",
                    description="Commit diff introducing broken route regex",
                ),
                ExpectedEvidence(
                    evidence_type="log",
                    source="api-gateway",
                    key_pattern="RouteMatchException: Invalid regex pattern syntax",
                    description="Gateway log reporting route failure",
                ),
            ],
        )
        super().__init__(truth)

    def get_initial_alert(self) -> dict:
        now = datetime.now(UTC)
        return {
            "alert_id": "ALT-BAD-DEPLOY-07",
            "title": "API Gateway 4xx Error Spike > 80%",
            "severity": "SEV1",
            "service": "api-gateway",
            "timestamp": now.isoformat(),
            "metric_name": "gateway_requests_404_ratio",
            "threshold_value": 0.10,
            "current_value": 0.88,
            "description": "API Gateway dropping 88% of incoming traffic following deployment",
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
                        "message": "Route /api/v1/orders matched to order-service:8082 [200 OK]",
                    }
                )
            else:
                logs.append(
                    {
                        "timestamp": cur.isoformat(),
                        "level": "ERROR",
                        "service": "api-gateway",
                        "message": "RouteMatchException: Invalid regex pattern syntax in routes.yaml near line 14: unmatched parenthesis '(/api/v1/(orders|payments)'",
                    }
                )
            cur += timedelta(seconds=15)
        return logs

    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        data: dict[str, list[dict]] = {"gateway_404_rate": [], "success_rate": []}
        cur = start_time
        while cur <= end_time:
            ts = cur.isoformat()
            if self.is_remediated:
                data["gateway_404_rate"].append({"timestamp": ts, "value": 0.01})
                data["success_rate"].append({"timestamp": ts, "value": 99.9})
            else:
                data["gateway_404_rate"].append({"timestamp": ts, "value": 88.4})
                data["success_rate"].append({"timestamp": ts, "value": 11.6})
            cur += timedelta(seconds=30)
        return data

    def get_commits(self) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "commit_sha": "f5e4d3c2b1a0",
                "service": "api-gateway",
                "author": "devops@company.internal",
                "message": "refactor: simplify route matching regex in gateway config",
                "timestamp": (now - timedelta(minutes=10)).isoformat(),
                "changed_files": ["config/routes.yaml"],
                "diff": (
                    "--- a/config/routes.yaml\n"
                    "+++ b/config/routes.yaml\n"
                    "@@ -14,1 +14,1 @@\n"
                    "-  pattern: ^/api/v1/(orders|payments|auth)/.*$\n"
                    "+  pattern: (/api/v1/(orders|payments\n"
                ),
            }
        ]

    def get_deployments(self) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "deployment_id": "dep-gateway-102",
                "service": "api-gateway",
                "version": "v2.2.0",
                "previous_version": "v2.1.0",
                "timestamp": (now - timedelta(minutes=8)).isoformat(),
                "deployed_by": "ci-runner",
                "status": "SUCCESS",
                "commit_sha": "f5e4d3c2b1a0",
                "config_changes": {"routes_version": "v2.2"},
            }
        ]

    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        if (
            action_type == "rollback_deployment"
            and parameters.get("target_service") == "api-gateway"
        ):
            self.is_remediated = True
            self.remediated_at = datetime.now(UTC)
            return True, "api-gateway rolled back to v2.1.0; route parsing normalized"
        return False, f"Action {action_type} failed to remediate bad deployment"
