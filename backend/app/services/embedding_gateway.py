from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

EMBEDDING_DIMENSIONS = 768
LOCAL_HASH_PROVIDER = "local_hash_v1_768"
_REMOTE_PROVIDERS = ("infinity",)


class EmbeddingGatewayError(Exception):
    def __init__(self, message: str, *, code: str = "EMBEDDING_CALL_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TextEmbedding:
    vector: list[float]
    provider: str
    runtime_provider: str
    model_name: str
    dimensions: int
    source_dimensions: int
    duration_ms: int
    fallback_used: bool = False
    error_message: str | None = None


def configured_embedding_provider() -> str:
    provider = settings.embedding_provider.strip().lower()
    if provider in _REMOTE_PROVIDERS:
        model = (
            settings.embedding_model.strip().lower().replace(":", "_").replace("-", "_").replace("/", "_")
        )
        return f"{provider}_{model}_{EMBEDDING_DIMENSIONS}"
    return LOCAL_HASH_PROVIDER


def configured_embedding_model() -> str:
    if settings.embedding_provider.strip().lower() in _REMOTE_PROVIDERS:
        return settings.embedding_model.strip() or "BAAI/bge-base-zh-v1.5"
    return "local_hash"


def _build_timeout(seconds: float) -> httpx.Timeout:
    seconds = float(seconds)
    return httpx.Timeout(
        seconds,
        connect=min(10.0, seconds),
        read=seconds,
        write=min(10.0, seconds),
        pool=min(5.0, seconds),
    )


def _normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _fit_dimensions(vector: list[float]) -> list[float]:
    if len(vector) >= EMBEDDING_DIMENSIONS:
        fitted = vector[:EMBEDDING_DIMENSIONS]
    else:
        fitted = vector + [0.0] * (EMBEDDING_DIMENSIONS - len(vector))
    return _normalize_vector([float(value) for value in fitted])


def _local_hash_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in re.findall(r"[\w\u4e00-\u9fff]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % EMBEDDING_DIMENSIONS
        vector[index] += 1.0 + digest[1] / 255.0
    return _normalize_vector(vector)


def _embed_with_infinity(text: str) -> tuple[list[float], str, int]:
    base_url = settings.embedding_base_url.rstrip("/")
    model_name = settings.embedding_model.strip() or "BAAI/bge-base-zh-v1.5"
    timeout = _build_timeout(settings.embedding_timeout_seconds)
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout) as client:
        for path in ("/embeddings", "/v1/embeddings"):
            try:
                response = client.post(
                    f"{base_url}{path}", json={"model": model_name, "input": [text]}
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = exc
                    continue
                raise
            except Exception as exc:
                last_error = exc
                continue
            payload: dict[str, Any] = response.json()
            data = payload.get("data")
            if not isinstance(data, list) or not data:
                raise EmbeddingGatewayError("Infinity embedding response did not include data")
            first = data[0]
            raw_vector = first.get("embedding") if isinstance(first, dict) else None
            if not isinstance(raw_vector, list) or not raw_vector:
                raise EmbeddingGatewayError("Infinity embedding vector is empty")
            return (
                [float(value) for value in raw_vector],
                str(payload.get("model") or model_name),
                len(raw_vector),
            )
    raise EmbeddingGatewayError(str(last_error or "Infinity embedding endpoint is unavailable"))


def embed_text(text: str) -> TextEmbedding:
    provider = configured_embedding_provider()
    model_name = configured_embedding_model()
    started = time.perf_counter()
    provider_key = settings.embedding_provider.strip().lower()
    # 调用时按名查找，保证测试 monkeypatch 模块属性时仍能命中。
    remote_call = _embed_with_infinity if provider_key == "infinity" else None
    if remote_call is not None:
        try:
            raw_vector, response_model, source_dimensions = remote_call(text)
            return TextEmbedding(
                vector=_fit_dimensions(raw_vector),
                provider=provider,
                runtime_provider=provider_key,
                model_name=response_model,
                dimensions=EMBEDDING_DIMENSIONS,
                source_dimensions=source_dimensions,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            if not settings.embedding_fallback_enabled:
                if isinstance(exc, EmbeddingGatewayError):
                    raise
                raise EmbeddingGatewayError(str(exc)) from exc
            fallback_vector = _local_hash_embedding(text)
            return TextEmbedding(
                vector=fallback_vector,
                provider=provider,
                runtime_provider="local_hash",
                model_name=model_name,
                dimensions=EMBEDDING_DIMENSIONS,
                source_dimensions=EMBEDDING_DIMENSIONS,
                duration_ms=int((time.perf_counter() - started) * 1000),
                fallback_used=True,
                error_message=str(exc)[:500],
            )

    fallback_vector = _local_hash_embedding(text)
    return TextEmbedding(
        vector=fallback_vector,
        provider=LOCAL_HASH_PROVIDER,
        runtime_provider="local_hash",
        model_name="local_hash",
        dimensions=EMBEDDING_DIMENSIONS,
        source_dimensions=EMBEDDING_DIMENSIONS,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
