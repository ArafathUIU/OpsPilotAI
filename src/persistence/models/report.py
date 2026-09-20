"""Incident report / postmortem ORM model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.persistence.models.incident import Incident


class IncidentReportModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured postmortem report produced after incident resolution."""

    __tablename__ = "incident_reports"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    timeline: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    lessons_learned: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prevention_items: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="report")
