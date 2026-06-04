"""add mvp1.2 context pack

Revision ID: f2b7c9d1e4a3
Revises: 0f4b8c6d2a91
Create Date: 2026-06-04 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f2b7c9d1e4a3"
down_revision: str | None = "0f4b8c6d2a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "draft_context_packs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("profile_version", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("readiness_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outline_plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("confirmed_by", sa.UUID(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "readiness_status IN ('pass', 'warn', 'block')",
            name=op.f("ck_draft_context_packs_draft_context_pack_readiness_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'superseded')",
            name=op.f("ck_draft_context_packs_draft_context_pack_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name=op.f("fk_draft_context_packs_confirmed_by_users")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_draft_context_packs_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_draft_context_packs_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_draft_context_packs_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_draft_context_packs_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_context_packs")),
    )
    op.create_index(
        "idx_draft_context_pack_profile",
        "draft_context_packs",
        ["tenant_id", "profile_id", "profile_version"],
        unique=False,
    )
    op.create_index(
        "idx_draft_context_pack_section",
        "draft_context_packs",
        ["tenant_id", "project_id", "section_id", "status"],
        unique=False,
    )

    op.create_table(
        "draft_section_context_packs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("context_pack_id", sa.UUID(), nullable=False),
        sa.Column("section_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("generation_mode", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('ready', 'blocked', 'superseded')",
            name=op.f("ck_draft_section_context_packs_draft_section_context_pack_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["context_pack_id"], ["draft_context_packs.id"], name=op.f("fk_draft_section_context_packs_context_pack_id_draft_context_packs")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_draft_section_context_packs_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_draft_section_context_packs_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_draft_section_context_packs_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_draft_section_context_packs_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_section_context_packs")),
    )
    op.create_index(
        "idx_draft_section_context_pack_parent",
        "draft_section_context_packs",
        ["tenant_id", "context_pack_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "idx_draft_section_context_pack_section",
        "draft_section_context_packs",
        ["tenant_id", "project_id", "section_id", "section_type"],
        unique=False,
    )

    op.create_table(
        "draft_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("chapter_id", sa.UUID(), nullable=True),
        sa.Column("section_context_pack_id", sa.UUID(), nullable=True),
        sa.Column("block_type", sa.String(length=64), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("links_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fact_claims_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("missing_fact_placeholders_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_flags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "block_type IN ('heading', 'paragraph', 'table', 'list', 'placeholder')",
            name=op.f("ck_draft_blocks_draft_block_type_allowed"),
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'covered', 'needs_evidence', 'needs_fact', 'approved', 'rejected')",
            name=op.f("ck_draft_blocks_draft_block_review_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["business_draft_chapters.id"], name=op.f("fk_draft_blocks_chapter_id_business_draft_chapters")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_draft_blocks_project_id_projects")),
        sa.ForeignKeyConstraint(["section_context_pack_id"], ["draft_section_context_packs.id"], name=op.f("fk_draft_blocks_section_context_pack_id_draft_section_context_packs")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_draft_blocks_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_draft_blocks_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_blocks")),
    )
    op.create_index(
        "idx_draft_block_chapter",
        "draft_blocks",
        ["tenant_id", "chapter_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "idx_draft_block_section_context",
        "draft_blocks",
        ["tenant_id", "section_context_pack_id"],
        unique=False,
    )

    op.create_table(
        "draft_coverage_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("context_pack_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issues_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pass', 'warn', 'block')",
            name=op.f("ck_draft_coverage_reviews_draft_coverage_review_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["context_pack_id"], ["draft_context_packs.id"], name=op.f("fk_draft_coverage_reviews_context_pack_id_draft_context_packs")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_draft_coverage_reviews_created_by_users")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_draft_coverage_reviews_project_id_projects")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_draft_coverage_reviews_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_draft_coverage_reviews_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_coverage_reviews")),
    )
    op.create_index(
        "idx_draft_coverage_review_context",
        "draft_coverage_reviews",
        ["tenant_id", "context_pack_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_draft_coverage_review_section",
        "draft_coverage_reviews",
        ["tenant_id", "project_id", "section_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_draft_coverage_review_section", table_name="draft_coverage_reviews")
    op.drop_index("idx_draft_coverage_review_context", table_name="draft_coverage_reviews")
    op.drop_table("draft_coverage_reviews")

    op.drop_index("idx_draft_block_section_context", table_name="draft_blocks")
    op.drop_index("idx_draft_block_chapter", table_name="draft_blocks")
    op.drop_table("draft_blocks")

    op.drop_index("idx_draft_section_context_pack_section", table_name="draft_section_context_packs")
    op.drop_index("idx_draft_section_context_pack_parent", table_name="draft_section_context_packs")
    op.drop_table("draft_section_context_packs")

    op.drop_index("idx_draft_context_pack_section", table_name="draft_context_packs")
    op.drop_index("idx_draft_context_pack_profile", table_name="draft_context_packs")
    op.drop_table("draft_context_packs")
