from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BusinessDraftChapter(Base):
    __tablename__ = "business_draft_chapters"
    __table_args__ = (
        CheckConstraint(
            "chapter_type IN ('qualification_response', 'business_response', 'commitment', "
            "'deviation_table', 'other')",
            name="business_draft_chapter_type_allowed",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected', 'superseded')",
            name="business_draft_chapter_status_allowed",
        ),
        CheckConstraint("version_no >= 1", name="business_draft_chapter_version_positive"),
        Index("idx_business_draft_section", "tenant_id", "project_id", "section_id", "status"),
        Index("idx_business_draft_order", "tenant_id", "section_id", "sort_order"),
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
    chapter_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    outline_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evidence_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    fact_check_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_from_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BusinessDraftEvidenceRef(Base):
    __tablename__ = "business_draft_evidence_refs"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('compliance_item', 'enterprise_material', 'manual')",
            name="business_draft_evidence_source_type_allowed",
        ),
        Index("idx_business_draft_evidence_chapter", "tenant_id", "chapter_id"),
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
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_draft_chapters.id"), nullable=False
    )
    compliance_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_items.id"), nullable=True
    )
    evidence_binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_evidence_bindings.id"), nullable=True
    )
    enterprise_material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_materials.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DraftFactCheck(Base):
    __tablename__ = "draft_fact_checks"
    __table_args__ = (
        CheckConstraint(
            "fact_type IN ('project_name', 'certificate_no', 'person_name', 'amount', "
            "'date', 'number', 'other')",
            name="draft_fact_check_type_allowed",
        ),
        CheckConstraint(
            "check_status IN ('verified', 'warning', 'unverified')",
            name="draft_fact_check_status_allowed",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="draft_fact_check_risk_level_allowed",
        ),
        Index("idx_draft_fact_chapter", "tenant_id", "chapter_id", "check_status"),
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
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_draft_chapters.id"), nullable=False
    )
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    fact_text: Mapped[str] = mapped_column(String(500), nullable=False)
    check_status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
