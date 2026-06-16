from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EnterpriseMaterial, EnterpriseMaterialChunk
from app.services.embedding_gateway import (
    EMBEDDING_DIMENSIONS,
    configured_embedding_model,
    configured_embedding_provider,
    embed_text,
)
from app.services.material_safety import safe_rerank_text_for_material
from app.services.rerank_gateway import (
    configured_rerank_model,
    configured_rerank_provider,
    rerank_texts,
)

DEFAULT_ALLOWED_DATA_LEVELS = {"public", "internal"}
DEFAULT_SEARCH_STATUSES = {"confirmed"}

SEARCH_KEYWORDS = (
    "营业执照",
    "资质",
    "安全生产许可证",
    "许可证",
    "项目经理",
    "建造师",
    "职称",
    "社保",
    "业绩",
    "合同",
    "财务",
    "审计",
    "纳税",
    "信用",
    "联合体",
    "保修",
    "缺陷责任期",
    "承诺",
    "净化",
    "洁净",
    "设备",
    "型号",
    "检测报告",
    "技术方案",
    "安装调试",
    "验收",
)


@dataclass(frozen=True)
class MaterialSearchHit:
    material: EnterpriseMaterial
    chunk: EnterpriseMaterialChunk | None
    snippet: str | None
    confidence_score: float
    base_score: float | None = None
    rerank_score: float | None = None
    rerank_provider: str | None = None
    rerank_model: str | None = None
    rerank_used: bool = False
    rerank_fallback_used: bool = False
    rerank_error: str | None = None
    recommend_reason: str | None = None
    matched_terms: list[str] | None = None
    material_status_hint: str | None = None


@dataclass(frozen=True)
class MaterialIndexHealth:
    status: str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    fallback_chunk_count: int
    rerank_provider: str
    rerank_model: str
    total_material_count: int
    confirmed_material_count: int
    indexed_material_count: int
    unindexed_material_count: int
    stale_material_count: int
    chunk_count: int
    coverage_rate: float
    last_indexed_at: datetime | None
    unindexed_materials: list[dict[str, Any]]
    stale_materials: list[dict[str, Any]]


@dataclass(frozen=True)
class MaterialIndexRebuildResult:
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    rebuilt_material_count: int
    rebuilt_chunk_count: int
    removed_chunk_count: int
    skipped_material_count: int
    health: MaterialIndexHealth


@dataclass(frozen=True)
class MaterialChunkDraft:
    content_text: str
    metadata: dict[str, Any]


CHUNK_SCHEMA_VERSION = "enterprise-material-chunk-v2"
VOLATILE_MATERIAL_TEXT_FIELDS = {
    "duplicate_merge",
    "duplicate_of_material_id",
    "duplicate_review",
    "extraction_confidence",
    "extraction_method",
    "needs_human_confirm",
    "primary_source_image",
    "source",
    "source_file_name",
    "source_files",
    "source_images",
    "source_locations",
    "source_sha256",
    "trust_boundary",
}


def search_terms(query: str) -> list[str]:
    normalized = query.lower().replace("，", " ").replace("。", " ")
    terms = [item for item in re.split(r"\s+", normalized) if len(item) >= 2]
    terms.extend(keyword.lower() for keyword in SEARCH_KEYWORDS if keyword in query)
    return list(dict.fromkeys(terms))


def matched_search_terms(query: str, text: str) -> list[str]:
    haystack = text.lower()
    return [term for term in search_terms(query) if term in haystack]


def material_text(material: EnterpriseMaterial) -> str:
    searchable_fields = dict(material.structured_fields or {})
    for key in VOLATILE_MATERIAL_TEXT_FIELDS:
        searchable_fields.pop(key, None)
    structured = json.dumps(searchable_fields, ensure_ascii=False)
    values = [
        material.name,
        material.material_type,
        material.issuing_authority,
        material.certificate_no,
        material.holder_name,
        material.project_name,
        material.amount,
        material.evidence_text,
        structured,
    ]
    return "\n".join(value for value in values if value)


