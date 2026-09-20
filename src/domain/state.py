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


ActionType = Literal[
    "restart_service",
    "rollback_deployment",
    "scale_replicas",
    "modify_configuration",
    "run_query",
    "clear_cache",
]

RiskTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class RemediationAction(BaseModel):
    """Concrete remediation operation planned by the Remediation Agent."""

    action_id: str = Field(description="Unique action ID e.g. ACT-ROLLBACK-01")
    action_type: ActionType
    target_service: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str
    rationale: str
    rollback_plan: str
    risk_tier: RiskTier = "MEDIUM"
    risk_score: float = Field(ge=0.0, le=1.0, default=0.5)
    requires_approval: bool = True
    estimated_downtime_seconds: int = 0
    idempotency_key: str = ""


class RemediationPlan(BaseModel):
    """Ordered remediation actions formulated from validated root causes."""

    incident_id: str
    hypothesis_id: str
    actions: list[RemediationAction]
    summary: str
    prevention_recommendations: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    """Human or automated policy decision on a pending remediation action."""

    action_id: str
    decision: Literal["APPROVED", "REJECTED", "MODIFIED"]
    decided_by: str  # user id or 'policy_engine:auto'
    reason: str
    modified_parameters: dict[str, Any] | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionExecutionResult(BaseModel):
    """Audit record of a dispatched remediation tool run."""

    action_id: str
    status: Literal["SUCCESS", "FAILED", "ROLLED_BACK"]
    output: str
    error_message: str | None = None
    duration_ms: float = 0.0
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VerificationAssessment(BaseModel):
    """Post-remediation empirical assessment evaluating health recovery."""

    status: Literal["RECOVERED", "PARTIALLY_RECOVERED", "UNCHANGED", "DEGRADED"]
    metrics_comparison: dict[str, Any] = Field(default_factory=dict)
    service_statuses: dict[str, str] = Field(default_factory=dict)
    rollback_recommended: bool = False
    explanation: str


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

    # Phase 5: Remediation, Governance, Execution & Verification
    remediation_plan: RemediationPlan | None = None
    pending_approvals: list[RemediationAction] = Field(default_factory=list)
    approval_decisions: list[ApprovalDecision] = Field(default_factory=list)
    execution_results: list[ActionExecutionResult] = Field(default_factory=list)
    verification: VerificationAssessment | None = None

    timeline: Annotated[list[TimelineEvent], operator.add] = Field(default_factory=list)
    errors: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Cost and iteration governance
    iteration_count: int = 0
    max_iterations: int = 3
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
