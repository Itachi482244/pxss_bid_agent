from __future__ import annotations

from datetime import UTC, datetime
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_request_context
from app.core.config import settings
from app.db.session import get_db
from app.models import AIModelConfig, AuditLog
from app.schemas.system import (
    ChatModelConfigRead,
    ChatModelConfigTestRequest,
    ChatModelConfigTestResult,
    ChatModelConfigUpdateRequest,
)
from app.services.model_config import env_chat_model_config, get_chat_model_config
from app.services.model_config_crypto import (
    ModelConfigCryptoError,
    decrypt_api_key,
    encrypt_api_key,
)

router = APIRouter()


@router.get("/info")
async def system_info() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
    }


def _read_payload(config: AIModelConfig | None) -> ChatModelConfigRead:
    if config is None:
        env_config = env_chat_model_config()
        return ChatModelConfigRead(
            provider=env_config.provider,
            base_url=env_config.base_url or None,
            simple_model=env_config.simple_model or None,
            complex_model=env_config.complex_model or None,
            timeout_seconds=env_config.timeout_seconds,
            enabled=env_config.provider != "mock" and bool(env_config.api_key),
            api_key_masked="环境变量已配置" if env_config.api_key else None,
            has_api_key=bool(env_config.api_key),
            source=env_config.source,
        )
    return ChatModelConfigRead(
        id=config.id,
        capability=config.capability,
        provider=config.provider,
        base_url=config.base_url,
        simple_model=config.simple_model,
        complex_model=config.complex_model,
        timeout_seconds=float(config.timeout_seconds),
        enabled=config.enabled,
        api_key_masked=config.api_key_masked,
        has_api_key=bool(config.api_key_encrypted),
        source="db",
        last_test_status=config.last_test_status,
        last_test_message=config.last_test_message,
        last_tested_at=config.last_tested_at,
        updated_at=config.updated_at,
    )


