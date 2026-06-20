"""add agent single confirm state

Revision ID: b6d4e8f2c9a1
Revises: a7c9e4d2b6f1
Create Date: 2026-06-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b6d4e8f2c9a1"
down_revision: str | None = "a7c9e4d2b6f1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "bid_sections",
        sa.Column(
            "assist_stage",
            sa.String(length=32),
            server_default="not_started",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_bid_sections_bid_section_assist_stage_allowed"),
        "bid_sections",
        "assist_stage IN ('not_started', 'advancing', 'awaiting_confirm', 'confirmed', 'generated')",
    )
    op.create_index(
        "idx_bid_sections_tenant_assist_stage",
        "bid_sections",
        ["tenant_id", "assist_stage"],
        unique=False,
    )

    op.add_column("agent_review_items", sa.Column("tier", sa.String(length=32), nullable=True))
    op.add_column(
        "agent_review_items",
        sa.Column("is_disqualifying", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "agent_review_items",
        sa.Column("conclusion_changed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "agent_review_items",
        sa.Column("auto_applied", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_agent_review_items_agent_review_item_tier_allowed"),
        "agent_review_items",
        "tier IS NULL OR tier IN ('silent', 'pre_accepted', 'blocking')",
    )
    op.create_index(
        "idx_agent_review_tier",
        "agent_review_items",
        ["tenant_id", "project_id", "section_id", "tier", "status"],
        unique=False,
    )

    op.create_table(
        "section_confirmations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confirmed_by", sa.UUID(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("withdrawn_by", sa.UUID(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'withdrawn')",
            name=op.f("ck_section_confirmations_section_confirmation_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name=op.f("fk_section_confirmations_confirmed_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_section_confirmations_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_section_confirmations_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_section_confirmations_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["withdrawn_by"], ["users.id"], name=op.f("fk_section_confirmations_withdrawn_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_section_confirmations")),
    )
    op.create_index(
        "idx_section_confirmations_section_status",
        "section_confirmations",
        ["tenant_id", "project_id", "section_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_section_confirmations_section_status", table_name="section_confirmations")
    op.drop_table("section_confirmations")

    op.drop_index("idx_agent_review_tier", table_name="agent_review_items")
    op.drop_constraint(
        op.f("ck_agent_review_items_agent_review_item_tier_allowed"),
        "agent_review_items",
        type_="check",
    )
    op.drop_column("agent_review_items", "auto_applied")
    op.drop_column("agent_review_items", "conclusion_changed")
    op.drop_column("agent_review_items", "is_disqualifying")
    op.drop_column("agent_review_items", "tier")

    op.drop_index("idx_bid_sections_tenant_assist_stage", table_name="bid_sections")
    op.drop_constraint(
        op.f("ck_bid_sections_bid_section_assist_stage_allowed"),
        "bid_sections",
        type_="check",
    )
    op.drop_column("bid_sections", "assist_stage")
