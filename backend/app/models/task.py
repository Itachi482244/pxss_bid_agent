from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AsyncTask(Base):
    __tablename__ = "async_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
            "'excel_export', 'document_section_plan', 'section_compliance_extract', "
            "'business_draft_generate', 'history_material_extract')",
            name="async_task_type_allowed",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'retrying', 'succeeded', 'failed', 'canceled')",
            name="async_task_status_allowed",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="async_task_progress_range"),
        CheckConstraint("retry_count >= 0", name="async_task_retry_count_non_negative"),
        CheckConstraint("max_retries >= 0", name="async_task_max_retries_non_negative"),
        UniqueConstraint("tenant_id", "task_type", "idempotency_key"),
        Index("idx_async_tasks_type_status", "tenant_id", "task_type", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bid_sections.id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FileAcquisitionTask(Base):
    __tablename__ = "file_acquisition_tasks"
    __table_args__ = (
        CheckConstraint(
            "fetch_method IN ('manual_public_url')",
            name="file_acquisition_fetch_method_allowed",
        ),
        CheckConstraint(
            "validation_status IN ('pending', 'allowed', 'blocked')",
            name="file_acquisition_validation_status_allowed",
        ),
        CheckConstraint(
            "content_length IS NULL OR content_length >= 0",
            name="file_acquisition_content_length_non_negative",
        ),
        Index("idx_file_acq_task", "tenant_id", "task_id"),
        Index("idx_file_acq_project", "tenant_id", "project_id", "section_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("async_tasks.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bid_sections.id"), nullable=True
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_site: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fetch_method: Mapped[str] = mapped_column(String(64), nullable=False, default="manual_public_url")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_length: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    redirect_chain_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    target_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ParseTask(Base):
    __tablename__ = "parse_tasks"
    __table_args__ = (
        CheckConstraint(
            "parser_type IN ('pdf_text', 'word', 'ocr', 'excel')",
            name="parse_task_parser_type_allowed",
        ),
        Index("idx_parse_tasks_document", "tenant_id", "document_id", "document_version_id"),
        Index("idx_parse_tasks_task", "tenant_id", "task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("async_tasks.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False
    )
    parser_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    options_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
