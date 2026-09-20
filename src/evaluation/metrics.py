"""Data models and metrics computation for autonomous incident evaluation."""

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Evaluation result for an individual scenario trial."""

    scenario_id: str
    scenario_name: str
    ground_truth_root_cause: str
    predicted_root_cause: str
    ground_truth_service: str
    predicted_service: str
    service_match: bool
    root_cause_similarity: float = Field(ge=0.0, le=1.0)
    remediation_action_valid: bool
    blast_radius_contained: bool
    critic_challenge_occurred: bool
    investigation_duration_ms: float
    total_evidence_count: int
    confidence_score: float = Field(ge=0.0, le=1.0)


class BenchmarkSummary(BaseModel):
    """Aggregated benchmark statistics across multiple simulated incident scenarios."""

    total_scenarios: int
    successful_attributions: int
    service_attribution_accuracy: float = Field(ge=0.0, le=100.0)
    root_cause_f1_score: float = Field(ge=0.0, le=1.0)
    remediation_validity_rate: float = Field(ge=0.0, le=100.0)
    safety_compliance_rate: float = Field(ge=0.0, le=100.0)
    mean_duration_ms: float
    average_confidence: float = Field(ge=0.0, le=1.0)
    results: list[EvaluationResult] = Field(default_factory=list)
