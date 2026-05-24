"""add compliance review p1 fields

Revision ID: a9d4e7f2c8b1
Revises: f6a1c8d9e2b3
Create Date: 2026-05-24 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a9d4e7f2c8b1"
down_revision: str | None = "f6a1c8d9e2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("compliance_items", sa.Column("dedup_key", sa.String(length=160), nullable=True))
    op.add_column("compliance_items", sa.Column("duplicate_group_id", sa.UUID(), nullable=True))
    op.add_column("compliance_items", sa.Column("duplicate_group_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("compliance_items", sa.Column("duplicate_group_confirmed_by", sa.UUID(), nullable=True))
    op.add_column("compliance_items", sa.Column("duplicate_group_status", sa.String(length=32), nullable=True))
    op.add_column("compliance_items", sa.Column("selected_text", sa.Text(), nullable=True))
    op.add_column("compliance_items", sa.Column("selection_start_offset", sa.Integer(), nullable=True))
    op.add_column("compliance_items", sa.Column("selection_end_offset", sa.Integer(), nullable=True))
    op.add_column("compliance_items", sa.Column("source_create_method", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        op.f("fk_compliance_items_duplicate_group_confirmed_by_users"),
        "compliance_items",
        "users",
        ["duplicate_group_confirmed_by"],
        ["id"],
    )
    op.create_index(
        "idx_cm_dedup",
        "compliance_items",
        ["tenant_id", "project_id", "section_id", "dedup_key"],
        unique=False,
    )
    op.create_index(
        "idx_cm_duplicate_group",
        "compliance_items",
        ["tenant_id", "project_id", "section_id", "duplicate_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_cm_duplicate_group", table_name="compliance_items")
    op.drop_index("idx_cm_dedup", table_name="compliance_items")
    op.drop_constraint(
        op.f("fk_compliance_items_duplicate_group_confirmed_by_users"),
        "compliance_items",
        type_="foreignkey",
    )
    op.drop_column("compliance_items", "source_create_method")
    op.drop_column("compliance_items", "selection_end_offset")
    op.drop_column("compliance_items", "selection_start_offset")
    op.drop_column("compliance_items", "selected_text")
    op.drop_column("compliance_items", "duplicate_group_status")
    op.drop_column("compliance_items", "duplicate_group_confirmed_by")
    op.drop_column("compliance_items", "duplicate_group_confirmed_at")
    op.drop_column("compliance_items", "duplicate_group_id")
    op.drop_column("compliance_items", "dedup_key")
