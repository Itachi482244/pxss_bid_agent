"""add ai sectioned extraction models

Revision ID: 0f4b8c6d2a91
Revises: a9d4e7f2c8b1
Create Date: 2026-05-29 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0f4b8c6d2a91"
down_revision: str | None = "a9d4e7f2c8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
        "'excel_export', 'document_section_plan', 'section_compliance_extract')",
    )

    op.create_table(
        "document_semantic_sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("section_type", sa.String(length=64), nullable=False),
        sa.Column("start_page", sa.Integer(), nullable=False),
        sa.Column("end_page", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_invocation_log_id", sa.UUID(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "section_type IN ('announcement', 'bidder_instructions', 'evaluation', "
            "'contract', 'technical', 'bill', 'forms', 'other')",
            name=op.f("ck_document_semantic_sections_document_semantic_section_type_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'verified', 'low_confidence', 'invalid')",
            name=op.f("ck_document_semantic_sections_document_semantic_section_status_allowed"),
        ),
        sa.CheckConstraint(
            "start_page >= 1",
            name=op.f("ck_document_semantic_sections_document_semantic_section_start_page_positive"),
        ),
        sa.CheckConstraint(
            "end_page >= start_page",
            name=op.f("ck_document_semantic_sections_document_semantic_section_page_range_valid"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name=op.f("ck_document_semantic_sections_document_semantic_section_confidence_range"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_semantic_sections_document_id_documents")),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name=op.f("fk_document_semantic_sections_document_version_id_document_versions")),
        sa.ForeignKeyConstraint(["model_invocation_log_id"], ["model_invocation_logs.id"], name=op.f("fk_document_semantic_sections_model_invocation_log_id_model_invocation_logs")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_document_semantic_sections_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_document_semantic_sections_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_semantic_sections")),
        sa.UniqueConstraint(
            "tenant_id",
            "document_version_id",
            "section_index",
            name=op.f("uq_document_semantic_sections_tenant_id"),
        ),
    )
    op.create_index(
        "idx_document_semantic_sections_version",
        "document_semantic_sections",
        ["tenant_id", "document_version_id", "section_index"],
        unique=False,
    )

    op.create_table(
        "document_extraction_quality_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("issues_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('passed', 'blocked')",
            name=op.f("ck_document_extraction_quality_reports_document_extraction_quality_report_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_extraction_quality_reports_document_id_documents")),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name=op.f("fk_document_extraction_quality_reports_document_version_id_document_versions")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_document_extraction_quality_reports_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["task_id"], ["async_tasks.id"], name=op.f("fk_document_extraction_quality_reports_task_id_async_tasks")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_document_extraction_quality_reports_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_extraction_quality_reports")),
    )
    op.create_index(
        "idx_document_extraction_quality_reports_task",
        "document_extraction_quality_reports",
        ["tenant_id", "task_id"],
        unique=False,
    )
    op.create_index(
        "idx_document_extraction_quality_reports_version",
        "document_extraction_quality_reports",
        ["tenant_id", "document_version_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_document_extraction_quality_reports_version", table_name="document_extraction_quality_reports")
    op.drop_index("idx_document_extraction_quality_reports_task", table_name="document_extraction_quality_reports")
    op.drop_table("document_extraction_quality_reports")
    op.drop_index("idx_document_semantic_sections_version", table_name="document_semantic_sections")
    op.drop_table("document_semantic_sections")

    op.drop_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', 'excel_export')",
    )
