"""Central registry and factory for all 10 incident simulation scenarios."""

from collections.abc import Callable

from simulator.scenarios.api_timeout import APITimeoutScenario
from simulator.scenarios.bad_deployment import BadDeploymentScenario
from simulator.scenarios.base import BaseScenario, GroundTruth
from simulator.scenarios.cpu_saturation import CPUSaturationScenario
from simulator.scenarios.db_connection_exhaustion import DBConnectionExhaustionScenario
from simulator.scenarios.downstream_failure import DownstreamFailureScenario
from simulator.scenarios.invalid_config import InvalidConfigScenario
from simulator.scenarios.memory_leak import MemoryLeakScenario
from simulator.scenarios.queue_backlog import QueueBacklogScenario
from simulator.scenarios.redis_pool_exhaustion import RedisPoolExhaustionScenario
from simulator.scenarios.slow_query import SlowQueryScenario

SCENARIO_REGISTRY: dict[str, Callable[[], BaseScenario]] = {
    "redis_pool_exhaustion": RedisPoolExhaustionScenario,
    "db_connection_exhaustion": DBConnectionExhaustionScenario,
    "slow_query": SlowQueryScenario,
    "memory_leak": MemoryLeakScenario,
    "cpu_saturation": CPUSaturationScenario,
    "downstream_failure": DownstreamFailureScenario,
    "bad_deployment": BadDeploymentScenario,
    "invalid_config": InvalidConfigScenario,
    "api_timeout": APITimeoutScenario,
    "queue_backlog": QueueBacklogScenario,
}


class ScenarioCatalog:
    """Provides lookup, instantiation, and ground-truth isolation."""

    @classmethod
    def list_scenario_ids(cls) -> list[str]:
        return list(SCENARIO_REGISTRY.keys())

    @classmethod
    def create_scenario(cls, scenario_id: str) -> BaseScenario:
        if scenario_id not in SCENARIO_REGISTRY:
            raise KeyError(
                f"Unknown scenario_id '{scenario_id}'. Available: {cls.list_scenario_ids()}"
            )
        return SCENARIO_REGISTRY[scenario_id]()

    @classmethod
    def get_ground_truth(cls, scenario_id: str) -> GroundTruth:
        """Retrieves ground truth for evaluation. NEVER expose to runtime agents."""
        instance = cls.create_scenario(scenario_id)
        return instance.ground_truth