def material_status_hint(material: EnterpriseMaterial) -> str:
    labels = {
        "confirmed": "资料已确认，可作为优先候选证据",
        "pending_confirm": "资料待确认，绑定前建议人工复核",
        "draft": "资料仍为草稿，不能直接替代正式证明",
        "expired": "资料已过期，不建议作为响应证据",
        "conflict": "资料存在冲突，不建议作为响应证据",
        "missing_evidence": "资料缺少原始佐证，需补充后再使用",
    }
    return labels.get(material.verification_status, f"资料状态：{material.verification_status}")


def material_type_hint(material: EnterpriseMaterial, query: str) -> str | None:
    query_text = query.lower()
    type_labels = {
        "license": "证照类资料",
        "qualification": "资质类资料",
        "personnel": "人员类资料",
        "performance": "业绩类资料",
        "business_template": "商务模板",
        "commitment": "承诺材料",
        "product_catalog": "产品目录",
        "test_report": "检测报告",
        "product_image": "产品图片",
        "technical_proposal": "技术方案",
    }
    material_label = type_labels.get(material.material_type)
    if not material_label:
        return None
    if material.material_type in {"license", "qualification"} and any(
        term in query for term in ("营业执照", "资质", "许可证", "资格")
    ):
        return f"{material_label}与资格/证照要求匹配"
    if material.material_type == "personnel" and any(term in query for term in ("项目经理", "人员", "建造师", "职称")):
        return f"{material_label}与人员要求匹配"
    if material.material_type == "performance" and any(term in query for term in ("业绩", "合同", "类似项目")):
        return f"{material_label}与业绩要求匹配"
    if material.material_type in {"product_catalog", "test_report", "technical_proposal"} and any(
        term in query_text for term in ("技术", "设备", "洁净", "净化", "检测报告", "验收", "安装调试")
    ):
        return f"{material_label}与技术响应要求匹配"
    return f"资料类型为{material_label}"


def recommendation_reason(query: str, material: EnterpriseMaterial, content: str) -> tuple[str, list[str], str]:
    terms = matched_search_terms(query, content)
    status_hint = material_status_hint(material)
    if terms:
        keyword_text = "、".join(terms[:6])
        reason = f"命中“{keyword_text}”等关键词"
    else:
        reason = "与当前要求存在语义相近内容"
    type_hint = material_type_hint(material, query)
    if type_hint:
        reason = f"{reason}；{type_hint}"
    reason = f"{reason}；{status_hint}"
    return reason, terms, status_hint


def vector_to_pg(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(size))


def _as_dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _compact_json(value: object, *, limit: int = 800) -> str | None:
    if value in (None, "", [], {}):
        return None
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def _material_identity_lines(material: EnterpriseMaterial) -> list[str]:
    pairs = [
        ("资料名称", material.name),
        ("资料类型", material.material_type),
        ("证书编号", material.certificate_no),
        ("发证机关", material.issuing_authority),
        ("持有人", material.holder_name),
        ("项目名称", material.project_name),
        ("金额", material.amount),
        ("有效期至", material.valid_until.isoformat() if material.valid_until else None),
    ]
    return [f"{label}：{value}" for label, value in pairs if value]


def _base_chunk_metadata(material: EnterpriseMaterial) -> dict[str, Any]:
    return {
        "chunk_schema_version": CHUNK_SCHEMA_VERSION,
        "material_name": material.name,
        "material_type": material.material_type,
        "verification_status": material.verification_status,
        "data_level": material.data_level,
        "certificate_no": material.certificate_no,
        "valid_until": material.valid_until.isoformat() if material.valid_until else None,
    }


def _source_images_for_location(
    source_images: list[dict[str, Any]],
    location: dict[str, Any],
) -> list[dict[str, Any]]:
    page_no = location.get("page_no")
    block_index = location.get("block_index")
    matches = [
        image
        for image in source_images
        if (page_no is None or image.get("page_no") == page_no)
        and (block_index is None or image.get("block_index") in (None, block_index))
    ]
    return matches or (source_images[:1] if len(source_images) == 1 else [])


