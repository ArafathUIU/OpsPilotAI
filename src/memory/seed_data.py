"""Curated historical postmortems for seeding episodic incident memory."""

from typing import Any

from pydantic import BaseModel, Field


class HistoricalPostmortem(BaseModel):
    """Structured postmortem document capturing lessons learned and remediation history."""

    incident_id: str
    title: str
    service: str
    severity: str
    summary: str
    root_cause: str
    detection_signals: list[str] = Field(default_factory=list)
    remediation_steps: list[str] = Field(default_factory=list)
    prevention_measures: list[str] = Field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


HISTORICAL_POSTMORTEMS: list[HistoricalPostmortem] = [
    HistoricalPostmortem(
        incident_id="PM-2025-001",
        title="Redis Connection Pool Starvation Under Flash Sale Traffic",
        service="order-service",
        severity="SEV-1",
        summary=(
            "Order Service experienced catastrophic degradation and HTTP 500 error spikes "
            "during a peak traffic spike. Investigation revealed Redis connection pool exhaustion "
            "as max_connections was hardcoded to 10."
        ),
        root_cause=(
            "Connection acquisition timeouts in Redis client pool. Maximum connection limit "
            "was capped at 10 while incoming concurrency surged to 250 requests/sec, "
            "causing blocked coroutines to time out waiting for Redis handles."
        ),
        detection_signals=[
            "TimeoutError: Timeout acquiring Redis connection from pool",
            "Redis client connection pool saturated (active_connections=10, max=10)",
            "Order creation p99 latency spiked from 45ms to 12,000ms",
        ],
        remediation_steps=[
            "Increased REDIS_MAX_CONNECTIONS from 10 to 100 via environment variable patch",
            "Added connection acquisition timeout of 500ms with fallback to degraded cache",
            "Executed graceful rolling restart of order-service pods",
        ],
        prevention_measures=[
            "Configured Prometheus alerts on redis_connected_clients / redis_max_connections > 0.8",
            "Introduced automated load testing for connection pool sizing in staging",
        ],
        metadata={"category": "resource_exhaustion", "component": "redis"},
    ),
    HistoricalPostmortem(
        incident_id="PM-2025-002",
        title="Database Connection Exhaustion from Slow Query Lock Contention",
        service="payment-service",
        severity="SEV-1",
        summary=(
            "Payment service degraded with asyncpg PoolTimeout errors. Database connection pool "
            "was starved by long-running unindexed transaction table queries."
        ),
        root_cause=(
            "A missing composite index on transactions(user_id, status) caused sequential table scans "
            "holding database connections open for >8 seconds each, saturating the max pool size of 20."
        ),
        detection_signals=[
            "asyncpg.exceptions.PoolTimeoutError: pool timed out after 30.0 seconds",
            "Postgres active connections reached max_connections limit",
            "Payment authorization failure rate escalated to 65%",
        ],
        remediation_steps=[
            "Terminated stuck read-only queries with pg_terminate_backend",
            "Added concurrent index CREATE INDEX CONCURRENTLY idx_tx_user_status",
            "Increased database connection pool max_size from 20 to 50",
        ],
        prevention_measures=[
            "Enabled pg_stat_statements monitoring with automated alerts on queries > 200ms",
            "Enforced query EXPLAIN validation in CI/CD pipeline",
        ],
        metadata={"category": "database", "component": "postgres"},
    ),
    HistoricalPostmortem(
        incident_id="PM-2025-003",
        title="Memory Leak in Auth Token Validation Service",
        service="auth-service",
        severity="SEV-2",
        summary=(
            "Auth Service nodes suffered progressive memory exhaustion and eventual OOM kills "
            "due to an unbounded token validation cache."
        ),
        root_cause=(
            "In-memory token blacklist cache grew monotonically without eviction or TTL policy, "
            "consuming all container heap over a 48-hour period."
        ),
        detection_signals=[
            "Container killed: OOMKilled (exit code 137)",
            "Memory usage monotonically climbed to 100% (512MiB cap)",
            "JWT validation latency degraded prior to process crashes",
        ],
        remediation_steps=[
            "Replaced unbounded Python dictionary with bounded TTLCache (maxsize=50000, ttl=3600)",
            "Temporarily increased container memory limit from 512MiB to 1GiB",
            "Restarted auth-service deployment to reclaim leaked memory",
        ],
        prevention_measures=[
            "Added automated leak detection tests in staging test suites",
            "Created memory slope anomaly alert in Prometheus",
        ],
        metadata={"category": "memory_leak", "component": "jwt_cache"},
    ),
    HistoricalPostmortem(
        incident_id="PM-2025-004",
        title="Cascading Failure Caused by Downstream Notification Service Hang",
        service="notification-service",
        severity="SEV-2",
        summary=(
            "Notification service third-party webhook provider experienced an outage, causing "
            "upstream order-service worker threads to block waiting for HTTP responses."
        ),
        root_cause=(
            "HTTP client calling downstream webhook endpoint lacked client-side socket timeouts, "
            "causing caller threads to block indefinitely and back up the message processing queue."
        ),
        detection_signals=[
            "Downstream HTTP request timeout after 60000ms",
            "Notification queue depth increased from 10 to 45,000 messages",
            "Worker thread pool 100% busy in WAITING state",
        ],
        remediation_steps=[
            "Configured aggressive 3-second connect and read timeouts on webhook HTTP client",
            "Enabled circuit breaker to fast-fail notification delivery during upstream outages",
            "Drained stuck dead-letter queue messages into asynchronous cold storage",
        ],
        prevention_measures=[
            "Mandated non-blocking circuit breaker wrappers for all external third-party APIs",
            "Added queue depth rate-of-change alerting",
        ],
        metadata={"category": "downstream_failure", "component": "http_client"},
    ),
    HistoricalPostmortem(
        incident_id="PM-2025-005",
        title="Invalid Routing Configuration in API Gateway Envoy Proxy",
        service="api-gateway",
        severity="SEV-1",
        summary=(
            "API Gateway dropped 40% of ingress requests following a GitOps deployment "
            "containing malformed regex route matchers."
        ),
        root_cause=(
            "A syntax error in Envoy virtual host routing configuration caused the proxy "
            "to reject traffic destined for order and payment clusters with HTTP 503 Service Unavailable."
        ),
        detection_signals=[
            "Envoy error: [config] error loading virtual_host routes: invalid regex",
            "HTTP 503 Service Unavailable spike across /api/v1/orders and /api/v1/payments",
            "GitOps sync status failed with validation error",
        ],
        remediation_steps=[
            "Executed automated GitOps rollback to previous healthy Git commit SHA",
            "Reloaded Envoy proxy routing configuration without pod restarts",
            "Verified traffic restoration via synthetic health checks",
        ],
        prevention_measures=[
            "Added pre-commit schema and regex validation hook for Envoy config",
            "Instituted canary deployment rollout requiring 5 minutes of 0% error rate",
        ],
        metadata={"category": "bad_deployment", "component": "gateway_config"},
    ),
]
