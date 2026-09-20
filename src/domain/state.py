"""Domain state models and structured agent communication contracts."""

import operator
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

IncidentStage = Literal[
    "CREATED",
    "PLANNING",
    "INVESTIGATING",
    "ANALYZING",
    "CRITIQUING",
    "REMEDIATION_PLANNING",
    "RISK_ASSESSMENT",
    "WAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "RESOLVED",
    "FAILED",
    "ESCALATED",
]


class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stage: IncidentStage
    actor: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    id: str = Field(description="Normalized unique identifier e.g. EV-LOG-01")
    type: Literal["log", "metric", "code", "memory", "config"]
    source: str = Field(description="Originating service e.g. payment-service")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation: str = Field(description="Factual, verifiable observation")
    raw_reference: str = Field(description="Exact log message, metric query, or commit SHA")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Confidence in relevance")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    id: str = Field(description="Unique hypothesis identifier e.g. HYP-01")
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: list[str] = Field(
        description="Must reference valid Evidence IDs (e.g. ['EV-LOG-01', 'EV-MET-02'])"
    )
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    reasoning_summary: str
    missing_information: list[str] = Field(default_factory=list)
    suggested_validation: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    decision: Literal["APPROVE", "CHALLENGE", "NEEDS_MORE_EVIDENCE"]
    critique_notes: str
    counter_hypotheses: list[str] = Field(default_factory=list)
    required_evidence_queries: list[str] = Field(default_factory=list)


class InvestigationTask(BaseModel):
    task_id: str
    agent_type: Literal["log_analyst", "metrics_analyst", "code_analyst", "memory_analyst"]
    target_service: str
    query_intent: str
    time_window_minutes: int = 15


class SupervisorPlan(BaseModel):
    triage_assessment: str
    initial_severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"]
    suspected_domains: list[str]
    tasks: list[InvestigationTask]
    reasoning: str


class AnalystAgentOutput(BaseModel):
    agent_type: str
    service: str
    findings_summary: str
    evidence_items: list[Evidence]
    anomalies_detected: bool


class RCAAgentOutput(BaseModel):
    hypotheses: list[Hypothesis]
    primary_hypothesis_id: str
    confidence_rationale: str


class IncidentState(BaseModel):
    """Primary LangGraph state representing the shared working memory across agents."""

    incident_id: str
    title: str
    severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"]
    affected_services: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_stage: IncidentStage = "CREATED"

    # Reducer fields for LangGraph concurrent branch merging
    investigation_tasks: list[InvestigationTask] = Field(default_factory=list)
    evidence: Annotated[list[Evidence], operator.add] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    selected_hypothesis: Hypothesis | None = None
    critique: CritiqueResult | None = None

    timeline: Annotated[list[TimelineEvent], operator.add] = Field(default_factory=list)
    errors: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Cost and iteration governance
    iteration_count: int = 0
    max_iterations: int = 3
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
