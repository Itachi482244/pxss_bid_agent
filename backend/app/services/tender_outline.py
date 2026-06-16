"""整合层：从项目的招标文件推导"建议目录"，映射成可喂入生成链路的 OutlineChapterInput。

数据流：
  招标文档(doc_type='tender') 最新已解析版本 → DocumentChunk 重建线性正文
  → tender_directory.derive_directory() 得到 DirectoryOutline（骨架+采购信号）
  → 映射成 [{section_type, title, custom, attachments}]
       · 能匹配 template_profile 章节的 → 真 section_type（走富生成）
       · 匹配不上的 → custom 占位章节（manual_placeholder，人工填）

输出直接供前端 seed `editedOutline`，再走既有 preview→确认→生成 通路。
本模块不持久化、不改 profile；目录的"权威骨架优先"通过现有 outline 覆盖通路实现。
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentVersion
from app.services.template_profile import get_template_profile, iter_profile_sections
from app.services.tender_directory import OutlineNode, derive_directory

# 招标文件章节标题关键词 → template_profile section_type（顺序匹配，先命中先用）
_SECTION_TYPE_RULES: list[tuple[tuple[str, ...], str]] = [
    (("法定代表人身份", "法人身份", "单位负责人身份"), "legal_representative_identity"),
    (("授权委托", "授权书"), "authorization_letter"),
    (("投标函", "响应函"), "bid_letter"),
    (("保证金",), "bid_security"),
    (("承诺书", "响应声明", "投标声明", "磋商声明"), "bid_commitment"),
    (("联合体",), "consortium_agreement"),
    (("已标价工程量清单", "工程量清单报价", "分项报价", "报价明细", "分项价格"), "boq_pricing_explanation"),
    (("报价一览", "投标总价", "开标一览", "报价表", "最后报价"), "bid_price_cover"),
    (("财务",), "financial_status"),
    (("基本情况", "供应商基本", "投标人基本"), "bidder_basic_info"),
    (("项目管理", "项目班子", "管理班子", "项目机构"), "project_management_team"),
    (("项目负责人简历", "项目经理简历", "负责人简历"), "project_manager_resume"),
    (("业绩",), "qualification_performance_summary"),
    (("资格", "资质"), "qualification_other_materials"),
]


def load_tender_text(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> tuple[str | None, dict[str, Any]]:
    """取最新已解析的招标文档，按 chunk 顺序重建线性正文。

    重建策略：heading_path 变化时只补一次"末级标题"行（去重，避免在枚举列表中间
    插入重复标题而打断『一、二、…』连续性），其余追加 content_text。
    """
    doc = db.scalar(
        select(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.project_id == project_id,
            Document.section_id == section_id,
            Document.doc_type == "tender",
            Document.status != "deleted",
        )
        .order_by(Document.created_at.desc())
    )
    if doc is None:
        return None, {"reason": "no_tender_document"}

    version = (
        db.get(DocumentVersion, doc.current_version_id) if doc.current_version_id else None
    )
    if version is None or version.parse_status != "succeeded":
        return None, {
            "reason": "tender_not_parsed",
            "document_id": str(doc.id),
            "title": doc.title,
            "version_status": version.parse_status if version else None,
        }

    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_version_id == version.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        return None, {"reason": "no_chunks", "document_id": str(doc.id), "title": doc.title}

    # 仅用 content_text 重建线性正文：本项目 Word 解析器会把标题也写进 content_text，
    # 因此无需再从 heading_path 注入标题（且 heading_path 以 "/" 连接，遇到含 "/" 的
    # 标题如「技术/商务响应与偏离表」会被 split 截断产生孤儿行，反而打断枚举解析）。
    parts: list[str] = []
    for c in chunks:
        ct = (c.content_text or "").strip()
        if ct:
            parts.append(ct)

    # 折叠相邻重复行（标题/正文重复输出时去噪）。
    deduped: list[str] = []
    for line in parts:
        if deduped and deduped[-1] == line:
            continue
        deduped.append(line)
    parts = deduped

    meta = {
        "document_id": str(doc.id),
        "version_id": str(version.id),
        "title": doc.title,
        "chunk_count": len(chunks),
    }
    return "\n".join(parts), meta


def _match_section_type(title: str, known: set[str]) -> str | None:
    for keywords, section_type in _SECTION_TYPE_RULES:
        if section_type in known and any(k in title for k in keywords):
            return section_type
    return None


def _slugify(title: str, order: int) -> str:
    base = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", title or "").strip("_")
    slug = f"tender_{order}_{base}" if base else f"tender_{order}"
    return slug[:120]


def map_nodes_to_chapters(
    nodes: list[OutlineNode], profile: dict[str, Any]
) -> list[dict[str, Any]]:
    known = {s["section_type"] for s in iter_profile_sections(profile)}
    chapters: list[dict[str, Any]] = []
    used_custom: set[str] = set()
    for node in nodes:
        attachments = [c.title for c in node.children]
        section_type = _match_section_type(node.title, known)
        if section_type:
            chapters.append(
                {
                    "section_type": section_type,
                    "title": node.title,
                    "custom": False,
                    "mapped_from": "profile",
                    "attachments": attachments,
                }
            )
        else:
            slug = _slugify(node.title, node.order)
            while slug in used_custom:
                slug = f"{slug}_x"
            used_custom.add(slug)
            chapters.append(
                {
                    "section_type": slug,
                    "title": node.title,
                    "custom": True,
                    "mapped_from": "custom",
                    "attachments": attachments,
                }
            )
    return chapters


def derive_project_directory(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """供 API 调用：返回招标文件推导出的建议目录 + 采购方式/信号/诊断。"""
    text, meta = load_tender_text(
        db, tenant_id=tenant_id, project_id=project_id, section_id=section_id
    )
    if text is None:
        return {
            "available": False,
            "reason": meta.get("reason"),
            "source": meta,
            "chapters": [],
            "signals": {},
            "diagnostics": [],
        }

    outline = derive_directory(text)
    profile = get_template_profile(profile_id)
    chapters = map_nodes_to_chapters(outline.nodes, profile)

    mapped = sum(1 for c in chapters if not c["custom"])
    return {
        "available": True,
        "procurement_method": outline.procurement_method,
        "document_term": outline.document_term,
        "signals": outline.signals,
        "diagnostics": outline.diagnostics
        + [f"映射章节 {len(chapters)} 个（命中模板 {mapped}，自定义 {len(chapters) - mapped}）"],
        "chapters": chapters,
        "source": meta,
    }
