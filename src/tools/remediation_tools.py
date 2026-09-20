"""Active remediation tools executing infrastructure changes, rollbacks, and patches."""

from typing import Any

from simulator.engine import SimulationEngine, default_simulator
from src.tools.base import BaseTool


class RestartServiceTool(BaseTool):
    """Restarts a target service container or pod."""

    name: str = "restart_service"
    description: str = "Perform a rolling restart of the specified target microservice."
    required_role: str = "OPERATOR"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, target_service: str, **kwargs: Any) -> dict[str, Any]:
        params = {"target_service": target_service, **kwargs}
        success, message = self.simulator.execute_action("restart_service", params)
        if not success:
            raise RuntimeError(f"Failed to restart service {target_service}: {message}")
        return {
            "target_service": target_service,
            "status": "RESTARTED",
            "message": message,
        }


class RollbackDeploymentTool(BaseTool):
    """Rolls back the target service deployment to the previous healthy version."""

    name: str = "rollback_deployment"
    description: str = "Roll back a service to its prior stable release version and commit SHA."
    required_role: str = "OPERATOR"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, target_service: str, target_version: str | None = None, **kwargs: Any) -> dict[str, Any]:
        params = {"target_service": target_service, "target_version": target_version, **kwargs}
        success, message = self.simulator.execute_action("rollback_deployment", params)
        if not success:
            raise RuntimeError(f"Rollback failed for {target_service}: {message}")
        return {
            "target_service": target_service,
            "target_version": target_version,
            "status": "ROLLED_BACK",
            "message": message,
        }


class ScaleReplicasTool(BaseTool):
    """Scales replica count for a service deployment."""

    name: str = "scale_replicas"
    description: str = "Scale the horizontal replica count for a target service."
    required_role: str = "OPERATOR"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, target_service: str, replicas: int, **kwargs: Any) -> dict[str, Any]:
        params = {"target_service": target_service, "replicas": replicas, **kwargs}
        success, message = self.simulator.execute_action("scale_replicas", params)
        if not success:
            raise RuntimeError(f"Scaling failed for {target_service}: {message}")
        return {
            "target_service": target_service,
            "replicas": replicas,
            "status": "SCALED",
            "message": message,
        }


class ModifyConfigurationTool(BaseTool):
    """Patches runtime configuration settings (e.g. pool sizes, timeouts, flags)."""

    name: str = "modify_configuration"
    description: str = "Apply a targeted configuration patch to a service."
    required_role: str = "OPERATOR"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, target_service: str, config_patch: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        patch = config_patch or {}
        combined = {**patch, **kwargs, "target_service": target_service}
        success, message = self.simulator.execute_action("modify_configuration", combined)
        if not success:
            raise RuntimeError(f"Config modification failed for {target_service}: {message}")
        return {
            "target_service": target_service,
            "applied_patch": combined,
            "status": "CONFIGURED",
            "message": message,
        }


class ClearCacheTool(BaseTool):
    """Clears temporary caches or evicts stale connection handles."""

    name: str = "clear_cache"
    description: str = "Evict expired keys, purge caches, or flush transient state."
    required_role: str = "OPERATOR"

    def __init__(self, simulator: SimulationEngine | None = None) -> None:
        self.simulator = simulator or default_simulator

    async def _run(self, target_service: str, cache_type: str = "all", **kwargs: Any) -> dict[str, Any]:
        params = {"target_service": target_service, "cache_type": cache_type, **kwargs}
        success, message = self.simulator.execute_action("clear_cache", params)
        if not success:
            raise RuntimeError(f"Cache clearance failed for {target_service}: {message}")
        return {
            "target_service": target_service,
            "cache_type": cache_type,
            "status": "PURGED",
            "message": message,
        }
