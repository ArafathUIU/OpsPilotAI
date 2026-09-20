"""Initial schema for OpsPilot AI.

Revision ID: 199e8e93c639
Revises:
Create Date: 2026-09-20 14:07:29.945344
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "199e8e93c639"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial core database tables."""
    # 1. Users
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), default="VIEWER", nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. Incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(10), default="SEV2", nullable=False),
        sa.Column("current_stage", sa.String(50), default="CREATED", nullable=False),
        sa.Column("affected_services", sa.JSON(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), default=0.0, nullable=False),
        sa.Column("total_tokens", sa.Integer(), default=0, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. Incident Events
    op.create_table(
        "incident_events",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. Evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("evidence_code", sa.String(50), nullable=False, index=True),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("raw_reference", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), default=1.0, nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Hypotheses
    op.create_table(
        "hypotheses",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("suggested_validation", sa.JSON(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. Remediation Actions
    op.create_table(
        "remediation_actions",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("target_service", sa.String(100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("expected_effect", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(20), default="MEDIUM", nullable=False),
        sa.Column("reversibility", sa.Boolean(), default=True, nullable=False),
        sa.Column("rollback_strategy", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. Approval Requests
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "action_id",
            sa.CHAR(36),
            sa.ForeignKey("remediation_actions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), default="PENDING", nullable=False),
        sa.Column("approver_user_id", sa.String(100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. Action Executions
    op.create_table(
        "action_executions",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "action_id",
            sa.CHAR(36),
            sa.ForeignKey("remediation_actions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("target_service", sa.String(100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("execution_status", sa.String(30), nullable=False),
        sa.Column("execution_output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Verification Results
    op.create_table(
        "verification_results",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("metric_observations", sa.JSON(), nullable=False),
        sa.Column("log_observations", sa.JSON(), nullable=False),
        sa.Column("recovery_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. Incident Reports
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column(
            "incident_id",
            sa.CHAR(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("confirmed_root_cause", sa.Text(), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("lessons_learned", sa.JSON(), nullable=False),
        sa.Column("prevention_items", sa.JSON(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("incident_reports")
    op.drop_table("verification_results")
    op.drop_table("action_executions")
    op.drop_table("approval_requests")
    op.drop_table("remediation_actions")
    op.drop_table("hypotheses")
    op.drop_table("evidence")
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.drop_table("users")
