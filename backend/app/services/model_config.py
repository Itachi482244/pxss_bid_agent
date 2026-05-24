from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIModelConfig
from app.services.model_config_crypto import ModelConfigCryptoError, decrypt_api_key


@dataclass(frozen=True)
class RuntimeChatModelConfig:
    provider: str
    base_url: str
    api_key: str
    simple_model: str
    complex_model: str
    timeout_seconds: float
    source: str

    def model_for_complexity(self, complexity: str) -> str:
        if complexity == "complex":
            return self.complex_model or self.simple_model
        return self.simple_model or self.complex_model


def get_chat_model_config(db: Session, tenant_id: uuid.UUID) -> AIModelConfig | None:
    return db.scalar(
        select(AIModelConfig).where(
            AIModelConfig.tenant_id == tenant_id,
            AIModelConfig.capability == "chat",
        )
    )


def env_chat_model_config() -> RuntimeChatModelConfig:
    provider = settings.llm_provider or "mock"
    simple_model = settings.llm_simple_model or settings.llm_model
    complex_model = settings.llm_complex_model or settings.llm_model or simple_model
    return RuntimeChatModelConfig(
        provider=provider,
        base_url=settings.llm_base_url or "",
        api_key=settings.llm_api_key or "",
        simple_model=simple_model,
        complex_model=complex_model,
        timeout_seconds=float(settings.llm_timeout_seconds),
        source="env" if provider != "mock" or settings.llm_api_key else "mock",
    )


def resolve_chat_model_config(db: Session, tenant_id: uuid.UUID) -> RuntimeChatModelConfig:
    config = get_chat_model_config(db, tenant_id)
    if config is not None and config.enabled:
        try:
            api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
            runtime = RuntimeChatModelConfig(
                provider=config.provider,
                base_url=config.base_url or "",
                api_key=api_key,
                simple_model=config.simple_model or "",
                complex_model=config.complex_model or config.simple_model or "",
                timeout_seconds=float(config.timeout_seconds or Decimal("30.0")),
                source="db",
            )
            if runtime.provider == "mock" or (
                runtime.base_url and runtime.model_for_complexity("simple") and runtime.api_key
            ):
                return runtime
        except ModelConfigCryptoError:
            pass
    return env_chat_model_config()
