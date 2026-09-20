"""Pydantic schemas for Incident API requests, responses, and summaries."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.domain.state import IncidentStage


class IncidentCreateRequest(BaseModel):
    """Payload to manually trigger or simulate an incident investigation."""

    title: str = Field(description="Incident title e.g. Payment Service Latency Spike")
    severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"] = "SEV1"
    affected_services: list[str] = Field(description="List of target microservices")
    symptoms: str = Field(default="", description="Observed error logs, latency spikes, or alerts")
    auto_remediate: bool = Field(default=False, description="Whether low-risk actions can execute automatically")


class EvidenceResponse(BaseModel):
    """Structured evidence item representation."""

    id: str
    type: str
    source: str
    timestamp: datetime
    observation: str
    raw_reference: str
    relevance_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class HypothesisResponse(BaseModel):
    """Causal root cause hypothesis representation."""

    id: str
    title: str
    description: str
    confidence: float
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    reasoning_summary: str


class TimelineEventResponse(BaseModel):
    """Timeline audit record representation."""

    timestamp: datetime
    stage: str
    actor: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentResponse(BaseModel):
    """Complete incident overview response model."""

    id: str
    title: str
    severity: str
    current_stage: IncidentStage
    affected_services: list[str]
    created_at: datetime
    resolved_at: datetime | None = None
    confidence_score: float = 0.0
    evidence_count: int = 0
    hypotheses_count: int = 0
    selected_hypothesis_title: str | None = None
    verification_status: str | None = None
