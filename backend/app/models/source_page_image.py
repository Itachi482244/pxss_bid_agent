from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SourcePageImage(Base):
    __tablename__ = "source_page_images"
    __table_args__ = (
        CheckConstraint("page_no IS NULL OR page_no >= 1", name="source_page_image_page_no_positive"),
        CheckConstraint("render_scale > 0", name="source_page_image_render_scale_positive"),
        CheckConstraint("image_file_size >= 0", name="source_page_image_file_size_non_negative"),
        CheckConstraint("width > 0", name="source_page_image_width_positive"),
        CheckConstraint("height > 0", name="source_page_image_height_positive"),
        CheckConstraint(
            "image_format IN ('jpeg', 'png', 'webp')",
            name="source_page_image_format_allowed",
        ),
        CheckConstraint(
            "status IN ('ready', 'failed')",
            name="source_page_image_status_allowed",
        ),
        UniqueConstraint(
            "tenant_id",
            "source_sha256",
            "page_no",
            "render_scale",
            "image_format",
            "max_width",
            "image_quality",
            name="uq_source_page_images_source_page_variant",
        ),
        Index("idx_source_page_images_source", "tenant_id", "source_kind", "source_id"),
        Index("idx_source_page_images_sha_page", "tenant_id", "source_sha256", "page_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    source_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    image_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    image_content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    image_format: Mapped[str] = mapped_column(String(16), nullable=False)
    image_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    render_scale: Mapped[float] = mapped_column(Float, nullable=False)
    max_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
