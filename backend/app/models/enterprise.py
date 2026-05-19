from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EnterpriseProfile(Base):
    __tablename__ = "enterprise_profiles"
    __table_args__ = (
        Index("idx_enterprise_profiles_tenant_name", "tenant_id", "company_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True
    )
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)
    unified_social_credit_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_representative: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registered_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    region_preferences: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    industry_preferences: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    forbidden_rules: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EnterpriseMaterial(Base):
    __tablename__ = "enterprise_materials"
    __table_args__ = (
        CheckConstraint(
            "material_type IN ('license', 'qualification', 'personnel', 'performance', "
            "'business_template', 'commitment', 'product_catalog', 'test_report', "
            "'product_image', 'technical_proposal', 'other')",
            name="enterprise_material_type_allowed",
        ),
        CheckConstraint(
            "data_level IN ('public', 'internal', 'restricted', 'confidential')",
            name="enterprise_material_data_level_allowed",
        ),
        CheckConstraint(
            "verification_status IN ('draft', 'pending_confirm', 'confirmed', 'conflict', "
            "'expired', 'missing_evidence')",
            name="enterprise_material_verification_status_allowed",
        ),
        CheckConstraint("file_size IS NULL OR file_size >= 0", name="enterprise_material_file_size_non_negative"),
        Index("idx_enterprise_materials_tenant_type", "tenant_id", "material_type", "verification_status"),
        Index("idx_enterprise_materials_valid_until", "tenant_id", "valid_until"),
        Index("idx_enterprise_materials_name", "tenant_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    material_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(String(300), nullable=True)
    certificate_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    holder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_level: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_confirm")
    structured_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bucket: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
