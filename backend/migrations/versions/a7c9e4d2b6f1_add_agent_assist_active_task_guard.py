"""add agent assist active task guard

Revision ID: a7c9e4d2b6f1
Revises: 9f6b2a1c4d5e
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "a7c9e4d2b6f1"
down_revision: str | None = "9f6b2a1c4d5e"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "uq_async_tasks_agent_assist_active_section",
        "async_tasks",
        ["tenant_id", "project_id", "section_id"],
        unique=True,
        postgresql_where=sa.text(
            "task_type = 'agent_assist' AND status IN ('pending', 'running', 'retrying')"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_async_tasks_agent_assist_active_section", table_name="async_tasks")
