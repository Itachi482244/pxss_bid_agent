from __future__ import annotations

from typing import Any

from app.models import EnterpriseMaterial
from app.schemas.enterprise import EnterpriseMaterialRead, EnterpriseMaterialSearchResult

SENSITIVE_DATA_LEVELS = {"restricted", "confidential"}
REDACTED_EVIDENCE_TEXT = "受限资料片段已隐藏；请完成脱敏或授权复核后再查看。"


def is_sensitive_data_level(data_level: str | None) -> bool:
    return data_level in SENSITIVE_DATA_LEVELS


def is_sensitive_material(material: EnterpriseMaterial) -> bool:
    return is_sensitive_data_level(material.data_level)


def redacted_material_name(material: EnterpriseMaterial) -> str:
    label = "机密资料" if material.data_level == "confidential" else "受限资料"
    return f"{label}（需授权查看）"


def safe_rerank_text_for_material(material: EnterpriseMaterial) -> str:
    if is_sensitive_material(material):
        return "\n".join(
            value
            for value in (
                redacted_material_name(material),
                material.material_type,
                material.verification_status,
                "资料内容受限，不能进入模型重排上下文。",
            )
            if value
        )
    return ""


def material_search_result_from_hit(
    hit: Any,
    *,
    allowed_data_levels: set[str],
) -> EnterpriseMaterialSearchResult:
    material_payload = EnterpriseMaterialRead.model_validate(hit.material).model_dump()
    data_level_allowed = hit.material.data_level in allowed_data_levels
    snippet = hit.snippet
    recommend_reason = hit.recommend_reason
    matched_terms = hit.matched_terms or []
    material_status_hint = hit.material_status_hint

    if is_sensitive_material(hit.material):
        material_payload.update(
            {
                "name": redacted_material_name(hit.material),
                "issuing_authority": None,
                "certificate_no": None,
                "holder_name": None,
                "project_name": None,
                "amount": None,
                "valid_from": None,
                "valid_until": None,
                "structured_fields": {
                    "redacted": True,
                    "data_level": hit.material.data_level,
                    "reason": "sensitive_material_requires_desensitization",
                },
                "evidence_text": None,
                "file_name": None,
                "sha256": None,
            }
        )
        snippet = REDACTED_EVIDENCE_TEXT
        data_level_allowed = False
        matched_terms = []
        material_status_hint = "资料受限，不能直接作为响应证据；需脱敏或授权复核后再使用"
        recommend_reason = "存在可能相关的受限资料；片段已隐藏，不能自动绑定或进入 ContextPack"

    return EnterpriseMaterialSearchResult(
        **material_payload,
        snippet=snippet,
        confidence_score=hit.confidence_score,
        base_score=hit.base_score,
        rerank_score=hit.rerank_score,
        rerank_provider=hit.rerank_provider,
        rerank_model=hit.rerank_model,
        rerank_used=hit.rerank_used,
        rerank_fallback_used=hit.rerank_fallback_used,
        rerank_error=hit.rerank_error,
        chunk_id=hit.chunk.id if hit.chunk else None,
        data_level_allowed=data_level_allowed,
        recommend_reason=recommend_reason,
        matched_terms=matched_terms,
        material_status_hint=material_status_hint,
    )
