from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from docx import Document as WordDocument
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AuditLog,
    BidSection,
    BusinessDraftChapter,
    BusinessDraftEvidenceRef,
    ComplianceEvidenceBinding,
    ComplianceItem,
    DraftFactCheck,
    ExportFile,
    Project,
)
from app.services.llm_gateway import LLMGatewayError, chat_completion
from app.services.storage import put_object_bytes


class BusinessDraftError(Exception):
    pass


class LLMBusinessDraftResponse(BaseModel):
    content_text: str = Field(min_length=1)


def _item_type_label(value: str) -> str:
    return {
        "qualification": "资格要求",
        "mandatory_response": "强制响应",
        "format": "格式要求",
        "deadline": "截止时间",
        "scoring": "评分办法",
        "reference_info": "参考信息",
        "technical_response": "技术响应",
        "other": "其他",
    }.get(value, value)


def _risk_label(value: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value, value)


def _binding_snapshot(binding: ComplianceEvidenceBinding) -> dict[str, Any]:
    snapshot = binding.material_snapshot or {}
    return {
        "binding_id": str(binding.id),
        "enterprise_material_id": str(binding.enterprise_material_id),
        "material_name": snapshot.get("name"),
        "material_type": snapshot.get("material_type"),
        "verification_status": snapshot.get("verification_status"),
        "evidence_text": binding.evidence_text,
        "confidence_score": str(binding.confidence_score) if binding.confidence_score is not None else None,
    }


def _chapter_groups(items: list[ComplianceItem]) -> list[tuple[str, str, list[ComplianceItem]]]:
    qualification = [item for item in items if item.item_type == "qualification"]
    business = [
        item
        for item in items
        if item.item_type in {"mandatory_response", "deadline", "format", "scoring"}
    ]
    reference = [item for item in items if item.item_type in {"reference_info", "other"}]
    groups = [
        ("qualification_response", "资格响应", qualification),
        ("business_response", "商务响应与实质性条款", business),
        ("commitment", "承诺、偏离与参考事项", reference),
    ]
    return [(chapter_type, title, group_items) for chapter_type, title, group_items in groups if group_items]


def _build_chapter_content(
    *,
    title: str,
    items: list[ComplianceItem],
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
) -> tuple[str, list[dict[str, Any]]]:
    lines = [
        f"{title}",
        "本章节由系统基于当前合规矩阵和已绑定企业资料证据生成，需经人工复核后进入正式商务标版本。",
        "",
    ]
    refs: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        bindings = bindings_by_item.get(item.id, [])
        lines.append(f"{index}. 招标要求：{item.requirement_text}")
        response = item.response_suggestion or f"我方将按{_item_type_label(item.item_type)}要求进行响应。"
        lines.append(f"   响应草稿：{response}")
        if bindings:
            evidence_labels = []
            for binding in bindings:
                snapshot = _binding_snapshot(binding)
                material_name = snapshot.get("material_name") or "企业资料"
                evidence_labels.append(str(material_name))
                refs.append(
                    {
                        "compliance_item_id": str(item.id),
                        "evidence_binding_id": str(binding.id),
                        "enterprise_material_id": str(binding.enterprise_material_id),
                        "source_type": "enterprise_material",
                        "source_snapshot": snapshot,
                        "quote_text": binding.evidence_text,
                    }
                )
            lines.append(f"   企业证据：{'；'.join(evidence_labels)}。")
        else:
            refs.append(
                {
                    "compliance_item_id": str(item.id),
                    "evidence_binding_id": None,
                    "enterprise_material_id": None,
                    "source_type": "compliance_item",
                    "source_snapshot": {
                        "requirement_text": item.requirement_text,
                        "item_type": item.item_type,
                        "risk_level": item.risk_level,
                        "source_page_no": item.source_page_no,
                    },
                    "quote_text": item.evidence_text or item.requirement_text,
                }
            )
            lines.append("   企业证据：[请人工确认] 当前矩阵项尚未绑定企业资料证据。")
        lines.append(f"   风险等级：{_risk_label(item.risk_level)}。")
        lines.append("")
    return "\n".join(lines).strip(), refs


