"""Action execution ORM model tracking deterministic tool runs."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.incident import Incident
    from src.persistence.models.remediation import RemediationActionModel


class ActionExecutionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution audit record verifying idempotency and target outcome."""

    __tablename__ = "action_executions"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("remediation_actions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_service: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    execution_status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # SUCCESS, FAILED, SKIPPED
    execution_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="executions")
    action: Mapped["RemediationActionModel | None"] = relationship(
        "RemediationActionModel", back_populates="executions"
    )
