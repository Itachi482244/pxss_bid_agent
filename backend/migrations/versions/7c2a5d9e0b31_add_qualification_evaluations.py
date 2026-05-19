"""add qualification evaluations

Revision ID: 7c2a5d9e0b31
Revises: 4f7a9c2b1d88
Create Date: 2026-05-16 09:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7c2a5d9e0b31"
down_revision: str | None = "4f7a9c2b1d88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qualification_evaluations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("compliance_item_id", sa.UUID(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("requirement_type", sa.String(length=64), nullable=False),
        sa.Column("extracted_requirement", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evaluation_status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), nullable=False),
        sa.Column("matched_material_id", sa.UUID(), nullable=True),
        sa.Column("matched_material_name", sa.String(length=300), nullable=True),
        sa.Column("matched_rule_code", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("missing_materials", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confirmed_by", sa.UUID(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirm_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "evaluation_status IN ('satisfied', 'not_satisfied', 'needs_material', 'pending_confirm', 'not_applicable')",
            name=op.f("ck_qualification_evaluations_qualification_evaluation_status_allowed"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name=op.f("ck_qualification_evaluations_qualification_evaluation_risk_level_allowed"),
        ),
        sa.ForeignKeyConstraint(["compliance_item_id"], ["compliance_items.id"], name=op.f("fk_qualification_evaluations_compliance_item_id_compliance_items")),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name=op.f("fk_qualification_evaluations_confirmed_by_users")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_qualification_evaluations_created_by_users")),
        sa.ForeignKeyConstraint(["matched_material_id"], ["enterprise_materials.id"], name=op.f("fk_qualification_evaluations_matched_material_id_enterprise_materials")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_qualification_evaluations_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_qualification_evaluations_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_qualification_evaluations_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_qualification_evaluations_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qualification_evaluations")),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "section_id",
            "compliance_item_id",
            name=op.f("uq_qualification_evaluations_tenant_id"),
        ),
    )
    op.create_index(
        "idx_qualification_eval_material",
        "qualification_evaluations",
        ["tenant_id", "matched_material_id"],
        unique=False,
    )
    op.create_index(
        "idx_qualification_eval_section_status",
        "qualification_evaluations",
        ["tenant_id", "project_id", "section_id", "evaluation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_qualification_eval_section_status", table_name="qualification_evaluations")
    op.drop_index("idx_qualification_eval_material", table_name="qualification_evaluations")
    op.drop_table("qualification_evaluations")
