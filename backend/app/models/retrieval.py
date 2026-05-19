from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.session import Base


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: object) -> str:
        return f"vector({self.dimensions})"


class EnterpriseMaterialChunk(Base):
    __tablename__ = "enterprise_material_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="enterprise_material_chunk_index_non_negative"),
        CheckConstraint("token_count >= 0", name="enterprise_material_chunk_token_count_non_negative"),
        Index("idx_enterprise_material_chunks_material", "tenant_id", "enterprise_material_id"),
        Index("idx_enterprise_material_chunks_level", "tenant_id", "data_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    enterprise_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_materials.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    embedding_vector: Mapped[str | None] = mapped_column(Vector(16), nullable=True)
    embedding_json: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    data_level: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