def _source_locations_from_fields(fields: dict[str, Any]) -> list[dict[str, Any]]:
    source_files = _as_dict_list(fields.get("source_files"))
    if not source_files:
        return [
            {
                **location,
                "source_file_name": fields.get("source_file_name"),
                "source_sha256": fields.get("source_sha256"),
            }
            for location in _as_dict_list(fields.get("source_locations"))
        ]

    locations: list[dict[str, Any]] = []
    for source_file in source_files:
        source_file_locations = _as_dict_list(source_file.get("source_locations"))
        if not source_file_locations:
            locations.append(
                {
                    "source_file_name": source_file.get("source_file_name") or source_file.get("file_name"),
                    "source_sha256": source_file.get("source_sha256") or source_file.get("sha256"),
                    "source_images": _as_dict_list(source_file.get("source_images")),
                }
            )
            continue
        for location in source_file_locations:
            locations.append(
                {
                    **location,
                    "source_file_name": source_file.get("source_file_name") or source_file.get("file_name"),
                    "source_sha256": source_file.get("source_sha256") or source_file.get("sha256"),
                    "source_images": _as_dict_list(source_file.get("source_images")),
                }
            )
    return locations


def _history_source_chunk_drafts(
    material: EnterpriseMaterial,
    fields: dict[str, Any],
) -> list[MaterialChunkDraft]:
    source_locations = _source_locations_from_fields(fields)
    if not source_locations:
        return []

    base_lines = _material_identity_lines(material)
    all_source_images = _as_dict_list(fields.get("source_images"))
    drafts: list[MaterialChunkDraft] = []
    for location in source_locations:
        snippet = str(location.get("snippet") or "").strip()
        table_text = _compact_json(location.get("table_json"))
        source_file_name = location.get("source_file_name") or fields.get("source_file_name") or material.file_name
        source_images = _source_images_for_location(
            _as_dict_list(location.get("source_images")) or all_source_images,
            location,
        )
        location_lines = [
            f"来源文件：{source_file_name}" if source_file_name else None,
            f"页码：{location.get('page_no')}" if location.get("page_no") is not None else None,
            f"来源块：{location.get('block_index')}" if location.get("block_index") is not None else None,
            f"标题路径：{location.get('heading_path')}" if location.get("heading_path") else None,
            f"原文片段：{snippet}" if snippet else None,
            f"表格内容：{table_text}" if table_text else None,
            f"证据摘要：{material.evidence_text}" if material.evidence_text and not snippet else None,
        ]
        content = "\n".join([*base_lines, *[line for line in location_lines if line]]).strip()
        if not content:
            continue
        metadata = {
            **_base_chunk_metadata(material),
            "chunk_strategy": "history_source_location",
            "source_file_name": source_file_name,
            "source_sha256": location.get("source_sha256") or fields.get("source_sha256"),
            "source_location": {
                key: location.get(key)
                for key in ("page_no", "block_index", "heading_path", "parser", "ocr_confidence")
                if location.get(key) is not None
            },
            "source_locations": [
                {
                    key: location.get(key)
                    for key in ("page_no", "block_index", "heading_path", "parser", "ocr_confidence", "snippet")
                    if location.get(key) is not None
                }
            ],
            "source_images": source_images,
            "primary_source_image": source_images[0] if source_images else None,
            "has_table": location.get("table_json") is not None,
        }
        drafts.append(MaterialChunkDraft(content_text=content, metadata=metadata))
    return drafts


def _paragraph_chunk_drafts(material: EnterpriseMaterial) -> list[MaterialChunkDraft]:
    source = material_text(material).strip() or material.name
    paragraphs = [item.strip() for item in re.split(r"\n+", source) if item.strip()]
    chunks: list[MaterialChunkDraft] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > 500 and current:
            chunks.append(
                MaterialChunkDraft(
                    content_text=current,
                    metadata={
                        **_base_chunk_metadata(material),
                        "chunk_strategy": "material_paragraph",
                    },
                )
            )
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(
            MaterialChunkDraft(
                content_text=current,
                metadata={
                    **_base_chunk_metadata(material),
                    "chunk_strategy": "material_paragraph",
                },
            )
        )
    return chunks or [
        MaterialChunkDraft(
            content_text=material.name,
            metadata={
                **_base_chunk_metadata(material),
                "chunk_strategy": "material_paragraph",
            },
        )
    ]


