"""Verification result ORM model confirming post-remediation health."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.incident import Incident


class VerificationResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Empirical assessment of recovery following an executed remediation."""

    __tablename__ = "verification_results"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # RESOLVED, PARTIALLY_RESOLVED, NOT_RESOLVED, INCONCLUSIVE
    metric_observations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    log_observations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recovery_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident")
