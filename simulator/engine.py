"""Master simulation orchestrator managing scenario injection and recovery verification."""

from datetime import UTC, datetime, timedelta

from simulator.scenarios.base import BaseScenario
from simulator.scenarios.catalog import ScenarioCatalog
from simulator.services.mock_repo import CommitRecord, DeploymentEvent, MockCodeRepository
from simulator.services.topology import ServiceTopology
from simulator.telemetry.generator import TelemetryGenerator
from simulator.telemetry.store import TelemetryStore


class SimulationEngine:
    """End-to-end incident simulator coordinating services, code repositories,
    telemetry generation, and remediation verification.
    """

    def __init__(self) -> None:
        self.topology = ServiceTopology()
        self.repository = MockCodeRepository()
        self.telemetry_store = TelemetryStore()
        self.generator = TelemetryGenerator(self.telemetry_store)
        self.active_scenario: BaseScenario | None = None
        self.scenario_start_time: datetime | None = None

    def reset(self) -> None:
        """Resets the simulation environment to a pristine state."""
        self.topology = ServiceTopology()
        self.repository = MockCodeRepository()
        self.telemetry_store.clear()
        self.active_scenario = None
        self.scenario_start_time = None

    def load_scenario(self, scenario_id: str) -> dict:
        """Injects a scenario, populates mock repo history, and generates telemetry.
        Returns the initial incident alert dictionary.
        """
        self.reset()
        scenario = ScenarioCatalog.create_scenario(scenario_id)
        self.active_scenario = scenario
        self.active_scenario.is_active = True

        now = datetime.now(UTC)
        self.scenario_start_time = now - timedelta(minutes=15)
        scenario.incident_started_at = self.scenario_start_time

        # 1. Populate mock repository commits
        for c in scenario.get_commits():
            self.repository.record_commit(
                CommitRecord(
                    commit_sha=c["commit_sha"],
                    service=c["service"],
                    author=c["author"],
                    message=c["message"],
                    timestamp=datetime.fromisoformat(c["timestamp"]),
                    changed_files=c.get("changed_files", []),
                    diff=c.get("diff", ""),
                )
            )

        # 2. Populate mock deployment events
        for d in scenario.get_deployments():
            self.repository.record_deployment(
                DeploymentEvent(
                    deployment_id=d["deployment_id"],
                    service=d["service"],
                    version=d["version"],
                    previous_version=d["previous_version"],
                    timestamp=datetime.fromisoformat(d["timestamp"]),
                    deployed_by=d["deployed_by"],
                    status=d.get("status", "SUCCESS"),
                    commit_sha=d.get("commit_sha", ""),
                    config_changes=d.get("config_changes", {}),
                )
            )

        # 3. Generate 30 minutes of baseline background telemetry
        baseline_start = now - timedelta(minutes=45)
        baseline_end = self.scenario_start_time
        self.generator.generate_background_traffic(baseline_start, baseline_end)

        # 4. Inject incident telemetry up to now
        self.generator.inject_scenario_telemetry(scenario, self.scenario_start_time, now)

        # 5. Degrade affected service statuses in topology
        for svc in scenario.ground_truth.affected_services:
            self.topology.set_service_status(svc, "DEGRADED")

        return scenario.get_initial_alert()

    def execute_action(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        """Executes a remediation action against the active scenario and generates
        post-action telemetry for recovery verification.
        """
        if not self.active_scenario:
            return False, "No active scenario loaded in simulator"

        success, message = self.active_scenario.apply_remediation(action_type, parameters)

        # If scenario-specific remediation didn't trigger, handle standard infra actions as operational successes
        if not success and action_type in ["scale_replicas", "clear_cache"]:
            target = parameters.get("target_service", "service")
            if action_type == "scale_replicas":
                replicas = parameters.get("replicas", 1)
                success = True
                message = f"{target} replica count adjusted to {replicas} (did not remediate root cause)"
            elif action_type == "clear_cache":
                success = True
                message = f"Transient cache cleared for {target} (did not remediate root cause)"

        if success and self.active_scenario.is_remediated:
            # Restore healthy status in topology
            for svc in self.active_scenario.ground_truth.affected_services:
                self.topology.set_service_status(svc, "HEALTHY")

            # Generate 10 minutes of recovered telemetry into the store
            now = datetime.now(UTC)
            post_start = now
            post_end = now + timedelta(minutes=10)
            self.generator.inject_scenario_telemetry(self.active_scenario, post_start, post_end)

        return success, message


# Global simulator singleton
default_simulator = SimulationEngine()