def split_material_chunks(material: EnterpriseMaterial) -> list[MaterialChunkDraft]:
    structured_fields = material.structured_fields or {}
    if isinstance(structured_fields, dict) and structured_fields.get("source") == "history_file_extract":
        history_chunks = _history_source_chunk_drafts(material, structured_fields)
        if history_chunks:
            return history_chunks
    return _paragraph_chunk_drafts(material)


def rebuild_material_chunks(db: Session, material: EnterpriseMaterial) -> list[EnterpriseMaterialChunk]:
    db.execute(
        delete(EnterpriseMaterialChunk).where(
            EnterpriseMaterialChunk.tenant_id == material.tenant_id,
            EnterpriseMaterialChunk.enterprise_material_id == material.id,
        )
    )
    chunks: list[EnterpriseMaterialChunk] = []
    for index, chunk_draft in enumerate(split_material_chunks(material)):
        content = chunk_draft.content_text
        embedding = embed_text(content)
        chunk = EnterpriseMaterialChunk(
            tenant_id=material.tenant_id,
            enterprise_material_id=material.id,
            chunk_index=index,
            content_text=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            metadata_json={
                **chunk_draft.metadata,
                "embedding_provider": embedding.provider,
                "embedding_runtime_provider": embedding.runtime_provider,
                "embedding_model": embedding.model_name,
                "embedding_dimensions": embedding.dimensions,
                "embedding_source_dimensions": embedding.source_dimensions,
                "embedding_duration_ms": embedding.duration_ms,
                "embedding_fallback_used": embedding.fallback_used,
                "embedding_error": embedding.error_message,
            },
            embedding_vector=vector_to_pg(embedding.vector),
            embedding_json=embedding.vector,
            data_level=material.data_level,
            token_count=max(1, len(content) // 2),
        )
        db.add(chunk)
        chunks.append(chunk)
    return chunks


def _virtual_chunk(material: EnterpriseMaterial) -> EnterpriseMaterialChunk:
    text = material_text(material).strip() or material.name
    embedding = embed_text(text)
    return EnterpriseMaterialChunk(
        id=uuid.uuid4(),
        tenant_id=material.tenant_id,
        enterprise_material_id=material.id,
        chunk_index=0,
        content_text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata_json={
            "material_name": material.name,
            "virtual": True,
            "embedding_provider": embedding.provider,
            "embedding_runtime_provider": embedding.runtime_provider,
            "embedding_model": embedding.model_name,
            "embedding_dimensions": embedding.dimensions,
            "embedding_source_dimensions": embedding.source_dimensions,
            "embedding_fallback_used": embedding.fallback_used,
            "embedding_error": embedding.error_message,
        },
        embedding_vector=vector_to_pg(embedding.vector),
        embedding_json=embedding.vector,
        data_level=material.data_level,
        token_count=max(1, len(text) // 2),
    )


def _score_chunk(
    *,
    chunk_text: str,
    query: str,
    query_terms: list[str],
    query_embedding: list[float],
    chunk_embedding: list[float] | None,
) -> float:
    if not query.strip():
        return 0.5
    haystack = chunk_text.lower()
    matched_terms = [term for term in query_terms if term in haystack]
    vector_score = max(0.0, cosine_similarity(query_embedding, chunk_embedding or [])) * 0.2
    if not matched_terms and vector_score < 0.08:
        return 0.0
    keyword_score = min(0.72, 0.24 * len(matched_terms))
    return min(0.99, keyword_score + vector_score)


def _material_ref(material: EnterpriseMaterial) -> dict[str, Any]:
    return {
        "id": str(material.id),
        "name": material.name,
        "material_type": material.material_type,
        "verification_status": material.verification_status,
        "updated_at": material.updated_at.isoformat() if material.updated_at else None,
    }


def get_material_index_health(db: Session, *, tenant_id: uuid.UUID) -> MaterialIndexHealth:
    materials = list(
        db.scalars(
            select(EnterpriseMaterial)
            .where(EnterpriseMaterial.tenant_id == tenant_id)
            .order_by(EnterpriseMaterial.updated_at.desc())
        ).all()
    )
    confirmed_materials = [material for material in materials if material.verification_status == "confirmed"]
    chunks = list(
        db.scalars(
            select(EnterpriseMaterialChunk).where(EnterpriseMaterialChunk.tenant_id == tenant_id)
        ).all()
    )
    expected_provider = configured_embedding_provider()
    chunk_stats: dict[uuid.UUID, dict[str, Any]] = {}
    fallback_chunk_count = 0
    for chunk in chunks:
        metadata = chunk.metadata_json or {}
        stats = chunk_stats.setdefault(
            chunk.enterprise_material_id,
            {
                "count": 0,
                "last_indexed_at": None,
                "provider_mismatch": False,
                "dimension_mismatch": False,
            },
        )
        stats["count"] += 1
        if stats["last_indexed_at"] is None or chunk.updated_at > stats["last_indexed_at"]:
            stats["last_indexed_at"] = chunk.updated_at
        if metadata.get("embedding_provider") != expected_provider:
            stats["provider_mismatch"] = True
        if metadata.get("embedding_dimensions") != EMBEDDING_DIMENSIONS:
            stats["dimension_mismatch"] = True
        if isinstance(chunk.embedding_json, list) and len(chunk.embedding_json) != EMBEDDING_DIMENSIONS:
            stats["dimension_mismatch"] = True
        if metadata.get("embedding_fallback_used") is True:
            fallback_chunk_count += 1
    indexed_material_count = 0
    unindexed_materials: list[dict[str, Any]] = []
    stale_materials: list[dict[str, Any]] = []
    for material in confirmed_materials:
        stats = chunk_stats.get(material.id)
        if not stats or stats["count"] <= 0:
            unindexed_materials.append(_material_ref(material))
            continue
        indexed_material_count += 1
        last_indexed_at = stats["last_indexed_at"]
        if material.updated_at and last_indexed_at and material.updated_at > last_indexed_at:
            stale_ref = _material_ref(material)
            stale_ref["last_indexed_at"] = last_indexed_at.isoformat()
            stale_ref["reason"] = "material_updated_after_index"
            stale_materials.append(stale_ref)
        elif stats["provider_mismatch"] or stats["dimension_mismatch"]:
            stale_ref = _material_ref(material)
            stale_ref["last_indexed_at"] = last_indexed_at.isoformat() if last_indexed_at else None
            reasons = []
            if stats["provider_mismatch"]:
                reasons.append("embedding_provider_changed")
            if stats["dimension_mismatch"]:
                reasons.append("embedding_dimension_changed")
            stale_ref["reason"] = ",".join(reasons)
            stale_materials.append(stale_ref)

    chunk_count = len(chunks)
    confirmed_count = len(confirmed_materials)
    unhealthy_count = len(unindexed_materials) + len(stale_materials)
    if confirmed_count == 0:
        status = "empty"
    elif unhealthy_count == 0:
        status = "healthy"
    else:
        status = "needs_rebuild"
    coverage_rate = round(indexed_material_count / confirmed_count, 4) if confirmed_count else 1.0
    last_indexed_at_values = [
        stats["last_indexed_at"] for stats in chunk_stats.values() if stats["last_indexed_at"] is not None
    ]
    last_indexed_at = max(last_indexed_at_values) if last_indexed_at_values else None
    return MaterialIndexHealth(
        status=status,
        embedding_provider=expected_provider,
        embedding_model=configured_embedding_model(),
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        fallback_chunk_count=fallback_chunk_count,
        rerank_provider=configured_rerank_provider(),
        rerank_model=configured_rerank_model(),
        total_material_count=len(materials),
        confirmed_material_count=confirmed_count,
        indexed_material_count=indexed_material_count,
        unindexed_material_count=len(unindexed_materials),
        stale_material_count=len(stale_materials),
        chunk_count=chunk_count,
        coverage_rate=coverage_rate,
        last_indexed_at=last_indexed_at,
        unindexed_materials=unindexed_materials[:20],
        stale_materials=stale_materials[:20],
    )


def rebuild_tenant_material_index(db: Session, *, tenant_id: uuid.UUID) -> MaterialIndexRebuildResult:
    confirmed_materials = list(
        db.scalars(
            select(EnterpriseMaterial)
            .where(
                EnterpriseMaterial.tenant_id == tenant_id,
                EnterpriseMaterial.verification_status == "confirmed",
            )
            .order_by(EnterpriseMaterial.updated_at.asc())
        ).all()
    )
    confirmed_ids = [material.id for material in confirmed_materials]
    stale_delete = delete(EnterpriseMaterialChunk).where(
        EnterpriseMaterialChunk.tenant_id == tenant_id,
    )
    if confirmed_ids:
        stale_delete = stale_delete.where(EnterpriseMaterialChunk.enterprise_material_id.not_in(confirmed_ids))
    removed_chunk_count = int(db.execute(stale_delete).rowcount or 0)

    rebuilt_chunk_count = 0
    for material in confirmed_materials:
        rebuilt_chunk_count += len(rebuild_material_chunks(db, material))
    db.flush()
    health = get_material_index_health(db, tenant_id=tenant_id)
    return MaterialIndexRebuildResult(
        embedding_provider=configured_embedding_provider(),
        embedding_model=configured_embedding_model(),
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        rebuilt_material_count=len(confirmed_materials),
        rebuilt_chunk_count=rebuilt_chunk_count,
        removed_chunk_count=removed_chunk_count,
        skipped_material_count=max(0, health.total_material_count - len(confirmed_materials)),
        health=health,
    )


def _hit_rerank_text(hit: MaterialSearchHit) -> str:
    safe_text = safe_rerank_text_for_material(hit.material)
    if safe_text:
        return safe_text
    values = [
        hit.material.name,
        hit.snippet,
        hit.chunk.content_text if hit.chunk else None,
        hit.material.evidence_text,
        hit.material.project_name,
        hit.material.certificate_no,
    ]
    return "\n".join(value for value in values if value)


def _rerank_hits(query: str, hits: list[MaterialSearchHit]) -> list[MaterialSearchHit]:
    if not query.strip() or len(hits) < 2:
        return hits
    documents = [_hit_rerank_text(hit) for hit in hits]
    base_scores = [hit.confidence_score for hit in hits]
    rerank_scores = rerank_texts(query, documents, base_scores=base_scores)
    if not rerank_scores:
        return hits
    score_map = {score.index: score for score in rerank_scores}
    reranked: list[MaterialSearchHit] = []
    for index, hit in enumerate(hits):
        rerank_score = score_map.get(index)
        if rerank_score is None:
            reranked.append(hit)
            continue
        final_score = min(0.99, rerank_score.score * 0.72 + hit.confidence_score * 0.28)
        reranked.append(
            replace(
                hit,
                confidence_score=round(final_score, 4),
                base_score=hit.confidence_score,
                rerank_score=round(rerank_score.score, 4),
                rerank_provider=rerank_score.provider,
                rerank_model=rerank_score.model_name,
                rerank_used=not rerank_score.fallback_used,
                rerank_fallback_used=rerank_score.fallback_used,
                rerank_error=rerank_score.error_message,
            )
        )
    reranked.sort(key=lambda item: (item.confidence_score, item.material.updated_at), reverse=True)
    return reranked


def _chunk_vector_scores(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    query_embedding: list[float],
    allowed_data_levels: set[str],
    verification_statuses: set[str],
    material_type: str | None,
    limit: int,
) -> dict[uuid.UUID, float]:
    distance = EnterpriseMaterialChunk.embedding_vector.op("<=>")(vector_to_pg(query_embedding))
    stmt = (
        select(EnterpriseMaterialChunk.id, (1 - distance).label("similarity"))
        .join(EnterpriseMaterial, EnterpriseMaterial.id == EnterpriseMaterialChunk.enterprise_material_id)
        .where(
            EnterpriseMaterialChunk.tenant_id == tenant_id,
            EnterpriseMaterialChunk.data_level.in_(allowed_data_levels),
            EnterpriseMaterialChunk.embedding_vector.is_not(None),
            EnterpriseMaterial.tenant_id == tenant_id,
            EnterpriseMaterial.verification_status.in_(verification_statuses),
        )
        .order_by(distance.asc())
        .limit(max(50, limit * 12))
    )
    if material_type:
        stmt = stmt.where(EnterpriseMaterial.material_type == material_type)
    try:
        rows = db.execute(stmt).all()
    except SQLAlchemyError:
        db.rollback()
        return {}
    return {chunk_id: max(0.0, float(similarity or 0.0)) for chunk_id, similarity in rows}


def search_material_hits(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    query: str,
    material_type: str | None = None,
    verification_status: str | None = None,
    verification_statuses: set[str] | None = None,
    allowed_data_levels: set[str] | None = None,
    limit: int = 20,
) -> list[MaterialSearchHit]:
    allowed = allowed_data_levels or DEFAULT_ALLOWED_DATA_LEVELS
    statuses = verification_statuses or ({verification_status} if verification_status else DEFAULT_SEARCH_STATUSES)
    stmt = select(EnterpriseMaterial).where(
        EnterpriseMaterial.tenant_id == tenant_id,
        EnterpriseMaterial.data_level.in_(allowed),
        EnterpriseMaterial.verification_status.in_(statuses),
    )
    if material_type:
        stmt = stmt.where(EnterpriseMaterial.material_type == material_type)
    materials = db.scalars(stmt.order_by(EnterpriseMaterial.updated_at.desc()).limit(200)).all()

    terms = search_terms(query)
    query_embedding = embed_text(query).vector
    vector_scores = _chunk_vector_scores(
        db,
        tenant_id=tenant_id,
        query_embedding=query_embedding,
        allowed_data_levels=allowed,
        verification_statuses=statuses,
        material_type=material_type,
        limit=limit,
    )
    hits: list[MaterialSearchHit] = []
    for material in materials:
        chunks = db.scalars(
            select(EnterpriseMaterialChunk)
            .where(
                EnterpriseMaterialChunk.tenant_id == tenant_id,
                EnterpriseMaterialChunk.enterprise_material_id == material.id,
                EnterpriseMaterialChunk.data_level.in_(allowed),
            )
            .order_by(EnterpriseMaterialChunk.chunk_index.asc())
        ).all()
        if chunks:
            candidates = chunks
        elif material.verification_status in statuses:
            candidates = [_virtual_chunk(material)]
        else:
            continue
        best_hit: MaterialSearchHit | None = None
        for chunk in candidates:
            score = _score_chunk(
                chunk_text=chunk.content_text,
                query=query,
                query_terms=terms,
                query_embedding=query_embedding,
                chunk_embedding=chunk.embedding_json,
            )
            if chunk.id in vector_scores:
                score = min(0.99, max(score, vector_scores[chunk.id] * 0.22))
            if score <= 0 and query.strip():
                continue
            if material.verification_status == "confirmed":
                score = min(0.99, score + 0.08)
            snippet = chunk.content_text[:220]
            reason, matched_terms, status_hint = recommendation_reason(query, material, chunk.content_text)
            hit = MaterialSearchHit(
                material=material,
                chunk=chunk if chunks else None,
                snippet=snippet,
                confidence_score=round(score, 4),
                recommend_reason=reason,
                matched_terms=matched_terms,
                material_status_hint=status_hint,
            )
            if best_hit is None or hit.confidence_score > best_hit.confidence_score:
                best_hit = hit
        if best_hit is not None:
            hits.append(best_hit)

    hits.sort(key=lambda item: (item.confidence_score, item.material.updated_at), reverse=True)
    rerank_top_k = max(1, int(settings.rerank_top_k))
    rerank_candidates = hits[: min(max(limit, 1), rerank_top_k)]
    return (_rerank_hits(query, rerank_candidates) + hits[len(rerank_candidates) :])[:limit]
