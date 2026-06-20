from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QualificationEvaluation(Base):
    __tablename__ = "qualification_evaluations"
    __table_args__ = (
        CheckConstraint(
            "evaluation_status IN ('satisfied', 'not_satisfied', 'needs_material', "
            "'pending_confirm', 'not_applicable')",
            name="qualification_evaluation_status_allowed",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="qualification_evaluation_risk_level_allowed",
        ),
        UniqueConstraint("tenant_id", "project_id", "section_id", "compliance_item_id"),
        Index(
            "idx_qualification_eval_section_status",
            "tenant_id",
            "project_id",
            "section_id",
            "evaluation_status",
        ),
        Index("idx_qualification_eval_material", "tenant_id", "matched_material_id"),
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
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_requirement: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matched_material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_materials.id"), nullable=True
    )
    matched_material_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    matched_rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_materials: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
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
