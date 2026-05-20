from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EnterpriseProfileBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=300)
    unified_social_credit_code: str | None = Field(default=None, max_length=64)
    legal_representative: str | None = Field(default=None, max_length=100)
    registered_address: str | None = Field(default=None, max_length=500)
    business_scope: str | None = None
    region_preferences: list[str] | None = None
    industry_preferences: list[str] | None = None
    forbidden_rules: list[str] | None = None


class EnterpriseProfileUpsertRequest(EnterpriseProfileBase):
    pass


class EnterpriseProfileRead(EnterpriseProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    updated_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EnterpriseMaterialCreateRequest(BaseModel):
    material_type: str = Field(..., max_length=64)
    name: str = Field(..., min_length=1, max_length=300)
    issuing_authority: str | None = Field(default=None, max_length=300)
    certificate_no: str | None = Field(default=None, max_length=128)
    holder_name: str | None = Field(default=None, max_length=200)
    project_name: str | None = Field(default=None, max_length=300)
    amount: str | None = Field(default=None, max_length=100)
    valid_from: date | None = None
    valid_until: date | None = None
    data_level: str = "internal"
    verification_status: str = "pending_confirm"
    structured_fields: dict[str, Any] | None = None
    evidence_text: str | None = None


class EnterpriseMaterialUpdateRequest(BaseModel):
    material_type: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    issuing_authority: str | None = Field(default=None, max_length=300)
    certificate_no: str | None = Field(default=None, max_length=128)
    holder_name: str | None = Field(default=None, max_length=200)
    project_name: str | None = Field(default=None, max_length=300)
    amount: str | None = Field(default=None, max_length=100)
    valid_from: date | None = None
    valid_until: date | None = None
    data_level: str | None = None
    verification_status: str | None = None
    structured_fields: dict[str, Any] | None = None
    evidence_text: str | None = None
    reason: str = Field(..., min_length=1, max_length=500)


class EnterpriseMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    material_type: str
    name: str
    issuing_authority: str | None
    certificate_no: str | None
    holder_name: str | None
    project_name: str | None
    amount: str | None
    valid_from: date | None
    valid_until: date | None
    data_level: str
    verification_status: str
    structured_fields: dict[str, Any] | None
    evidence_text: str | None
    file_name: str | None
    content_type: str | None
    file_size: int | None
    sha256: str | None
    created_by: uuid.UUID
    updated_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EnterpriseMaterialSearchResult(EnterpriseMaterialRead):
    snippet: str | None
    confidence_score: float
    chunk_id: uuid.UUID | None = None
    data_level_allowed: bool = True
    recommend_reason: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    material_status_hint: str | None = None


class EnterpriseMaterialChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    enterprise_material_id: uuid.UUID
    chunk_index: int
    content_text: str
    content_hash: str
    metadata_json: dict[str, Any] | None
    data_level: str
    token_count: int
    created_at: datetime
    updated_at: datetime
