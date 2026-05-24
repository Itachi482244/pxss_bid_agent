from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatModelConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    capability: str = "chat"
    provider: str
    base_url: str | None = None
    simple_model: str | None = None
    complex_model: str | None = None
    timeout_seconds: float
    enabled: bool
    api_key_masked: str | None = None
    has_api_key: bool = False
    source: str
    last_test_status: str | None = None
    last_test_message: str | None = None
    last_tested_at: datetime | None = None
    updated_at: datetime | None = None


class ChatModelConfigUpdateRequest(BaseModel):
    provider: str = Field(default="mock", max_length=64)
    base_url: str | None = Field(default=None, max_length=2000)
    simple_model: str | None = Field(default=None, max_length=128)
    complex_model: str | None = Field(default=None, max_length=128)
    timeout_seconds: float = Field(default=30.0, ge=1, le=300)
    enabled: bool = True
    api_key: str | None = Field(default=None, max_length=4000)
    clear_api_key: bool = False

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in {"mock", "deepseek", "openai_compatible"}:
            raise ValueError("provider must be mock, deepseek, or openai_compatible")
        return value


class ChatModelConfigTestRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=64)
    base_url: str | None = Field(default=None, max_length=2000)
    simple_model: str | None = Field(default=None, max_length=128)
    complex_model: str | None = Field(default=None, max_length=128)
    timeout_seconds: float | None = Field(default=None, ge=1, le=300)
    enabled: bool | None = None
    api_key: str | None = Field(default=None, max_length=4000)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str | None) -> str | None:
        if value is not None and value not in {"mock", "deepseek", "openai_compatible"}:
            raise ValueError("provider must be mock, deepseek, or openai_compatible")
        return value


class ChatModelConfigTestResult(BaseModel):
    status: str
    message: str
    provider: str
    model_name: str | None = None
    duration_ms: int | None = None
    source: str
