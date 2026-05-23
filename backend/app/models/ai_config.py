from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AIModelConfig(Base):
    __tablename__ = "ai_model_configs"
    __table_args__ = (
        CheckConstraint(
            "capability IN ('chat', 'embedding', 'rerank')",
            name="ai_model_config_capability_allowed",
        ),
        CheckConstraint(
            "provider IN ('mock', 'deepseek', 'openai_compatible')",
            name="ai_model_config_provider_allowed",
        ),
        CheckConstraint(
            "last_test_status IS NULL OR last_test_status IN ('success', 'failed', 'skipped')",
            name="ai_model_config_last_test_status_allowed",
        ),
        UniqueConstraint("tenant_id", "capability", name="uq_ai_model_configs_tenant_capability"),
        Index("idx_ai_model_configs_tenant_enabled", "tenant_id", "capability", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    capability: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    simple_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    complex_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timeout_seconds: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=30.0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_masked: Mapped[str | None] = mapped_column(String(128), nullable=True)
    encryption_key_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
