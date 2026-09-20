"""Webhook ingestion routes for external monitoring alerts (Prometheus, Datadog, PagerDuty)."""

from typing import Any

from fastapi import APIRouter, status

from apps.api.schemas.webhook import AlertWebhookPayload
from apps.api.services.incident_service import default_incident_service
from src.observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


@router.post(
    "/alerts",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest external monitoring alert",
    description="Receives firing alerts from Prometheus Alertmanager, Datadog, or PagerDuty and triggers autonomous investigation.",
)
async def ingest_alert_webhook(payload: AlertWebhookPayload) -> dict[str, Any]:
    logger.info(
        f"Webhook received alert: [{payload.alert_name}] on [{payload.service}] (severity: {payload.severity})"
    )

    if payload.status == "resolved":
        logger.info(f"Alert [{payload.alert_name}] marked as resolved by provider. Skipping triage.")
        return {"status": "ignored", "reason": "Alert status is resolved"}

    # Provision incident and launch investigation
    incident = default_incident_service.create_incident(
        title=f"{payload.alert_name}: {payload.summary}",
        severity=payload.severity,
        affected_services=[payload.service],
        symptoms=payload.description or payload.summary,
    )

    return {
        "status": "ingested",
        "incident_id": incident.id,
        "message": f"Autonomous investigation started for {payload.service}",
    }
