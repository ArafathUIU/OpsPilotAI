"""API routes module."""

from apps.api.routes.health import router as health_router
from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.webhooks import router as webhooks_router

__all__ = ["health_router", "incidents_router", "webhooks_router"]
