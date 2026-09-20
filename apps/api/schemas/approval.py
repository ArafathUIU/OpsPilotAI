"""Pydantic schemas for Human-in-the-loop (HITL) approval requests and decisions."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    """Payload submitted by a human operator approving, rejecting, or modifying an action."""

    decision: Literal["APPROVED", "REJECTED", "MODIFIED"]
    approver_id: str = Field(description="Unique username or operator email")
    approver_role: Literal["VIEWER", "OPERATOR", "ADMIN"] = "OPERATOR"
    reason: str = Field(description="Human justification for the approval decision")
    modified_parameters: dict[str, Any] | None = Field(
        default=None, description="Updated parameters if decision is MODIFIED"
    )


class ApprovalRequestResponse(BaseModel):
    """Details of an action awaiting human authorization."""

    id: str
    incident_id: str
    action_id: str
    action_type: str
    target_service: str
    risk_level: str
    status: str
    description: str
    rollback_plan: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    responded_at: datetime | None = None
    approver_id: str | None = None
    comment: str | None = None
