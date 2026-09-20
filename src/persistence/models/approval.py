"""Approval request ORM model for Human-in-the-loop governance."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.incident import Incident
    from src.persistence.models.remediation import RemediationActionModel


class ApprovalRequestModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Human approval record required before high-risk execution."""

    __tablename__ = "approval_requests"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("remediation_actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING, APPROVED, REJECTED, EXPIRED
    approver_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="approval_requests")
    action: Mapped["RemediationActionModel"] = relationship(
        "RemediationActionModel", back_populates="approvals"
    )
