from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

LOCAL_RERANK_PROVIDER = "local_overlap_v1"
_REMOTE_PROVIDERS = ("infinity",)


class RerankGatewayError(Exception):
    def __init__(self, message: str, *, code: str = "RERANK_CALL_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RerankScore:
    index: int
    score: float
    provider: str
    runtime_provider: str
    model_name: str
    duration_ms: int
    fallback_used: bool = False
    error_message: str | None = None


def configured_rerank_provider() -> str:
    if not settings.rerank_enabled:
        return "disabled"
    provider = settings.rerank_provider.strip().lower()
    if provider in _REMOTE_PROVIDERS:
        model = settings.rerank_model.strip().lower().replace(":", "_").replace("-", "_").replace("/", "_")
        return f"{provider}_{model}"
    return LOCAL_RERANK_PROVIDER


def configured_rerank_model() -> str:
    if not settings.rerank_enabled:
        return "disabled"
    if settings.rerank_provider.strip().lower() in _REMOTE_PROVIDERS:
        return settings.rerank_model.strip() or "BAAI/bge-reranker-base"
    return "local_overlap"


def _build_timeout(seconds: float) -> httpx.Timeout:
    seconds = float(seconds)
    return httpx.Timeout(
        seconds,
        connect=min(10.0, seconds),
        read=seconds,
        write=min(10.0, seconds),
        pool=min(5.0, seconds),
    )


def _normalize_score(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    if 0.0 <= value <= 1.0:
        return round(value, 6)
    return round(1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, value)))), 6)


def _parse_rerank_payload(payload: dict[str, Any], *, count: int) -> list[tuple[int, float]]:
    raw_results = payload.get("results")
    if raw_results is None:
        raw_results = payload.get("data")
    if isinstance(raw_results, list):
        parsed: list[tuple[int, float]] = []
        for fallback_index, item in enumerate(raw_results):
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int):
                index = fallback_index
            score = item.get("relevance_score", item.get("score"))
            if score is None:
                score = item.get("logit")
            if isinstance(score, int | float):
                parsed.append((index, _normalize_score(float(score))))
        if parsed:
            return [(index, score) for index, score in parsed if 0 <= index < count]

    raw_scores = payload.get("scores")
    if isinstance(raw_scores, list):
        parsed = [
            (index, _normalize_score(float(score)))
            for index, score in enumerate(raw_scores)
            if isinstance(score, int | float)
        ]
        if parsed:
            return parsed[:count]
    raise RerankGatewayError("Rerank response did not include scores")


def _tokenize_search_text(text: str) -> list[str]:
    normalized = text.lower().replace("，", " ").replace("。", " ")
    tokens = [item for item in re.split(r"[\s,;；、:：()（）]+", normalized) if len(item) >= 2]
    cjk_text = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    tokens.extend(cjk_text[index : index + 2] for index in range(max(0, len(cjk_text) - 1)))
    return list(dict.fromkeys(tokens))


def _rerank_with_infinity(query: str, documents: list[str]) -> tuple[list[tuple[int, float]], str, str]:
    base_url = settings.rerank_base_url.rstrip("/")
    model_name = settings.rerank_model.strip() or "BAAI/bge-reranker-base"
    timeout = _build_timeout(settings.rerank_timeout_seconds)
    last_error: Exception | None = None
    with httpx.Client(timeout=timeout) as client:
        for path in ("/rerank", "/v1/rerank"):
            try:
                response = client.post(
                    f"{base_url}{path}",
                    json={"model": model_name, "query": query, "documents": documents},
                )
                response.raise_for_status()
                return (
                    _parse_rerank_payload(response.json(), count=len(documents)),
                    model_name,
                    "infinity_rerank",
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = exc
                    continue
                raise
            except Exception as exc:
                last_error = exc
                continue
    raise RerankGatewayError(str(last_error or "Infinity rerank endpoint is unavailable"))


def _local_overlap_scores(
    query: str,
    documents: list[str],
    *,
    base_scores: list[float] | None = None,
) -> list[tuple[int, float]]:
    query_terms = set(_tokenize_search_text(query))
    scored: list[tuple[int, float]] = []
    for index, document in enumerate(documents):
        doc_terms = set(_tokenize_search_text(document))
        overlap = len(query_terms & doc_terms) / max(1, len(query_terms))
        base = base_scores[index] if base_scores and index < len(base_scores) else 0.0
        scored.append((index, round(min(0.99, overlap * 0.7 + base * 0.3), 6)))
    return scored


def rerank_texts(
    query: str,
    documents: list[str],
    *,
    base_scores: list[float] | None = None,
) -> list[RerankScore]:
    if not documents:
        return []
    started = time.perf_counter()
    provider = configured_rerank_provider()
    model_name = configured_rerank_model()
    if not settings.rerank_enabled:
        return []

    provider_key = settings.rerank_provider.strip().lower()
    if provider_key in _REMOTE_PROVIDERS:
        try:
            scores, response_model, runtime_provider = _rerank_with_infinity(query, documents)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return [
                RerankScore(
                    index=index,
                    score=_normalize_score(score),
                    provider=provider,
                    runtime_provider=runtime_provider,
                    model_name=response_model,
                    duration_ms=duration_ms,
                )
                for index, score in scores
            ]
        except Exception as exc:
            if not settings.rerank_fallback_enabled:
                if isinstance(exc, RerankGatewayError):
                    raise
                raise RerankGatewayError(str(exc)) from exc
            scores = _local_overlap_scores(query, documents, base_scores=base_scores)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return [
                RerankScore(
                    index=index,
                    score=score,
                    provider=provider,
                    runtime_provider="local_overlap",
                    model_name=model_name,
                    duration_ms=duration_ms,
                    fallback_used=True,
                    error_message=str(exc)[:500],
                )
                for index, score in scores
            ]

    scores = _local_overlap_scores(query, documents, base_scores=base_scores)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return [
        RerankScore(
            index=index,
            score=score,
            provider=LOCAL_RERANK_PROVIDER,
            runtime_provider="local_overlap",
            model_name="local_overlap",
            duration_ms=duration_ms,
        )
        for index, score in scores
    ]