def _json_from_model_text(content: str) -> dict[str, Any]:
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()
    return json.loads(content)


def _chapter_prompt(
    *,
    project: Project,
    title: str,
    template_content: str,
    refs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    evidence_payload = [
        {
            "source_type": ref.get("source_type"),
            "quote_text": ref.get("quote_text"),
            "source_snapshot": ref.get("source_snapshot"),
        }
        for ref in refs[:80]
    ]
    return [
        {
            "role": "system",
            "content": (
                "你是商务标书草稿助手。只输出 JSON，不要输出解释。"
                "你只能基于输入的合规矩阵草稿和证据改写商务标章节，禁止编造项目名称、证书编号、人员、金额、日期。"
                "无法从证据确认的事实必须写成 [请人工确认]。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"项目名称：{project.name}\n"
                f"章节标题：{title}\n\n"
                "请将下面的模板草稿整理为可人工复核的商务标章节正文，保留逐项响应关系，"
                "语言可以更正式，但不得新增没有证据的事实。\n\n"
                "输出 JSON 格式：{\"content_text\":\"章节正文\"}\n\n"
                f"模板草稿：\n{template_content}\n\n"
                f"证据：\n{json.dumps(evidence_payload, ensure_ascii=False)}"
            ),
        },
    ]


def _generate_chapter_content_with_llm(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    title: str,
    template_content: str,
    refs: list[dict[str, Any]],
    item_count: int,
) -> tuple[str, str, uuid.UUID | None]:
    messages = _chapter_prompt(
        project=project,
        title=title,
        template_content=template_content,
        refs=refs,
    )
    try:
        result = chat_completion(
            db,
            tenant_id=tenant_id,
            project_id=project.id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            task_type="business_draft_generation",
            prompt_version="business-draft-chapter@2026-05-17",
            messages=messages,
            complexity="complex" if item_count >= 12 or len(template_content) >= 5000 else "simple",
            temperature=0.1,
            response_format={"type": "json_object"},
            evidence_refs={
                "compliance_item_ids": [
                    ref["compliance_item_id"]
                    for ref in refs
                    if ref.get("compliance_item_id")
                ],
                "evidence_binding_ids": [
                    ref["evidence_binding_id"]
                    for ref in refs
                    if ref.get("evidence_binding_id")
                ],
            },
        )
        parsed = LLMBusinessDraftResponse.model_validate(_json_from_model_text(result.content))
        return parsed.content_text.strip(), f"{result.provider}:{result.model_name}", result.log_id
    except (LLMGatewayError, ValidationError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return template_content, "template", None


def _evidence_corpus(db: Session, chapter: BusinessDraftChapter) -> str:
    refs = db.scalars(
        select(BusinessDraftEvidenceRef).where(
            BusinessDraftEvidenceRef.tenant_id == chapter.tenant_id,
            BusinessDraftEvidenceRef.chapter_id == chapter.id,
        )
    ).all()
    values: list[str] = []
    for ref in refs:
        values.append(ref.quote_text or "")
        values.append(str(ref.source_snapshot or ""))
    return "\n".join(values)


_PERSON_ROLE_PATTERN = re.compile(
    r"(?:项目经理|项目负责人|技术负责人|项目总工|总监理工程师|注册建造师|建造师|造价工程师|项目总监)"
    r"(?:拟派|拟任|为|由|是|：|:|，|,|\s)+"
    r"([\u4e00-\u9fa5]{2,4})"
)
_ID_CARD_PATTERN = re.compile(r"(?<![0-9])[0-9]{17}[0-9Xx](?![0-9])")
_BUILDER_CERT_PATTERN = re.compile(
    r"(?:建造师|证书|执业)\s*(?:编号|证号)[：:，,为是\s]*([A-Za-z0-9]{6,32})"
)
_PERFORMANCE_AMOUNT_PATTERN = re.compile(
    r"(?:合同金额|中标金额|合同额|工程造价|合同价)[：:，,\s]*(\d+(?:\.\d+)?\s*(?:万元|亿元|元))"
)
_PERFORMANCE_CONTRACT_PATTERN = re.compile(
    r"(?:业绩|类似工程|类似项目|合同名称|工程名称)[：:，,\s]*《([^》]{2,60})》"
)
_PERSON_NAME_STOPWORDS = {"我方", "详见", "见附", "拟派", "拟任", "暂定", "待定", "无", "略"}


def _personnel_fact_candidates(text: str) -> list[tuple[str, str]]:
    """Detect personnel facts (project manager / certified builder names + ids).

    MVP1.3 #7 requires personnel facts to be fact-checked. Names are only taken
    when they follow an explicit role keyword + separator so we do not flag
    arbitrary two-character phrases, and obvious filler words are dropped.
    """
    out: list[tuple[str, str]] = []
    for name in _PERSON_ROLE_PATTERN.findall(text):
        if name and name not in _PERSON_NAME_STOPWORDS:
            out.append(("person_name", name))
    for id_no in _ID_CARD_PATTERN.findall(text):
        out.append(("person_name", id_no))
    for cert_no in _BUILDER_CERT_PATTERN.findall(text):
        out.append(("certificate_no", cert_no))
    return out


def _performance_fact_candidates(text: str) -> list[tuple[str, str]]:
    """Detect performance facts (contract amounts and similar-project names).

    MVP1.3 #7 requires 业绩 (track-record) facts to be fact-checked so they are
    not fabricated. Contract amounts map to ``amount`` and contract/project names
    to ``other`` so they verify against bound evidence like any other fact.
    """
    out: list[tuple[str, str]] = []
    for amount in _PERFORMANCE_AMOUNT_PATTERN.findall(text):
        out.append(("amount", amount.strip()))
    for contract in _PERFORMANCE_CONTRACT_PATTERN.findall(text):
        out.append(("other", contract.strip()))
    return out


def recompose_chapter_text_from_blocks(db: Session, chapter: BusinessDraftChapter) -> str:
    """Rebuild a chapter's ``content_text`` from its current draft blocks.

    With MVP1.3 per-clause blocks a single block no longer represents the whole
    chapter, so editing one block must not overwrite the entire chapter body.
    We concatenate the chapter's blocks in sort order; the caller persists the
    result and re-runs fact checks on the recomposed text.
    """
    from app.models import DraftBlock

    blocks = db.scalars(
        select(DraftBlock)
        .where(
            DraftBlock.tenant_id == chapter.tenant_id,
            DraftBlock.chapter_id == chapter.id,
        )
        .order_by(DraftBlock.sort_order.asc(), DraftBlock.created_at.asc())
    ).all()
    segments = [block.content_text.strip() for block in blocks if block.content_text.strip()]
    if not segments:
        return chapter.content_text
    return "\n\n".join(segments)


def run_fact_checks(
    db: Session,
    *,
    chapter: BusinessDraftChapter,
    project: Project,
    actor_user_id: uuid.UUID,
) -> list[DraftFactCheck]:
    db.execute(
        delete(DraftFactCheck).where(
            DraftFactCheck.tenant_id == chapter.tenant_id,
            DraftFactCheck.chapter_id == chapter.id,
        )
    )
    corpus = _evidence_corpus(db, chapter)
    checks: list[DraftFactCheck] = []

    candidates: list[tuple[str, str]] = []
    if project.name in chapter.content_text:
        candidates.append(("project_name", project.name))
    for value in sorted(set(re.findall(r"[A-Z0-9]{8,32}", chapter.content_text))):
        candidates.append(("certificate_no", value))
    for value in sorted(set(re.findall(r"\d+(?:\.\d+)?\s*(?:万元|元|个月|天|日历日|年)", chapter.content_text))):
        candidates.append(("number", value))
    for value in sorted(set(re.findall(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}日?", chapter.content_text))):
        candidates.append(("date", value))
    candidates.extend(_personnel_fact_candidates(chapter.content_text))
    candidates.extend(_performance_fact_candidates(chapter.content_text))

    seen: set[tuple[str, str]] = set()
    for fact_type, fact_text in candidates:
        key = (fact_type, fact_text)
        if key in seen:
            continue
        seen.add(key)
        verified = fact_text in corpus or fact_type == "project_name"
        check = DraftFactCheck(
            tenant_id=chapter.tenant_id,
            project_id=chapter.project_id,
            section_id=chapter.section_id,
            chapter_id=chapter.id,
            fact_type=fact_type,
            fact_text=fact_text,
            check_status="verified" if verified else "unverified",
            risk_level="low" if verified else "high",
            evidence_text=fact_text if verified else None,
            detail="已在项目基础信息或绑定证据中找到一致事实。"
            if verified
            else "未在当前章节绑定证据中找到一致事实，正式使用前需人工确认。",
            created_by=actor_user_id,
        )
        db.add(check)
        checks.append(check)

    if not checks:
        check = DraftFactCheck(
            tenant_id=chapter.tenant_id,
            project_id=chapter.project_id,
            section_id=chapter.section_id,
            chapter_id=chapter.id,
            fact_type="other",
            fact_text="未发现需自动校验的关键事实",
            check_status="verified",
            risk_level="low",
            evidence_text=None,
            detail="当前章节没有识别到证书编号、金额、日期等高风险事实。",
            created_by=actor_user_id,
        )
        db.add(check)
        checks.append(check)

    unverified_values = [
        item.fact_text for item in checks if item.check_status == "unverified" and item.fact_text
    ]
    updated_content = chapter.content_text
    for value in unverified_values:
        updated_content = updated_content.replace(value, "[请人工确认]")
    if updated_content != chapter.content_text:
        chapter.content_text = updated_content
    chapter.fact_check_status = (
        "unverified" if any(item.check_status == "unverified" for item in checks) else "verified"
    )
    return checks


def generate_business_draft_chapters(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> list[BusinessDraftChapter]:
    project = db.get(Project, project_id)
    if project is None:
        raise BusinessDraftError("项目不存在")

    items = db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(ComplianceItem.item_type.asc(), ComplianceItem.risk_level.desc(), ComplianceItem.created_at.asc())
    ).all()
    if not items:
        raise BusinessDraftError("当前标段没有可生成草稿的合规矩阵项")

    bindings = db.scalars(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.status == "active",
        )
    ).all()
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]] = {}
    for binding in bindings:
        bindings_by_item.setdefault(binding.compliance_item_id, []).append(binding)

    existing = db.scalars(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.status != "superseded",
        )
    ).all()
    for chapter in existing:
        chapter.status = "superseded"

    chapters: list[BusinessDraftChapter] = []
    for sort_order, (chapter_type, title, group_items) in enumerate(_chapter_groups(items), start=1):
        template_content, refs = _build_chapter_content(
            title=title,
            items=group_items,
            bindings_by_item=bindings_by_item,
        )
        content_text, generator, invocation_log_id = _generate_chapter_content_with_llm(
            db,
            tenant_id=tenant_id,
            project=project,
            section_id=section_id,
            actor_user_id=actor_user_id,
            title=title,
            template_content=template_content,
            refs=refs,
            item_count=len(group_items),
        )
        chapter = BusinessDraftChapter(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            chapter_type=chapter_type,
            title=title,
            sort_order=sort_order,
            content_text=content_text,
            outline_json={"item_count": len(group_items), "item_types": sorted({item.item_type for item in group_items})},
            evidence_summary_json={
                "bound_evidence_count": sum(
                    len(bindings_by_item.get(item.id, [])) for item in group_items
                ),
                "unbound_item_count": sum(1 for item in group_items if not bindings_by_item.get(item.id)),
            },
            fact_check_status="pending",
            status="pending_review",
            version_no=1,
            generated_from_json={
                "compliance_item_ids": [str(item.id) for item in group_items],
                "generated_at": datetime.now(UTC).isoformat(),
                "generator": generator,
                "model_invocation_log_id": str(invocation_log_id) if invocation_log_id else None,
            },
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        db.add(chapter)
        db.flush()
        for ref in refs:
            db.add(
                BusinessDraftEvidenceRef(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    section_id=section_id,
                    chapter_id=chapter.id,
                    compliance_item_id=uuid.UUID(ref["compliance_item_id"])
                    if ref.get("compliance_item_id")
                    else None,
                    evidence_binding_id=uuid.UUID(ref["evidence_binding_id"])
                    if ref.get("evidence_binding_id")
                    else None,
                    enterprise_material_id=uuid.UUID(ref["enterprise_material_id"])
                    if ref.get("enterprise_material_id")
                    else None,
                    source_type=ref["source_type"],
                    source_snapshot=ref["source_snapshot"],
                    quote_text=ref.get("quote_text"),
                )
            )
        db.flush()
        run_fact_checks(db, chapter=chapter, project=project, actor_user_id=actor_user_id)
        chapters.append(chapter)

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="business_draft.generated",
            object_type="business_draft_chapter",
            object_id=None,
            after_json={"chapter_count": len(chapters), "chapter_ids": [str(chapter.id) for chapter in chapters]},
            reason="基于合规矩阵和企业证据生成商务标章节草稿",
            severity="info",
        )
    )
    return chapters


