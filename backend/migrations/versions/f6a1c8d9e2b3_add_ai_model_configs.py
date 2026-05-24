"""add ai model configs

Revision ID: f6a1c8d9e2b3
Revises: 3a6b8e2d4c91
Create Date: 2026-05-23 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f6a1c8d9e2b3"
down_revision: str | None = "3a6b8e2d4c91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_model_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("simple_model", sa.String(length=128), nullable=True),
        sa.Column("complex_model", sa.String(length=128), nullable=True),
        sa.Column("timeout_seconds", sa.Numeric(8, 2), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_key_masked", sa.String(length=128), nullable=True),
        sa.Column("encryption_key_version", sa.String(length=32), nullable=True),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_message", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "capability IN ('chat', 'embedding', 'rerank')",
            name=op.f("ck_ai_model_configs_ai_model_config_capability_allowed"),
        ),
        sa.CheckConstraint(
            "provider IN ('mock', 'deepseek', 'openai_compatible')",
            name=op.f("ck_ai_model_configs_ai_model_config_provider_allowed"),
        ),
        sa.CheckConstraint(
            "last_test_status IS NULL OR last_test_status IN ('success', 'failed', 'skipped')",
            name=op.f("ck_ai_model_configs_ai_model_config_last_test_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_ai_model_configs_created_by_users")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_ai_model_configs_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_ai_model_configs_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_model_configs")),
        sa.UniqueConstraint("tenant_id", "capability", name="uq_ai_model_configs_tenant_capability"),
    )
    op.create_index(
        "idx_ai_model_configs_tenant_enabled",
        "ai_model_configs",
        ["tenant_id", "capability", "enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_ai_model_configs_tenant_enabled", table_name="ai_model_configs")
    op.drop_table("ai_model_configs")
