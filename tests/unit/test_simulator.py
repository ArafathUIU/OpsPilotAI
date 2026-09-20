"""Unit tests for the incident simulation engine, topology, and ground-truth scenarios."""

from simulator.engine import SimulationEngine
from simulator.scenarios.catalog import ScenarioCatalog
from simulator.services.topology import ServiceTopology


def test_service_topology_dependencies():
    topology = ServiceTopology()

    # 5 standard services
    services = topology.list_services()
    assert len(services) == 5

    # API Gateway depends on payment-service
    gateway = topology.get_service("api-gateway")
    assert gateway is not None
    assert "payment-service" in gateway.dependencies

    # payment-service upstream dependent is api-gateway and order-service
    upstream = topology.get_upstream_dependents("payment-service")
    assert "api-gateway" in upstream
    assert "order-service" in upstream


def test_all_ten_scenarios_registered_with_ground_truth():
    scenario_ids = ScenarioCatalog.list_scenario_ids()
    assert len(scenario_ids) == 10

    expected_ids = [
        "redis_pool_exhaustion",
        "db_connection_exhaustion",
        "slow_query",
        "memory_leak",
        "cpu_saturation",
        "downstream_failure",
        "bad_deployment",
        "invalid_config",
        "api_timeout",
        "queue_backlog",
    ]
    for exp_id in expected_ids:
        assert exp_id in scenario_ids
        scenario = ScenarioCatalog.create_scenario(exp_id)
        gt = scenario.ground_truth
        assert gt.scenario_id == exp_id
        assert len(gt.affected_services) > 0
        assert len(gt.root_cause) > 10
        assert len(gt.expected_evidence) > 0
        assert gt.recommended_remediation in [
            "rollback_deployment",
            "restart_service",
            "modify_configuration",
            "scale_replicas",
            "clear_cache",
        ]


def test_redis_pool_exhaustion_simulation_and_recovery():
    engine = SimulationEngine()

    # 1. Load scenario
    alert = engine.load_scenario("redis_pool_exhaustion")
    assert alert["service"] == "payment-service"
    assert "2.8" in alert["title"]
    assert alert["severity"] == "SEV1"

    # 2. Verify affected service degraded in topology
    service = engine.topology.get_service("payment-service")
    assert service is not None
    assert service.status == "DEGRADED"

    # 3. Verify mock commits & deployments present in repository
    commits = engine.repository.get_recent_commits("payment-service")
    assert len(commits) >= 1
    assert "max_connections" in commits[0].diff

    deployments = engine.repository.get_recent_deployments("payment-service")
    assert len(deployments) == 1
    assert deployments[0].version == "v2.4.1"

    # 4. Verify telemetry store has incident logs & metrics
    logs = engine.telemetry_store.query_logs(
        service="payment-service", pattern="RedisTimeoutException"
    )
    assert len(logs) > 0

    metrics = engine.telemetry_store.query_metrics(
        metric_name="p95_latency_ms", service="payment-service"
    )
    assert len(metrics) > 0
    assert metrics[-1].value > 2000.0

    # 5. Execute correct remediation action: rollback
    success, message = engine.execute_action(
        "rollback_deployment", {"target_service": "payment-service"}
    )
    assert success is True
    assert "rolled back" in message

    # 6. Verify service health restored in topology
    assert engine.topology.get_service("payment-service").status == "HEALTHY"

    # 7. Verify post-remediation metrics normalize
    recovered_metrics = engine.telemetry_store.query_metrics(
        metric_name="p95_latency_ms", service="payment-service"
    )
    assert recovered_metrics[-1].value < 300.0  # Latency returned to ~265ms
