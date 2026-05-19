from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ComplianceItem(Base):
    __tablename__ = "compliance_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('qualification', 'mandatory_response', 'format', 'deadline', "
            "'scoring', 'reference_info', 'technical_response', 'other')",
            name="compliance_item_type_allowed",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_confirm', 'confirmed', 'needs_material', "
            "'rejected', 'superseded')",
            name="compliance_item_status_allowed",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="compliance_item_risk_level_allowed",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="compliance_item_confidence_score_range",
        ),
        CheckConstraint(
            "status != 'confirmed' OR source_chunk_id IS NOT NULL",
            name="compliance_confirmed_requires_source_chunk",
        ),
        CheckConstraint(
            "is_batch_confirm_allowed = false OR "
            "(risk_level != 'high' AND is_mandatory = false AND status != 'needs_material')",
            name="compliance_batch_confirm_guard",
        ),
        Index("idx_cm_tenant_project_section", "tenant_id", "project_id", "section_id"),
        Index(
            "idx_cm_filter",
            "tenant_id",
            "project_id",
            "section_id",
            "status",
            "risk_level",
            "owner_user_id",
        ),
        Index(
            "idx_cm_source",
            "tenant_id",
            "source_document_id",
            "source_version_id",
            "source_chunk_id",
        ),
        Index("idx_cm_updated", "tenant_id", "project_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bid_sections.id"), nullable=False
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False
    )
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=True
    )
    source_page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_confirm")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_batch_confirm_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    modified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    modify_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComplianceEvidenceBinding(Base):
    __tablename__ = "compliance_evidence_bindings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'deleted')",
            name="compliance_evidence_binding_status_allowed",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="compliance_evidence_binding_confidence_score_range",
        ),
        Index(
            "idx_cm_evidence_item",
            "tenant_id",
            "project_id",
            "section_id",
            "compliance_item_id",
            "status",
        ),
        Index(
            "idx_cm_evidence_material",
            "tenant_id",
            "enterprise_material_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bid_sections.id"), nullable=False
    )
    compliance_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_items.id"), nullable=False
    )
    enterprise_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_materials.id"), nullable=False
    )
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    material_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    bind_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
