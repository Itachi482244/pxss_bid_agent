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


class DraftContextPack(Base):
    __tablename__ = "draft_context_packs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'superseded')",
            name="draft_context_pack_status_allowed",
        ),
        CheckConstraint(
            "readiness_status IN ('pass', 'warn', 'block')",
            name="draft_context_pack_readiness_allowed",
        ),
        Index("idx_draft_context_pack_section", "tenant_id", "project_id", "section_id", "status"),
        Index("idx_draft_context_pack_profile", "tenant_id", "profile_id", "profile_version"),
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
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    readiness_status: Mapped[str] = mapped_column(String(32), nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    readiness_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    outline_plan_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DraftSectionContextPack(Base):
    __tablename__ = "draft_section_context_packs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ready', 'blocked', 'superseded')",
            name="draft_section_context_pack_status_allowed",
        ),
        Index("idx_draft_section_context_pack_parent", "tenant_id", "context_pack_id", "sort_order"),
        Index(
            "idx_draft_section_context_pack_section",
            "tenant_id",
            "project_id",
            "section_id",
            "section_type",
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
    context_pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_context_packs.id"), nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DraftBlock(Base):
    __tablename__ = "draft_blocks"
    __table_args__ = (
        CheckConstraint(
            "block_type IN ('heading', 'paragraph', 'table', 'list', 'placeholder')",
            name="draft_block_type_allowed",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'covered', 'needs_evidence', 'needs_fact', 'approved', 'rejected')",
            name="draft_block_review_status_allowed",
        ),
        Index("idx_draft_block_chapter", "tenant_id", "chapter_id", "sort_order"),
        Index("idx_draft_block_section_context", "tenant_id", "section_context_pack_id"),
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
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_draft_chapters.id"), nullable=True
    )
    section_context_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_section_context_packs.id"), nullable=True
    )
    block_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    links_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    fact_claims_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    missing_fact_placeholders_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    risk_flags_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DraftCoverageReview(Base):
    __tablename__ = "draft_coverage_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pass', 'warn', 'block')",
            name="draft_coverage_review_status_allowed",
        ),
        Index("idx_draft_coverage_review_context", "tenant_id", "context_pack_id", "created_at"),
        Index("idx_draft_coverage_review_section", "tenant_id", "project_id", "section_id"),
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
    context_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_context_packs.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    issues_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
