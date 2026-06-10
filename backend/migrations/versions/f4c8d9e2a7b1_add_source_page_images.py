"""add source page images

Revision ID: f4c8d9e2a7b1
Revises: e3b9a1c7d2f4
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4c8d9e2a7b1"
down_revision: str | None = "e3b9a1c7d2f4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "source_page_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_bucket", sa.String(length=128), nullable=False),
        sa.Column("source_object_key", sa.String(length=512), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_file_name", sa.String(length=300), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("image_bucket", sa.String(length=128), nullable=False),
        sa.Column("image_object_key", sa.String(length=512), nullable=False),
        sa.Column("image_content_type", sa.String(length=128), nullable=False),
        sa.Column("image_format", sa.String(length=16), nullable=False),
        sa.Column("image_quality", sa.Integer(), nullable=True),
        sa.Column("image_file_size", sa.BigInteger(), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("render_scale", sa.Float(), nullable=False),
        sa.Column("max_width", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("height > 0", name=op.f("ck_source_page_images_source_page_image_height_positive")),
        sa.CheckConstraint(
            "image_file_size >= 0",
            name=op.f("ck_source_page_images_source_page_image_file_size_non_negative"),
        ),
        sa.CheckConstraint(
            "image_format IN ('jpeg', 'png', 'webp')",
            name=op.f("ck_source_page_images_source_page_image_format_allowed"),
        ),
        sa.CheckConstraint(
            "page_no IS NULL OR page_no >= 1",
            name=op.f("ck_source_page_images_source_page_image_page_no_positive"),
        ),
        sa.CheckConstraint(
            "render_scale > 0",
            name=op.f("ck_source_page_images_source_page_image_render_scale_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'failed')",
            name=op.f("ck_source_page_images_source_page_image_status_allowed"),
        ),
        sa.CheckConstraint("width > 0", name=op.f("ck_source_page_images_source_page_image_width_positive")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_source_page_images_tenant_id_tenants")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_page_images")),
        sa.UniqueConstraint(
            "tenant_id",
            "source_sha256",
            "page_no",
            "render_scale",
            "image_format",
            "max_width",
            "image_quality",
            name=op.f("uq_source_page_images_source_page_variant"),
        ),
    )
    op.create_index(
        "idx_source_page_images_sha_page",
        "source_page_images",
        ["tenant_id", "source_sha256", "page_no"],
        unique=False,
    )
    op.create_index(
        "idx_source_page_images_source",
        "source_page_images",
        ["tenant_id", "source_kind", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_source_page_images_source", table_name="source_page_images")
    op.drop_index("idx_source_page_images_sha_page", table_name="source_page_images")
    op.drop_table("source_page_images")
