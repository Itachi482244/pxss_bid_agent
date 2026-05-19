"""add compliance evidence bindings

Revision ID: b84c3e5d9a12
Revises: 7c2a5d9e0b31
Create Date: 2026-05-16 14:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b84c3e5d9a12"
down_revision: str | None = "7c2a5d9e0b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_evidence_bindings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("compliance_item_id", sa.UUID(), nullable=False),
        sa.Column("enterprise_material_id", sa.UUID(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("material_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("bind_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name=op.f("ck_compliance_evidence_bindings_compliance_evidence_binding_confidence_score_range"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'deleted')",
            name=op.f("ck_compliance_evidence_bindings_compliance_evidence_binding_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["compliance_item_id"],
            ["compliance_items.id"],
            name=op.f("fk_compliance_evidence_bindings_compliance_item_id_compliance_items"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_compliance_evidence_bindings_created_by_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["users.id"],
            name=op.f("fk_compliance_evidence_bindings_deleted_by_users"),
        ),
        sa.ForeignKeyConstraint(
            ["enterprise_material_id"],
            ["enterprise_materials.id"],
            name=op.f("fk_compliance_evidence_bindings_enterprise_material_id_enterprise_materials"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_compliance_evidence_bindings_project_id_projects"),
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["bid_sections.id"],
            name=op.f("fk_compliance_evidence_bindings_section_id_bid_sections"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_compliance_evidence_bindings_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compliance_evidence_bindings")),
    )
    op.create_index(
        "idx_cm_evidence_item",
        "compliance_evidence_bindings",
        ["tenant_id", "project_id", "section_id", "compliance_item_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_cm_evidence_material",
        "compliance_evidence_bindings",
        ["tenant_id", "enterprise_material_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_cm_evidence_material", table_name="compliance_evidence_bindings")
    op.drop_index("idx_cm_evidence_item", table_name="compliance_evidence_bindings")
    op.drop_table("compliance_evidence_bindings")
