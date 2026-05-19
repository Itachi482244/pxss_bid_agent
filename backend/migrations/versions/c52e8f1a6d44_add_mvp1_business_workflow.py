"""add mvp1 business workflow

Revision ID: c52e8f1a6d44
Revises: b84c3e5d9a12
Create Date: 2026-05-16 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

revision: str = "c52e8f1a6d44"
down_revision: str | None = "b84c3e5d9a12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: object) -> str:
        return f"vector({self.dimensions})"


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION
          WHEN undefined_file THEN
            RAISE NOTICE 'pgvector extension is not available; enterprise_material_chunks.embedding_vector will be skipped by deployment image checks.';
        END
        $$;
        """
    )
    op.drop_constraint(
        op.f("ck_export_files_export_file_type_allowed"),
        "export_files",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_export_files_export_file_type_allowed"),
        "export_files",
        "export_type IN ('compliance_matrix_excel', 'business_draft_word')",
    )

    op.create_table(
        "business_draft_chapters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("chapter_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("outline_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fact_check_status", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("generated_from_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edit_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "chapter_type IN ('qualification_response', 'business_response', 'commitment', 'deviation_table', 'other')",
            name=op.f("ck_business_draft_chapters_business_draft_chapter_type_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected', 'superseded')",
            name=op.f("ck_business_draft_chapters_business_draft_chapter_status_allowed"),
        ),
        sa.CheckConstraint(
            "version_no >= 1",
            name=op.f("ck_business_draft_chapters_business_draft_chapter_version_positive"),
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name=op.f("fk_business_draft_chapters_approved_by_users")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_business_draft_chapters_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_business_draft_chapters_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_business_draft_chapters_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_business_draft_chapters_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_business_draft_chapters_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_draft_chapters")),
    )
    op.create_index(
        "idx_business_draft_order",
        "business_draft_chapters",
        ["tenant_id", "section_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "idx_business_draft_section",
        "business_draft_chapters",
        ["tenant_id", "project_id", "section_id", "status"],
        unique=False,
    )

    op.create_table(
        "business_draft_evidence_refs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("chapter_id", sa.UUID(), nullable=False),
        sa.Column("compliance_item_id", sa.UUID(), nullable=True),
        sa.Column("evidence_binding_id", sa.UUID(), nullable=True),
        sa.Column("enterprise_material_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('compliance_item', 'enterprise_material', 'manual')",
            name=op.f("ck_business_draft_evidence_refs_business_draft_evidence_source_type_allowed"),
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["business_draft_chapters.id"], name=op.f("fk_business_draft_evidence_refs_chapter_id_business_draft_chapters")),
        sa.ForeignKeyConstraint(["compliance_item_id"], ["compliance_items.id"], name=op.f("fk_business_draft_evidence_refs_compliance_item_id_compliance_items")),
        sa.ForeignKeyConstraint(["enterprise_material_id"], ["enterprise_materials.id"], name=op.f("fk_business_draft_evidence_refs_enterprise_material_id_enterprise_materials")),
        sa.ForeignKeyConstraint(["evidence_binding_id"], ["compliance_evidence_bindings.id"], name=op.f("fk_business_draft_evidence_refs_evidence_binding_id_compliance_evidence_bindings")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_business_draft_evidence_refs_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_business_draft_evidence_refs_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_business_draft_evidence_refs_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_draft_evidence_refs")),
    )
    op.create_index(
        "idx_business_draft_evidence_chapter",
        "business_draft_evidence_refs",
        ["tenant_id", "chapter_id"],
        unique=False,
    )

    op.create_table(
        "draft_fact_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("chapter_id", sa.UUID(), nullable=False),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("fact_text", sa.String(length=500), nullable=False),
        sa.Column("check_status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "check_status IN ('verified', 'warning', 'unverified')",
            name=op.f("ck_draft_fact_checks_draft_fact_check_status_allowed"),
        ),
        sa.CheckConstraint(
            "fact_type IN ('project_name', 'certificate_no', 'person_name', 'amount', 'date', 'number', 'other')",
            name=op.f("ck_draft_fact_checks_draft_fact_check_type_allowed"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name=op.f("ck_draft_fact_checks_draft_fact_check_risk_level_allowed"),
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["business_draft_chapters.id"], name=op.f("fk_draft_fact_checks_chapter_id_business_draft_chapters")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_draft_fact_checks_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_draft_fact_checks_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_draft_fact_checks_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_draft_fact_checks_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_fact_checks")),
    )
    op.create_index(
        "idx_draft_fact_chapter",
        "draft_fact_checks",
        ["tenant_id", "chapter_id", "check_status"],
        unique=False,
    )

    op.create_table(
        "qualification_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("satisfied_count", sa.Integer(), nullable=False),
        sa.Column("blocking_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("pending_count", sa.Integer(), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("confirmed_by", sa.UUID(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirm_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "recommendation IN ('go', 'conditional_go', 'no_go')",
            name=op.f("ck_qualification_decisions_qualification_decision_recommendation_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'superseded')",
            name=op.f("ck_qualification_decisions_qualification_decision_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name=op.f("fk_qualification_decisions_confirmed_by_users")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_qualification_decisions_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_qualification_decisions_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_qualification_decisions_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_qualification_decisions_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qualification_decisions")),
    )
    op.create_index(
        "idx_qualification_decision_section",
        "qualification_decisions",
        ["tenant_id", "project_id", "section_id", "status"],
        unique=False,
    )

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("related_object_type", sa.String(length=100), nullable=True),
        sa.Column("related_object_id", sa.UUID(), nullable=True),
        sa.Column("assignee_user_id", sa.UUID(), nullable=True),
        sa.Column("evidence_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'transferred', 'canceled')",
            name=op.f("ck_approval_tasks_approval_task_status_allowed"),
        ),
        sa.CheckConstraint(
            "task_type IN ('qualification_decision', 'draft_chapter', 'submit_confirmation')",
            name=op.f("ck_approval_tasks_approval_task_type_allowed"),
        ),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], name=op.f("fk_approval_tasks_assignee_user_id_users")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_approval_tasks_created_by_users")),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], name=op.f("fk_approval_tasks_decided_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_approval_tasks_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_approval_tasks_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_approval_tasks_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_tasks")),
    )
    op.create_index(
        "idx_approval_tasks_assignee",
        "approval_tasks",
        ["tenant_id", "assignee_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_approval_tasks_section",
        "approval_tasks",
        ["tenant_id", "project_id", "section_id", "status"],
        unique=False,
    )

    op.create_table(
        "enterprise_material_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("enterprise_material_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_vector", Vector(16), nullable=True),
        sa.Column("embedding_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_level", sa.String(length=32), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name=op.f("ck_enterprise_material_chunks_enterprise_material_chunk_index_non_negative"),
        ),
        sa.CheckConstraint(
            "token_count >= 0",
            name=op.f("ck_enterprise_material_chunks_enterprise_material_chunk_token_count_non_negative"),
        ),
        sa.ForeignKeyConstraint(["enterprise_material_id"], ["enterprise_materials.id"], name=op.f("fk_enterprise_material_chunks_enterprise_material_id_enterprise_materials")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_enterprise_material_chunks_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enterprise_material_chunks")),
    )
    op.create_index(
        "idx_enterprise_material_chunks_level",
        "enterprise_material_chunks",
        ["tenant_id", "data_level"],
        unique=False,
    )
    op.create_index(
        "idx_enterprise_material_chunks_material",
        "enterprise_material_chunks",
        ["tenant_id", "enterprise_material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_enterprise_material_chunks_material", table_name="enterprise_material_chunks")
    op.drop_index("idx_enterprise_material_chunks_level", table_name="enterprise_material_chunks")
    op.drop_table("enterprise_material_chunks")
    op.drop_index("idx_approval_tasks_section", table_name="approval_tasks")
    op.drop_index("idx_approval_tasks_assignee", table_name="approval_tasks")
    op.drop_table("approval_tasks")
    op.drop_index("idx_qualification_decision_section", table_name="qualification_decisions")
    op.drop_table("qualification_decisions")
    op.drop_index("idx_draft_fact_chapter", table_name="draft_fact_checks")
    op.drop_table("draft_fact_checks")
    op.drop_index("idx_business_draft_evidence_chapter", table_name="business_draft_evidence_refs")
    op.drop_table("business_draft_evidence_refs")
    op.drop_index("idx_business_draft_section", table_name="business_draft_chapters")
    op.drop_index("idx_business_draft_order", table_name="business_draft_chapters")
    op.drop_table("business_draft_chapters")
    op.drop_constraint(
        op.f("ck_export_files_export_file_type_allowed"),
        "export_files",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_export_files_export_file_type_allowed"),
        "export_files",
        "export_type IN ('compliance_matrix_excel')",
    )
