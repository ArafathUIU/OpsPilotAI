"""Remediation action ORM model for mitigating root causes."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.approval import ApprovalRequestModel
    from src.persistence.models.execution import ActionExecutionModel
    from src.persistence.models.incident import Incident


class RemediationActionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured remediation action planned by the Remediation Agent."""

    __tablename__ = "remediation_actions"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_service: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_effect: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    reversibility: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rollback_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="remediation_actions")
    approvals: Mapped[list["ApprovalRequestModel"]] = relationship(
        "ApprovalRequestModel",
        back_populates="action",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[list["ActionExecutionModel"]] = relationship(
        "ActionExecutionModel",
        back_populates="action",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