def _audit_model_config(
    db: Session,
    ctx: RequestContext,
    *,
    action: str,
    config: AIModelConfig | None,
    before_json: dict[str, object] | None,
    after_json: dict[str, object] | None,
    reason: str,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action=action,
            object_type="ai_model_config",
            object_id=config.id if config else None,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def _safe_config_snapshot(config: AIModelConfig | None) -> dict[str, object] | None:
    if config is None:
        return None
    return {
        "capability": config.capability,
        "provider": config.provider,
        "base_url": config.base_url,
        "simple_model": config.simple_model,
        "complex_model": config.complex_model,
        "timeout_seconds": float(config.timeout_seconds),
        "enabled": config.enabled,
        "api_key_masked": config.api_key_masked,
        "last_test_status": config.last_test_status,
        "last_test_message": config.last_test_message,
    }


@router.get("/model-configs/chat", response_model=ChatModelConfigRead)
def get_chat_model_config_route(
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatModelConfigRead:
    return _read_payload(get_chat_model_config(db, ctx.tenant_id))


@router.put("/model-configs/chat", response_model=ChatModelConfigRead)
def upsert_chat_model_config(
    payload: ChatModelConfigUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatModelConfigRead:
    config = get_chat_model_config(db, ctx.tenant_id)
    before = _safe_config_snapshot(config)
    if config is None:
        config = AIModelConfig(
            tenant_id=ctx.tenant_id,
            capability="chat",
            provider=payload.provider,
            timeout_seconds=payload.timeout_seconds,
            enabled=payload.enabled,
            created_by=ctx.user_id,
            updated_by=ctx.user_id,
        )
        db.add(config)

    config.provider = payload.provider
    config.base_url = payload.base_url.strip() if payload.base_url else None
    config.simple_model = payload.simple_model.strip() if payload.simple_model else None
    config.complex_model = payload.complex_model.strip() if payload.complex_model else None
    config.timeout_seconds = payload.timeout_seconds
    config.enabled = payload.enabled
    config.updated_by = ctx.user_id

    if payload.clear_api_key:
        config.api_key_encrypted = None
        config.api_key_masked = None
        config.encryption_key_version = None
    elif payload.api_key is not None and payload.api_key.strip():
        try:
            encrypted, masked, key_version = encrypt_api_key(payload.api_key)
        except ModelConfigCryptoError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"模型配置加密密钥不可用：{exc}",
            ) from exc
        config.api_key_encrypted = encrypted
        config.api_key_masked = masked
        config.encryption_key_version = key_version

    db.flush()
    after = _safe_config_snapshot(config)
    _audit_model_config(
        db,
        ctx,
        action="model_config.updated",
        config=config,
        before_json=before,
        after_json=after,
        reason="更新 Chat 模型配置",
    )
    db.commit()
    db.refresh(config)
    return _read_payload(config)


def _resolve_test_inputs(
    payload: ChatModelConfigTestRequest,
    config: AIModelConfig | None,
) -> tuple[str, str, str, str, float, str, str]:
    provider = payload.provider or (config.provider if config else settings.llm_provider) or "mock"
    base_url = payload.base_url if payload.base_url is not None else (
        config.base_url if config else settings.llm_base_url
    )
    simple_model = payload.simple_model if payload.simple_model is not None else (
        config.simple_model if config else settings.llm_simple_model or settings.llm_model
    )
    complex_model = payload.complex_model if payload.complex_model is not None else (
        config.complex_model if config else settings.llm_complex_model or settings.llm_model
    )
    timeout = payload.timeout_seconds if payload.timeout_seconds is not None else (
        float(config.timeout_seconds) if config else float(settings.llm_timeout_seconds)
    )
    api_key = payload.api_key.strip() if payload.api_key else ""
    source = "draft"
    if not api_key and config and config.api_key_encrypted:
        source = "db"
        api_key = decrypt_api_key(config.api_key_encrypted)
    if not api_key and settings.llm_api_key:
        source = "env"
        api_key = settings.llm_api_key
    return provider, base_url or "", simple_model or "", complex_model or simple_model or "", timeout, api_key, source


@router.post("/model-configs/chat/test", response_model=ChatModelConfigTestResult)
def test_chat_model_config(
    payload: ChatModelConfigTestRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ChatModelConfigTestResult:
    config = get_chat_model_config(db, ctx.tenant_id)
    started = time.perf_counter()
    severity = "info"
    try:
        provider, base_url, simple_model, _complex_model, timeout, api_key, source = _resolve_test_inputs(payload, config)
        if provider == "mock":
            result = ChatModelConfigTestResult(
                status="success",
                message="mock 模型配置可用，将走本地规则兜底。",
                provider=provider,
                model_name=simple_model or "mock",
                duration_ms=0,
                source=source,
            )
        elif provider not in {"deepseek", "openai_compatible"}:
            raise ValueError("当前仅支持 deepseek、openai_compatible 或 mock")
        elif not base_url or not simple_model or not api_key:
            raise ValueError("测试远程模型需要 base_url、simple_model 和 api_key")
        else:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": simple_model,
                        "messages": [{"role": "user", "content": "请回复 JSON：{\"ok\": true}"}],
                        "temperature": 0,
                        "max_tokens": 64,
                    },
                )
                response.raise_for_status()
            result = ChatModelConfigTestResult(
                status="success",
                message="模型连接测试成功。",
                provider=provider,
                model_name=simple_model,
                duration_ms=int((time.perf_counter() - started) * 1000),
                source=source,
            )
    except Exception as exc:
        severity = "warning"
        result = ChatModelConfigTestResult(
            status="failed",
            message=str(exc)[:1000] or exc.__class__.__name__,
            provider=payload.provider or (config.provider if config else settings.llm_provider) or "mock",
            model_name=payload.simple_model or (config.simple_model if config else settings.llm_simple_model),
            duration_ms=int((time.perf_counter() - started) * 1000),
            source="draft" if payload.model_fields_set else "db" if config else "env",
        )

    if config is not None:
        config.last_test_status = "success" if result.status == "success" else "failed"
        config.last_test_message = result.message
        config.last_tested_at = datetime.now(UTC)
        config.updated_by = ctx.user_id
    _audit_model_config(
        db,
        ctx,
        action="model_config.tested",
        config=config,
        before_json=None,
        after_json=result.model_dump(mode="json"),
        reason="测试 Chat 模型配置",
        severity=severity,
    )
    db.commit()
    return result
