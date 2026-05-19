from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import EnterpriseMaterial, EnterpriseMaterialChunk

EMBEDDING_DIMENSIONS = 16

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


def search_terms(query: str) -> list[str]:
    normalized = query.lower().replace("，", " ").replace("。", " ")
    terms = [item for item in re.split(r"\s+", normalized) if len(item) >= 2]
    terms.extend(keyword.lower() for keyword in SEARCH_KEYWORDS if keyword in query)
    return list(dict.fromkeys(terms))


def material_text(material: EnterpriseMaterial) -> str:
    structured = json.dumps(material.structured_fields or {}, ensure_ascii=False)
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


def pseudo_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in re.findall(r"[\w\u4e00-\u9fff]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % EMBEDDING_DIMENSIONS
        vector[index] += 1.0 + digest[1] / 255.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def vector_to_pg(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[index] * right[index] for index in range(size))


def split_material_chunks(material: EnterpriseMaterial) -> list[str]:
    source = material_text(material).strip() or material.name
    paragraphs = [item.strip() for item in re.split(r"\n+", source) if item.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > 500 and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks or [material.name]


def rebuild_material_chunks(db: Session, material: EnterpriseMaterial) -> list[EnterpriseMaterialChunk]:
    db.execute(
        delete(EnterpriseMaterialChunk).where(
            EnterpriseMaterialChunk.tenant_id == material.tenant_id,
            EnterpriseMaterialChunk.enterprise_material_id == material.id,
        )
    )
    chunks: list[EnterpriseMaterialChunk] = []
    for index, content in enumerate(split_material_chunks(material)):
        embedding = pseudo_embedding(content)
        chunk = EnterpriseMaterialChunk(
            tenant_id=material.tenant_id,
            enterprise_material_id=material.id,
            chunk_index=index,
            content_text=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            metadata_json={
                "material_name": material.name,
                "material_type": material.material_type,
                "verification_status": material.verification_status,
            },
            embedding_vector=vector_to_pg(embedding),
            embedding_json=embedding,
            data_level=material.data_level,
            token_count=max(1, len(content) // 2),
        )
        db.add(chunk)
        chunks.append(chunk)
    return chunks


def _virtual_chunk(material: EnterpriseMaterial) -> EnterpriseMaterialChunk:
    text = material_text(material).strip() or material.name
    embedding = pseudo_embedding(text)
    return EnterpriseMaterialChunk(
        id=uuid.uuid4(),
        tenant_id=material.tenant_id,
        enterprise_material_id=material.id,
        chunk_index=0,
        content_text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata_json={"material_name": material.name, "virtual": True},
        embedding_vector=vector_to_pg(embedding),
        embedding_json=embedding,
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
    if not matched_terms:
        return 0.0
    keyword_score = min(0.72, 0.24 * len(matched_terms))
    vector_score = max(0.0, cosine_similarity(query_embedding, chunk_embedding or [])) * 0.2
    return min(0.99, keyword_score + vector_score)


def search_material_hits(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    query: str,
    material_type: str | None = None,
    verification_status: str | None = None,
    allowed_data_levels: set[str] | None = None,
    limit: int = 20,
) -> list[MaterialSearchHit]:
    allowed = allowed_data_levels or {"public", "internal"}
    stmt = select(EnterpriseMaterial).where(
        EnterpriseMaterial.tenant_id == tenant_id,
        EnterpriseMaterial.data_level.in_(allowed),
    )
    if material_type:
        stmt = stmt.where(EnterpriseMaterial.material_type == material_type)
    if verification_status:
        stmt = stmt.where(EnterpriseMaterial.verification_status == verification_status)
    materials = db.scalars(stmt.order_by(EnterpriseMaterial.updated_at.desc()).limit(200)).all()

    terms = search_terms(query)
    query_embedding = pseudo_embedding(query)
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
        candidates = chunks or [_virtual_chunk(material)]
        best_hit: MaterialSearchHit | None = None
        for chunk in candidates:
            score = _score_chunk(
                chunk_text=chunk.content_text,
                query=query,
                query_terms=terms,
                query_embedding=query_embedding,
                chunk_embedding=chunk.embedding_json,
            )
            if score <= 0 and query.strip():
                continue
            if material.verification_status == "confirmed":
                score = min(0.99, score + 0.08)
            snippet = chunk.content_text[:220]
            hit = MaterialSearchHit(
                material=material,
                chunk=chunk if chunks else None,
                snippet=snippet,
                confidence_score=round(score, 4),
            )
            if best_hit is None or hit.confidence_score > best_hit.confidence_score:
                best_hit = hit
        if best_hit is not None:
            hits.append(best_hit)

    hits.sort(key=lambda item: (item.confidence_score, item.material.updated_at), reverse=True)
    return hits[:limit]
