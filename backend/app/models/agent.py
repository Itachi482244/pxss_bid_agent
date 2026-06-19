from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AgentReviewItem(Base):
    __tablename__ = "agent_review_items"
    __table_args__ = (
        CheckConstraint(
            "step IN ('matrix_review', 'evidence_binding', 'qualification_technical')",
            name="agent_review_item_step_allowed",
        ),
        CheckConstraint(
            "status IN ('open', 'accepted', 'dismissed', 'superseded', 'auto_passed')",
            name="agent_review_item_status_allowed",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="agent_review_item_severity_allowed",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="agent_review_item_confidence_score_range",
        ),
        Index(
            "idx_agent_review_section_status",
            "tenant_id",
            "project_id",
            "section_id",
            "status",
            "step",
            "created_at",
        ),
        Index("idx_agent_review_task", "tenant_id", "async_task_id"),
        Index("idx_agent_review_object", "tenant_id", "object_type", "object_id", "status"),
        Index("idx_agent_review_compliance", "tenant_id", "compliance_item_id", "status"),
        Index("idx_agent_review_material", "tenant_id", "enterprise_material_id", "status"),
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
    async_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("async_tasks.id"), nullable=True
    )
    run_key: Mapped[str] = mapped_column(String(128), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    compliance_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_items.id"), nullable=True
    )
    enterprise_material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_materials.id"), nullable=True
    )
    qualification_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("qualification_evaluations.id"), nullable=True
    )
    qualification_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("qualification_decisions.id"), nullable=True
    )
    draft_block_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_blocks.id"), nullable=True
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    escalation_reasons: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    recommendation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_ref_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
