"""Microservice topology, metadata, and dependency graph."""

from typing import Literal

from pydantic import BaseModel, Field

ServiceStatus = Literal["HEALTHY", "DEGRADED", "DOWN"]


class ServiceNode(BaseModel):
    name: str
    display_name: str
    description: str
    tier: Literal["frontend", "gateway", "business", "data", "external"]
    dependencies: list[str] = Field(default_factory=list)
    default_port: int
    health_endpoint: str = "/health"
    version: str = "v1.0.0"
    status: ServiceStatus = "HEALTHY"


# Complete 5-tier microservice architecture
DEFAULT_TOPOLOGY: dict[str, ServiceNode] = {
    "api-gateway": ServiceNode(
        name="api-gateway",
        display_name="API Gateway",
        description="Public edge router handling SSL termination, rate limiting, and request routing.",
        tier="gateway",
        dependencies=["auth-service", "order-service", "payment-service"],
        default_port=8080,
        version="v2.1.0",
    ),
    "auth-service": ServiceNode(
        name="auth-service",
        display_name="Authentication Service",
        description="Issues and validates JWT tokens and handles user permissions.",
        tier="business",
        dependencies=[],
        default_port=8081,
        version="v1.4.2",
    ),
    "order-service": ServiceNode(
        name="order-service",
        display_name="Order Processing Service",
        description="Manages shopping carts, checkout workflows, and order state.",
        tier="business",
        dependencies=["payment-service", "notification-service"],
        default_port=8082,
        version="v3.0.1",
    ),
    "payment-service": ServiceNode(
        name="payment-service",
        display_name="Payment Processing Service",
        description="Executes credit card authorizations, gateway tokens, and Redis cache transactions.",
        tier="business",
        dependencies=["notification-service"],
        default_port=8083,
        version="v2.4.0",
    ),
    "notification-service": ServiceNode(
        name="notification-service",
        display_name="Notification Service",
        description="Sends emails, SMS alerts, and async webhooks via RabbitMQ/Kafka queue.",
        tier="business",
        dependencies=[],
        default_port=8084,
        version="v1.2.0",
    ),
}


class ServiceTopology:
    """Manages service topology and dependency relationships."""

    def __init__(self, services: dict[str, ServiceNode] | None = None) -> None:
        self.services = services or {
            k: v.model_copy(deep=True) for k, v in DEFAULT_TOPOLOGY.items()
        }

    def get_service(self, name: str) -> ServiceNode | None:
        return self.services.get(name)

    def list_services(self) -> list[ServiceNode]:
        return list(self.services.values())

    def get_upstream_dependents(self, service_name: str) -> list[str]:
        """Finds all services that depend on service_name."""
        dependents = []
        for name, node in self.services.items():
            if service_name in node.dependencies:
                dependents.append(name)
        return dependents

    def get_downstream_dependencies(self, service_name: str) -> list[str]:
        """Finds all services that service_name calls."""
        node = self.services.get(service_name)
        return node.dependencies if node else []

    def set_service_status(self, service_name: str, status: ServiceStatus) -> None:
        if service_name in self.services:
            self.services[service_name].status = status
