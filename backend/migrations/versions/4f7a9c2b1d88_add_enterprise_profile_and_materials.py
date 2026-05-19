"""add enterprise profile and materials

Revision ID: 4f7a9c2b1d88
Revises: 9b7c2d1e4a68
Create Date: 2026-05-15 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4f7a9c2b1d88"
down_revision: str | None = "9b7c2d1e4a68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enterprise_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(length=300), nullable=False),
        sa.Column("unified_social_credit_code", sa.String(length=64), nullable=True),
        sa.Column("legal_representative", sa.String(length=100), nullable=True),
        sa.Column("registered_address", sa.String(length=500), nullable=True),
        sa.Column("business_scope", sa.Text(), nullable=True),
        sa.Column("region_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("industry_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("forbidden_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_enterprise_profiles_created_by_users")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_enterprise_profiles_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_enterprise_profiles_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enterprise_profiles")),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_enterprise_profiles_tenant_id")),
    )
    op.create_index(
        "idx_enterprise_profiles_tenant_name",
        "enterprise_profiles",
        ["tenant_id", "company_name"],
        unique=False,
    )

    op.create_table(
        "enterprise_materials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("material_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("issuing_authority", sa.String(length=300), nullable=True),
        sa.Column("certificate_no", sa.String(length=128), nullable=True),
        sa.Column("holder_name", sa.String(length=200), nullable=True),
        sa.Column("project_name", sa.String(length=300), nullable=True),
        sa.Column("amount", sa.String(length=100), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("data_level", sa.String(length=32), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("structured_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=300), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("bucket", sa.String(length=128), nullable=True),
        sa.Column("object_key", sa.String(length=512), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "data_level IN ('public', 'internal', 'restricted', 'confidential')",
            name=op.f("ck_enterprise_materials_enterprise_material_data_level_allowed"),
        ),
        sa.CheckConstraint(
            "file_size IS NULL OR file_size >= 0",
            name=op.f("ck_enterprise_materials_enterprise_material_file_size_non_negative"),
        ),
        sa.CheckConstraint(
            "material_type IN ('license', 'qualification', 'personnel', 'performance', 'business_template', 'commitment', 'other')",
            name=op.f("ck_enterprise_materials_enterprise_material_type_allowed"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('draft', 'pending_confirm', 'confirmed', 'conflict', 'expired', 'missing_evidence')",
            name=op.f("ck_enterprise_materials_enterprise_material_verification_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_enterprise_materials_created_by_users")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_enterprise_materials_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_enterprise_materials_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enterprise_materials")),
    )
    op.create_index(
        "idx_enterprise_materials_name",
        "enterprise_materials",
        ["tenant_id", "name"],
        unique=False,
    )
    op.create_index(
        "idx_enterprise_materials_tenant_type",
        "enterprise_materials",
        ["tenant_id", "material_type", "verification_status"],
        unique=False,
    )
    op.create_index(
        "idx_enterprise_materials_valid_until",
        "enterprise_materials",
        ["tenant_id", "valid_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_enterprise_materials_valid_until", table_name="enterprise_materials")
    op.drop_index("idx_enterprise_materials_tenant_type", table_name="enterprise_materials")
    op.drop_index("idx_enterprise_materials_name", table_name="enterprise_materials")
    op.drop_table("enterprise_materials")
    op.drop_index("idx_enterprise_profiles_tenant_name", table_name="enterprise_profiles")
    op.drop_table("enterprise_profiles")
