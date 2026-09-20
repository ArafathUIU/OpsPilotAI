"""Incident and IncidentEvent ORM models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.approval import ApprovalRequestModel
    from src.persistence.models.evidence import EvidenceModel
    from src.persistence.models.execution import ActionExecutionModel
    from src.persistence.models.hypothesis import HypothesisModel
    from src.persistence.models.remediation import RemediationActionModel
    from src.persistence.models.report import IncidentReportModel


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core incident tracking record."""

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), default="SEV2", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), default="CREATED", nullable=False)

    # List of affected microservices stored as JSON
    affected_services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Financial and resource cost governance
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    events: Mapped[list["IncidentEvent"]] = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.created_at",
        lazy="selectin",
    )
    evidence_items: Mapped[list["EvidenceModel"]] = relationship(
        "EvidenceModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    hypotheses: Mapped[list["HypothesisModel"]] = relationship(
        "HypothesisModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    remediation_actions: Mapped[list["RemediationActionModel"]] = relationship(
        "RemediationActionModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    approval_requests: Mapped[list["ApprovalRequestModel"]] = relationship(
        "ApprovalRequestModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[list["ActionExecutionModel"]] = relationship(
        "ActionExecutionModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    report: Mapped["IncidentReportModel | None"] = relationship(
        "IncidentReportModel",
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class IncidentEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chronological log of investigation events, state transitions, and agent messages."""

    __tablename__ = "incident_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")