def export_business_draft_word(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    extra_snapshot: dict[str, object] | None = None,
) -> ExportFile:
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    chapters = db.scalars(
        select(BusinessDraftChapter)
        .where(
            BusinessDraftChapter.tenant_id == tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.status != "superseded",
        )
        .order_by(BusinessDraftChapter.sort_order.asc(), BusinessDraftChapter.created_at.asc())
    ).all()
    if not chapters:
        raise BusinessDraftError("尚无可导出的商务标章节草稿")

    document = WordDocument()
    document.add_heading(project.name if project else "商务标章节草稿", level=0)
    document.add_paragraph(f"标段：{section.name if section else '未识别标段'}")
    document.add_paragraph("说明：本文件为平台生成的商务标/资格响应草稿，需人工复核后使用。")
    for chapter in chapters:
        document.add_heading(chapter.title, level=1)
        for paragraph in chapter.content_text.splitlines():
            if paragraph.strip():
                document.add_paragraph(paragraph.strip())
        checks = db.scalars(
            select(DraftFactCheck).where(
                DraftFactCheck.tenant_id == tenant_id,
                DraftFactCheck.chapter_id == chapter.id,
            )
        ).all()
        document.add_paragraph("事实性校验：")
        for check in checks:
            document.add_paragraph(
                f"- {check.fact_text}：{check.check_status}，{check.detail}",
                style=None,
            )

    buffer = BytesIO()
    document.save(buffer)
    data = buffer.getvalue()
    content_hash = hashlib.sha256(data).hexdigest()
    export_id = uuid.uuid4()
    now = datetime.now(UTC)
    file_name = f"商务标章节草稿-{now.strftime('%Y%m%d%H%M%S')}.docx"
    object_key = (
        f"tenant/{tenant_id}/project/{project_id}/section/{section_id}/"
        f"exports/{export_id}/{file_name}"
    )
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    source_snapshot = {
        "chapter_ids": [str(chapter.id) for chapter in chapters],
        "chapter_count": len(chapters),
        "exported_at": now.isoformat(),
        "snapshot_note": "商务标章节草稿，需人工复核后使用",
    }
    if extra_snapshot:
        source_snapshot.update(extra_snapshot)

    export_file = ExportFile(
        id=export_id,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_id=None,
        export_type="business_draft_word",
        file_name=file_name,
        bucket=settings.minio_bucket,
        object_key=object_key,
        sha256=content_hash,
        filter_json=None,
        source_snapshot_json=source_snapshot,
        status="available",
        created_by=actor_user_id,
    )
    db.add(export_file)
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="business_draft.word_exported",
            object_type="export_file",
            object_id=export_file.id,
            after_json={"file_name": file_name, "sha256": content_hash, "source_snapshot": source_snapshot},
            reason="导出商务标章节草稿 Word 文件",
            severity="warning" if source_snapshot.get("preflight_status") == "block" else "info",
        )
    )
    return export_file
