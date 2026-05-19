"""add model invocation logs

Revision ID: d8f3a1b2c4e5
Revises: c52e8f1a6d44
Create Date: 2026-05-17 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d8f3a1b2c4e5"
down_revision: str | None = "c52e8f1a6d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_invocation_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("complexity", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "actor_type IN ('user', 'system', 'worker')",
            name=op.f("ck_model_invocation_logs_model_invocation_actor_type_allowed"),
        ),
        sa.CheckConstraint(
            "complexity IN ('simple', 'complex')",
            name=op.f("ck_model_invocation_logs_model_invocation_complexity_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'skipped')",
            name=op.f("ck_model_invocation_logs_model_invocation_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_model_invocation_logs_actor_user_id_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_model_invocation_logs_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_model_invocation_logs_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_model_invocation_logs_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_invocation_logs")),
    )
    op.create_index(
        "idx_model_invocation_project_time",
        "model_invocation_logs",
        ["tenant_id", "project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_model_invocation_status",
        "model_invocation_logs",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_model_invocation_task",
        "model_invocation_logs",
        ["tenant_id", "task_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_model_invocation_task", table_name="model_invocation_logs")
    op.drop_index("idx_model_invocation_status", table_name="model_invocation_logs")
    op.drop_index("idx_model_invocation_project_time", table_name="model_invocation_logs")
    op.drop_table("model_invocation_logs")
