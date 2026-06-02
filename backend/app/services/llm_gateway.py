from __future__ import annotations

import hashlib
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuditLog, ModelInvocationLog
from app.services.model_config import RuntimeChatModelConfig, resolve_chat_model_config

Complexity = Literal["simple", "complex"]
ComplexityInput = Literal["simple", "complex", "auto"]


class LLMGatewayError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "LLM_CALL_FAILED",
        log_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.log_id = log_id


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model_name: str
    complexity: Complexity
    prompt_version: str
    log_id: uuid.UUID
    usage: dict[str, int | None]


def _message_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{message.get('role', '')}: {message.get('content', '')}" for message in messages)


def _summary(text: str, *, max_chars: int = 1000) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 2)


def choose_complexity(
    *,
    task_type: str,
    messages: list[dict[str, str]],
    complexity: ComplexityInput = "auto",
) -> Complexity:
    if complexity in {"simple", "complex"}:
        return complexity

    prompt_text = _message_text(messages)
    estimated_tokens = _estimate_tokens(prompt_text)
    if estimated_tokens >= 3000:
        return "complex"
    if task_type in {"business_draft_generation", "compliance_matrix_generation"} and estimated_tokens >= 1800:
        return "complex"
    return "simple"


def choose_model(complexity: Complexity, config: RuntimeChatModelConfig | None = None) -> str:
    if config is not None:
        return config.model_for_complexity(complexity)
    if complexity == "complex":
        return settings.llm_complex_model or settings.llm_model
    return settings.llm_simple_model or settings.llm_model


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)
    if not message:
        return exc.__class__.__name__
    return message[:1000]


def _audit_invocation(
    db: Session,
    log: ModelInvocationLog,
    *,
    action: str,
    severity: str,
    reason: str,
) -> None:
    db.add(
        AuditLog(
            tenant_id=log.tenant_id,
            project_id=log.project_id,
            section_id=log.section_id,
            actor_user_id=log.actor_user_id,
            actor_type=log.actor_type,
            action=action,
            object_type="model_invocation",
            object_id=log.id,
            before_json=None,
            after_json={
                "task_type": log.task_type,
                "provider": log.provider,
                "model_name": log.model_name,
                "complexity": log.complexity,
                "prompt_version": log.prompt_version,
                "status": log.status,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "total_tokens": log.total_tokens,
                "duration_ms": log.duration_ms,
                "error_code": log.error_code,
            },
            reason=reason,
            severity=severity,
        )
    )


def _usage_value(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return None


def _post_chat_completion_with_wall_timeout(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    result_queue: queue.Queue[tuple[str, dict[str, Any] | Exception]] = queue.Queue(maxsize=1)

    def run_request() -> None:
        try:
            timeout = httpx.Timeout(
                timeout_seconds,
                connect=min(20.0, timeout_seconds),
                write=min(30.0, timeout_seconds),
                pool=min(10.0, timeout_seconds),
            )
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            result_queue.put(("ok", response.json()))
        except Exception as exc:  # pragma: no cover - provider/proxy specific error types.
            result_queue.put(("error", exc))

    thread = threading.Thread(target=run_request, name="llm-chat-completion", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"LLM request exceeded wall timeout of {timeout_seconds:.0f}s")

    status, value = result_queue.get_nowait()
    if status == "error":
        raise value
    return value  # type: ignore[return-value]


def chat_completion(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    task_type: str,
    prompt_version: str,
    messages: list[dict[str, str]],
    project_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_type: Literal["user", "system", "worker"] = "system",
    complexity: ComplexityInput = "auto",
    temperature: float = 0.0,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    timeout_seconds: float | None = None,
    evidence_refs: dict[str, Any] | None = None,
) -> LLMResult:
    prompt_text = _message_text(messages)
    resolved_complexity = choose_complexity(
        task_type=task_type,
        messages=messages,
        complexity=complexity,
    )
    runtime_config = resolve_chat_model_config(db, tenant_id)
    model_name = choose_model(resolved_complexity, runtime_config)
    provider = runtime_config.provider or "mock"
    request_timeout_seconds = float(runtime_config.timeout_seconds)
    if timeout_seconds is not None:
        request_timeout_seconds = max(request_timeout_seconds, float(timeout_seconds))
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    estimated_tokens = _estimate_tokens(prompt_text)

    log = ModelInvocationLog(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        task_type=task_type,
        provider=provider,
        model_name=model_name,
        complexity=resolved_complexity,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        input_summary=_summary(prompt_text),
        input_tokens=estimated_tokens,
        status="skipped",
        request_json={
            "endpoint": "/chat/completions",
            "model": model_name,
            "temperature": temperature,
            "response_format": response_format,
            "max_tokens": max_tokens,
            "message_count": len(messages),
            "message_roles": [message.get("role") for message in messages],
            "prompt_char_count": len(prompt_text),
            "timeout_seconds": request_timeout_seconds,
            "model_config_source": runtime_config.source,
        },
        evidence_refs_json=evidence_refs,
    )
    db.add(log)
    db.flush()

    if provider not in {"deepseek", "openai_compatible"} or not runtime_config.api_key or not runtime_config.base_url:
        log.status = "skipped"
        log.error_code = "LLM_NOT_CONFIGURED"
        log.error_message = "远程模型未配置，已跳过调用。"
        _audit_invocation(
            db,
            log,
            action="model.invocation_skipped",
            severity="warning",
            reason="远程模型未配置，业务逻辑将使用本地兜底。",
        )
        db.flush()
        raise LLMGatewayError(log.error_message, code=log.error_code, log_id=log.id)

    payload: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    started_at = time.perf_counter()
    try:
        response_data = _post_chat_completion_with_wall_timeout(
            url=f"{runtime_config.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {runtime_config.api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout_seconds=request_timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        choice = response_data["choices"][0]
        content = choice["message"]["content"] or ""
        usage = response_data.get("usage") or {}
        input_tokens = _usage_value(usage, "prompt_tokens", "input_tokens") or estimated_tokens
        output_tokens = _usage_value(usage, "completion_tokens", "output_tokens")
        total_tokens = _usage_value(usage, "total_tokens")

        log.status = "succeeded"
        log.duration_ms = duration_ms
        log.output_summary = _summary(content)
        log.input_tokens = input_tokens
        log.output_tokens = output_tokens
        log.total_tokens = total_tokens
        log.response_json = {
            "finish_reason": choice.get("finish_reason"),
            "usage": usage,
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "content_char_count": len(content),
        }
        _audit_invocation(
            db,
            log,
            action="model.invocation_succeeded",
            severity="info",
            reason="远程模型调用成功。",
        )
        db.flush()
        return LLMResult(
            content=content,
            provider=provider,
            model_name=model_name,
            complexity=resolved_complexity,
            prompt_version=prompt_version,
            log_id=log.id,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
        )
    except Exception as exc:
        log.status = "failed"
        log.duration_ms = int((time.perf_counter() - started_at) * 1000)
        log.error_code = "LLM_CALL_FAILED"
        log.error_message = _safe_error_message(exc)
        _audit_invocation(
            db,
            log,
            action="model.invocation_failed",
            severity="warning",
            reason="远程模型调用失败，业务逻辑将使用本地兜底。",
        )
        db.flush()
        raise LLMGatewayError(log.error_message, code=log.error_code, log_id=log.id) from exc
