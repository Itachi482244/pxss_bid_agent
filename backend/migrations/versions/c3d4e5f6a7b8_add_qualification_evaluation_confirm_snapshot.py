"""add qualification evaluation confirm snapshot

Revision ID: c3d4e5f6a7b8
Revises: b6d4e8f2c9a1
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b6d4e8f2c9a1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "qualification_evaluations",
        sa.Column("confirmed_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qualification_evaluations", "confirmed_snapshot_json")
