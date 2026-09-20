"""Pydantic schemas for monitoring alert ingestion webhooks."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AlertWebhookPayload(BaseModel):
    """Normalized alert payload ingested from Prometheus, Datadog, or PagerDuty."""

    source: Literal["prometheus", "datadog", "pagerduty", "custom"] = "prometheus"
    status: Literal["firing", "resolved"] = "firing"
    alert_name: str = Field(description="Alert name or rule title e.g. HighHttpErrorRate")
    service: str = Field(description="Target microservice e.g. payment-service")
    severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"] = "SEV1"
    summary: str = Field(description="Concise description of the alert symptom")
    description: str = Field(default="", description="Detailed diagnostic or error snippet")
    starts_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    generator_url: str = Field(default="", description="Link back to Prometheus or monitoring dashboard")
