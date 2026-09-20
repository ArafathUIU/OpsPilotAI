"""Base class and Ground Truth definitions for incident simulation scenarios."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExpectedEvidence(BaseModel):
    """Ground-truth evidence item expected to be uncovered during investigation."""

    evidence_type: Literal["log", "metric", "code", "memory", "config"]
    source: str
    key_pattern: str
    description: str


class GroundTruth(BaseModel):
    """Ground truth metadata for an incident scenario.

    IMPORTANT: Ground truth is strictly quarantined from AI agents during runtime
    and is only accessible by the evaluation framework.
    """

    scenario_id: str
    name: str
    root_cause: str
    affected_services: list[str]
    trigger_event: str
    recommended_remediation: str
    expected_evidence: list[ExpectedEvidence]
    forbidden_claims: list[str] = Field(
        default_factory=list,
        description="Plausible red herrings or incorrect correlation hypotheses",
    )


class BaseScenario(ABC):
    """Abstract base class for all incident simulation scenarios."""

    def __init__(self, ground_truth: GroundTruth) -> None:
        self.ground_truth = ground_truth
        self.is_active: bool = False
        self.is_remediated: bool = False
        self.incident_started_at: datetime | None = None
        self.remediated_at: datetime | None = None

    @abstractmethod
    def get_initial_alert(self) -> dict:
        """Returns the initial Prometheus/Webhook alert payload that triggers OpsPilot."""
        pass

    @abstractmethod
    def generate_logs(self, start_time: datetime, end_time: datetime) -> list[dict]:
        """Generates realistic application logs for the given time window."""
        pass

    @abstractmethod
    def generate_metrics(self, start_time: datetime, end_time: datetime) -> dict[str, list[dict]]:
        """Generates time-series metric data points (e.g. latency, error rate, CPU, connections)."""
        pass

    @abstractmethod
    def get_commits(self) -> list[dict]:
        """Returns mock git commits associated with this scenario."""
        pass

    @abstractmethod
    def get_deployments(self) -> list[dict]:
        """Returns mock deployment events associated with this scenario."""
        pass

    @abstractmethod
    def apply_remediation(self, action_type: str, parameters: dict) -> tuple[bool, str]:
        """Executes a remediation action against the simulated environment.
        Returns: (success: bool, output_message: str)
        """
        pass
