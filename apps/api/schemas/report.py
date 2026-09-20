"""Pydantic schemas for postmortem incident reports."""

from datetime import datetime

from pydantic import BaseModel, Field


class PostmortemReportResponse(BaseModel):
    """Structured postmortem report capturing the complete incident lifecycle."""

    incident_id: str
    title: str
    severity: str
    status: str
    lead_service: str
    detected_at: datetime
    resolved_at: datetime | None = None
    mttd_seconds: int = Field(description="Mean Time to Detect in seconds")
    mttr_seconds: int = Field(description="Mean Time to Remediate in seconds")
    executive_summary: str
    root_cause_analysis: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    remediation_summary: str
    five_whys: list[str] = Field(default_factory=list)
    preventative_actions: list[str] = Field(default_factory=list)
    full_markdown: str
