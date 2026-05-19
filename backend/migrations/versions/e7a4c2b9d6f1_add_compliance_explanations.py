"""add compliance explanations

Revision ID: e7a4c2b9d6f1
Revises: d8f3a1b2c4e5
Create Date: 2026-05-17 16:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

revision: str = "e7a4c2b9d6f1"
down_revision: str | None = "d8f3a1b2c4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "compliance_items",
        sa.Column("explanation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("compliance_items", "explanation_json")
