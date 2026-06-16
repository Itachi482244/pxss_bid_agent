from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BidSection,
    BusinessDraftChapter,
    DraftBlock,
    DraftContextPack,
    DraftCoverageReview,
    DraftFactCheck,
    EnterpriseMaterial,
    Project,
)
from app.services.context_pack import _material_applies_to_project, _project_facts
from app.services.tender_compliance_coverage import (
    CoverLayer,
    CoverStatus,
    CoverageItem,
    compute_coverage,
)
from app.services.tender_directory import derive_directory
from app.services.tender_format_assembler import build_form_facts, material_render_candidate_ids
from app.services.tender_format_export import (
    _material_confirmed_for_export,
    _response_item_snapshots,
    _source_image_refs,
)
from app.services.tender_format_templates import extract_format_templates
from app.services.tender_outline import load_tender_text, map_nodes_to_chapters
from app.services.tender_pricing import build_pricing_report
from app.services.template_profile import get_template_profile


_STATUS_RANK = {"pass": 0, "warn": 1, "block": 2}
_STATUS_LABEL = {"pass": "可继续", "warn": "需复核", "block": "阻断"}
_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}


def _worst_status(statuses: list[str]) -> str:
    return max(statuses or ["pass"], key=lambda status: _STATUS_RANK.get(status, 1))


def _check(
    *,
    code: str,
    title: str,
    status: str,
    message: str,
    category: str,
    count: int = 0,
    action_label: str | None = None,
    target: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "status": status,
        "message": message,
        "category": category,
        "count": count,
        "action_label": action_label,
        "target": target,
        "details": details or [],
    }


def _coverage_item_detail(item: CoverageItem) -> dict[str, Any]:
    return {
        "layer": item.layer.value,
        "title": item.title,
        "status": item.status.value,
        "status_label": item.status_label,
        "detail": item.detail,
        "disqualifying": item.disqualifying,
    }


def _format_coverage_check(items: list[CoverageItem], disqualifying: list[CoverageItem]) -> dict[str, Any]:
    if disqualifying:
        return _check(
            code="coverage.disqualifying_gaps",
            title="L1 合规格式",
            status="block",
            count=len(disqualifying),
            message=f"{len(disqualifying)} 项核心资格/废标项尚未满足",
            category="coverage",
            action_label="补齐资格材料",
            target="evidence",
            details=[_coverage_item_detail(item) for item in disqualifying[:8]],
        )
    gaps = [item for item in items if item.status in {CoverStatus.NEEDS_MATERIAL, CoverStatus.MISSING, CoverStatus.PARTIAL, CoverStatus.PENDING}]
    if gaps:
        by_layer: dict[str, int] = {}
        for item in gaps:
            by_layer[item.layer.value] = by_layer.get(item.layer.value, 0) + 1
        message = "；".join(f"{layer} {count} 项" for layer, count in by_layer.items())
        return _check(
            code="coverage.gaps",
            title="L1-L3 覆盖缺口",
            status="warn",
            count=len(gaps),
            message=f"仍有 {len(gaps)} 项待处理：{message}",
            category="coverage",
            action_label="查看缺口",
            target="chapter",
            details=[_coverage_item_detail(item) for item in gaps[:10]],
        )
    return _check(
        code="coverage.ready",
        title="L1-L3 覆盖",
        status="pass",
        message="合规格式、评分覆盖与偏离响应暂未发现阻断缺口",
        category="coverage",
    )


def _source_image_embeddable(material: EnterpriseMaterial) -> bool:
    return any(
        str(ref.get("content_type") or "").lower() in _IMAGE_CONTENT_TYPES
        and bool(ref.get("bucket"))
        and bool(ref.get("object_key"))
        for ref in _source_image_refs(material)
    )


def _material_embeddable_state(material: EnterpriseMaterial) -> tuple[bool, str]:
    if _source_image_embeddable(material):
        return True, "已有可嵌入来源页图片"
    if not material.bucket or not material.object_key:
        return False, "未上传可读取文件"
    content_type = (material.content_type or "").lower()
    filename = (material.file_name or "").lower()
    if content_type in _IMAGE_CONTENT_TYPES:
        return True, "原始文件为图片"
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return True, "原始 PDF 可渲染为图片"
    return False, f"暂不支持嵌入的文件类型：{material.content_type or material.file_name or 'unknown'}"


def _material_metadata_snapshots(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
) -> list[dict[str, Any]]:
    materials = db.scalars(
        select(EnterpriseMaterial)
        .where(EnterpriseMaterial.tenant_id == tenant_id)
        .order_by(EnterpriseMaterial.created_at.desc())
    ).all()
    snapshots: list[dict[str, Any]] = []
    for material in materials:
        if not _material_applies_to_project(material, project):
            continue
        if not _material_confirmed_for_export(material):
            continue
        embeddable, reason = _material_embeddable_state(material)
        snapshots.append(
            {
                "material_id": str(material.id),
                "material_name": material.name,
                "material_type": material.material_type,
                "verification_status": material.verification_status,
                "data_level": material.data_level,
                "certificate_no": material.certificate_no,
                "evidence_text": material.evidence_text,
                "file_name": material.file_name,
                "content_type": material.content_type,
                "bucket": material.bucket,
                "object_key": material.object_key,
                "selected_for_export": False,
                "embeddable": embeddable,
                "embed_status": "ready" if embeddable else "not_embeddable",
                "embed_reason": reason,
            }
        )
    return snapshots


def _pricing_check(pricing: Any) -> dict[str, Any]:
    issue_count = len(pricing.issues)
    has_hard_issue = pricing.budget_status == "over_budget" or any("不一致" in item for item in pricing.issues)
    if has_hard_issue:
        return _check(
            code="pricing.blocking_issues",
            title="L3 报价校验",
            status="block",
            count=issue_count,
            message="报价存在超预算或合价不一致等正式稿阻断问题",
            category="pricing",
            action_label="检查报价",
            target="chapter",
            details=[{"message": item} for item in pricing.issues[:8]],
        )
    if pricing.issues:
        return _check(
            code="pricing.pending",
            title="L3 报价校验",
            status="warn",
            count=issue_count,
            message="报价清单仍有待补字段或未识别项",
            category="pricing",
            action_label="补充报价",
            target="chapter",
            details=[{"message": item} for item in pricing.issues[:8]],
        )
    return _check(
        code="pricing.ready",
        title="L3 报价校验",
        status="pass",
        message="报价算术与预算校验暂未发现问题",
        category="pricing",
    )


def _latest_context_pack(db: Session, *, tenant_id: uuid.UUID, project_id: uuid.UUID, section_id: uuid.UUID) -> DraftContextPack | None:
    return db.scalar(
        select(DraftContextPack)
        .where(
            DraftContextPack.tenant_id == tenant_id,
            DraftContextPack.project_id == project_id,
            DraftContextPack.section_id == section_id,
            DraftContextPack.status != "superseded",
        )
        .order_by(DraftContextPack.created_at.desc())
    )


def _context_pack_check(context_pack: DraftContextPack | None) -> dict[str, Any]:
    if context_pack is None:
        return _check(
            code="context_pack.missing",
            title="投标素材包",
            status="warn",
            message="尚未确认投标素材包；正式稿前建议先确认生成输入",
            category="context_pack",
            action_label="生成投标素材包",
            target="chapter",
        )
    status = context_pack.readiness_status
    return _check(
        code=f"context_pack.{status}",
        title="投标素材包",
        status=status,
        message=f"最近投标素材包状态：{_STATUS_LABEL.get(status, status)}",
        category="context_pack",
        action_label="查看投标素材包" if status != "pass" else None,
        target="chapter" if status != "pass" else None,
        details=[
            check
            for check in (context_pack.readiness_json or {}).get("checks", [])
            if isinstance(check, dict) and check.get("status") in {"warn", "block"}
        ][:8],
    )


def _latest_coverage_review_check(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    review = db.scalar(
        select(DraftCoverageReview)
        .where(
            DraftCoverageReview.tenant_id == tenant_id,
            DraftCoverageReview.project_id == project_id,
            DraftCoverageReview.section_id == section_id,
        )
        .order_by(DraftCoverageReview.created_at.desc())
    )
    if review is None:
        return None, None
    if review.status == "pass":
        return (
            _check(
                code="draft_coverage.pass",
                title="草稿覆盖检查",
                status="pass",
                message="最近一次草稿覆盖检查通过",
                category="draft",
            ),
            {
                "status": review.status,
                "summary": review.summary_json,
                "issue_count": len(review.issues_json or []),
            },
        )
    return (
        _check(
            code=f"draft_coverage.{review.status}",
            title="草稿覆盖检查",
            status=review.status,
            count=len(review.issues_json or []),
            message="最近一次草稿覆盖检查仍有风险",
            category="draft",
            action_label="处理草稿覆盖",
            target="review",
            details=(review.issues_json or [])[:8],
        ),
        {
            "status": review.status,
            "summary": review.summary_json,
            "issue_count": len(review.issues_json or []),
        },
    )


def _draft_review_check(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blocks = db.scalars(
        select(DraftBlock).where(
            DraftBlock.tenant_id == tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
        )
    ).all()
    counts: dict[str, int] = {}
    for block in blocks:
        counts[block.review_status] = counts.get(block.review_status, 0) + 1
    unresolved = sum(count for status, count in counts.items() if status != "approved")
    blocking = counts.get("needs_evidence", 0) + counts.get("needs_fact", 0) + counts.get("rejected", 0)
    summary = {
        "block_count": len(blocks),
        "approved_count": counts.get("approved", 0),
        "unresolved_count": unresolved,
        "blocking_count": blocking,
        "status_counts": counts,
    }
    if not blocks:
        return (
            _check(
                code="draft_blocks.missing",
                title="草稿审阅",
                status="warn",
                message="尚未生成或审阅结构化草稿；正式稿前建议完成草稿审阅",
                category="draft",
                action_label="生成草稿",
                target="chapter",
            ),
            summary,
        )
    if blocking:
        return (
            _check(
                code="draft_blocks.blocking",
                title="草稿审阅",
                status="block",
                count=blocking,
                message=f"{blocking} 个草稿块仍缺事实/证据或已被退回",
                category="draft",
                action_label="处理草稿审阅",
                target="review",
                details=[{"status": status, "count": count} for status, count in sorted(counts.items()) if status != "approved"],
            ),
            summary,
        )
    if unresolved:
        return (
            _check(
                code="draft_blocks.pending",
                title="草稿审阅",
                status="warn",
                count=unresolved,
                message=f"{unresolved} 个草稿块尚未人工通过",
                category="draft",
                action_label="继续审阅",
                target="review",
            ),
            summary,
        )
    return (
        _check(
            code="draft_blocks.ready",
            title="草稿审阅",
            status="pass",
            message="结构化草稿已全部人工通过",
            category="draft",
        ),
        summary,
    )


def _fact_check(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> tuple[dict[str, Any], dict[str, Any]]:
    chapters = db.scalars(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.status != "superseded",
        )
    ).all()
    checks = db.scalars(
        select(DraftFactCheck).where(
            DraftFactCheck.tenant_id == tenant_id,
            DraftFactCheck.project_id == project_id,
            DraftFactCheck.section_id == section_id,
        )
    ).all()
    unverified = [item for item in checks if item.check_status == "unverified"]
    high_unverified = [item for item in unverified if item.risk_level == "high"]
    pending_chapters = [chapter for chapter in chapters if chapter.fact_check_status == "pending"]
    summary = {
        "chapter_count": len(chapters),
        "fact_check_count": len(checks),
        "unverified_count": len(unverified),
        "high_unverified_count": len(high_unverified),
        "pending_chapter_count": len(pending_chapters),
    }
    if high_unverified:
        return (
            _check(
                code="draft_facts.unverified_high",
                title="草稿事实校验",
                status="block",
                count=len(high_unverified),
                message=f"{len(high_unverified)} 个高风险事实未被证据支持",
                category="draft",
                action_label="重新事实校验",
                target="chapter",
                details=[
                    {
                        "fact_type": item.fact_type,
                        "fact_text": item.fact_text,
                        "detail": item.detail,
                    }
                    for item in high_unverified[:8]
                ],
            ),
            summary,
        )
    if unverified or pending_chapters or (chapters and not checks):
        return (
            _check(
                code="draft_facts.pending",
                title="草稿事实校验",
                status="warn",
                count=len(unverified) + len(pending_chapters),
                message="仍有草稿事实待核验或事实校验未执行",
                category="draft",
                action_label="执行事实校验",
                target="chapter",
            ),
            summary,
        )
    if not chapters:
        return (
            _check(
                code="draft_facts.no_draft",
                title="草稿事实校验",
                status="warn",
                message="尚未生成草稿，暂无法校验草稿事实",
                category="draft",
                action_label="生成草稿",
                target="chapter",
            ),
            summary,
        )
    return (
        _check(
            code="draft_facts.ready",
            title="草稿事实校验",
            status="pass",
            message="草稿事实校验暂未发现未支持事实",
            category="draft",
        ),
        summary,
    )


def _material_check(materials: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [item for item in materials if item.get("selected_for_export")]
    not_embeddable = [item for item in selected if not item.get("embeddable")]
    if not_embeddable:
        return _check(
            code="export_materials.not_embeddable",
            title="导出材料嵌入",
            status="warn",
            count=len(not_embeddable),
            message=f"{len(not_embeddable)} 项预计引用材料暂无可嵌入图片/PDF",
            category="export",
            action_label="检查材料文件",
            target="evidence",
            details=[
                {
                    "material_id": item.get("material_id"),
                    "material_name": item.get("material_name"),
                    "reason": item.get("embed_reason"),
                }
                for item in not_embeddable[:8]
            ],
        )
    if selected:
        return _check(
            code="export_materials.ready",
            title="导出材料嵌入",
            status="pass",
            count=len(selected),
            message=f"预计嵌入/引用 {len(selected)} 项已确认材料",
            category="export",
        )
    return _check(
        code="export_materials.none",
        title="导出材料嵌入",
        status="warn",
        message="本次未识别到可嵌入的证照/证明材料",
        category="export",
        action_label="检查材料绑定",
        target="evidence",
    )


def build_section_quality_summary(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    profile_id: str | None = None,
) -> dict[str, Any]:
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    if (
        project is None
        or section is None
        or project.tenant_id != tenant_id
        or section.tenant_id != tenant_id
        or section.project_id != project_id
    ):
        raise ValueError("项目或标段不存在")

    generated_at = datetime.now(UTC)
    checks: list[dict[str, Any]] = []
    text, source_meta = load_tender_text(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    if text is None:
        summary = "正式稿阻断：缺少可体检的招标正文"
        checks.append(
            _check(
                code="source.no_tender_text",
                title="招标正文",
                status="block",
                message=f"当前标段没有可体检的招标正文：{source_meta.get('reason')}",
                category="source",
                action_label="上传/解析招标文件",
                target="documents",
            )
        )
        status = "block"
        return {
            "project_id": project_id,
            "section_id": section_id,
            "status": status,
            "status_label": _STATUS_LABEL[status],
            "summary": summary,
            "generated_at": generated_at,
            "checks": checks,
            "suggested_actions": ["上传并解析招标文件"],
            "coverage_summary": {},
            "pricing_summary": {},
            "material_summary": {"selected_count": 0, "embeddable_count": 0, "materials": []},
            "export_preview": {
                "review_allowed": True,
                "submission_allowed": False,
                "submission_blocked_reason": summary,
                "export_modes": ["review", "submission"],
                "chapter_count": 0,
                "scoring_index_count": 0,
                "technical_response_count": 0,
                "placeholder_count": 0,
                "pageref_note": "评分索引页码由 Word/LibreOffice 分页引擎更新；无法定位项会保留待定位状态。",
            },
            "context_pack_status": None,
            "draft_summary": {},
            "source": source_meta,
        }

    outline = derive_directory(text)
    profile = get_template_profile(profile_id)
    chapters = map_nodes_to_chapters(outline.nodes, profile)
    if not chapters:
        checks.append(
            _check(
                code="directory.unavailable",
                title="响应文件目录",
                status="block",
                message="未能从招标文件推导出响应文件目录，无法判断格式标完整性",
                category="coverage",
                action_label="检查招标文件格式章",
                target="documents",
                details=[{"diagnostic": item} for item in outline.diagnostics[:6]],
            )
        )

    project_facts = _project_facts(db, tenant_id=tenant_id, project=project, section=section)
    form_facts = build_form_facts(project_facts, outline.signals)
    response_items = _response_item_snapshots(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    material_snapshots = _material_metadata_snapshots(db, tenant_id=tenant_id, project=project)
    selected_ids = material_render_candidate_ids(
        chapters,
        material_snapshots,
        compliance_items=response_items,
    )
    for snapshot in material_snapshots:
        snapshot["selected_for_export"] = str(snapshot["material_id"]) in selected_ids

    render_chapters = [*chapters]
    templates = extract_format_templates(text, [str(chapter.get("title") or "") for chapter in render_chapters])
    coverage = compute_coverage(
        text=text,
        templates=templates,
        chapters=render_chapters,
        facts=form_facts,
        available_materials=material_snapshots,
        compliance_items=response_items,
    )
    coverage_check = _format_coverage_check(coverage.items, coverage.disqualifying_gaps)
    checks.append(coverage_check)

    pricing = build_pricing_report(
        text=text,
        budget_amount=section.budget_amount or project.budget_amount,
    )
    checks.append(_pricing_check(pricing))

    context_pack = _latest_context_pack(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    checks.append(_context_pack_check(context_pack))

    coverage_review_check, coverage_review_summary = _latest_coverage_review_check(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    if coverage_review_check is not None:
        checks.append(coverage_review_check)

    draft_review_check, draft_review_summary = _draft_review_check(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    fact_check, fact_summary = _fact_check(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    checks.extend([draft_review_check, fact_check])
    checks.append(_material_check(material_snapshots))

    status = _worst_status([check["status"] for check in checks])
    block_count = sum(1 for check in checks if check["status"] == "block")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    if status == "block":
        summary = f"正式稿阻断：{block_count} 类硬风险，需处理后再导出正式版"
    elif status == "warn":
        summary = f"可生成审阅稿；仍有 {warn_count} 类事项建议复核"
    else:
        summary = "未发现提交前阻断，可继续审阅或导出"

    selected_materials = [item for item in material_snapshots if item.get("selected_for_export")]
    embeddable_selected = [item for item in selected_materials if item.get("embeddable")]
    suggested_actions = [
        str(check["action_label"])
        for check in checks
        if check.get("status") in {"warn", "block"} and check.get("action_label")
    ]

    return {
        "project_id": project_id,
        "section_id": section_id,
        "status": status,
        "status_label": _STATUS_LABEL.get(status, status),
        "summary": summary,
        "generated_at": generated_at,
        "checks": checks,
        "suggested_actions": list(dict.fromkeys(suggested_actions))[:6],
        "coverage_summary": {
            "summary": coverage.summary(),
            "gap_count": len(coverage.gaps),
            "disqualifying_gap_count": len(coverage.disqualifying_gaps),
            "l1_gap_count": len([item for item in coverage.gaps if item.layer == CoverLayer.L1_FORMAT]),
            "l2_gap_count": len([item for item in coverage.gaps if item.layer == CoverLayer.L2_SCORING]),
            "l3_gap_count": len([item for item in coverage.gaps if item.layer == CoverLayer.L3_RESPONSE]),
        },
        "pricing_summary": {
            "row_count": len(pricing.rows),
            "total_amount": str(pricing.total_amount) if pricing.total_amount is not None else None,
            "budget_amount": str(pricing.budget_amount) if pricing.budget_amount is not None else None,
            "budget_status": pricing.budget_status,
            "issue_count": len(pricing.issues),
            "issues": pricing.issues,
        },
        "material_summary": {
            "total_confirmed_allowed_count": len(material_snapshots),
            "selected_count": len(selected_materials),
            "embeddable_count": len(embeddable_selected),
            "not_embeddable_count": len(selected_materials) - len(embeddable_selected),
            "materials": selected_materials,
        },
        "export_preview": {
            "review_allowed": True,
            "submission_allowed": status != "block",
            "submission_blocked_reason": summary if status == "block" else None,
            "export_modes": ["review", "submission"],
            "chapter_count": len(chapters),
            "scoring_index_count": len([item for item in response_items if item.get("item_type") == "scoring"]),
            "technical_response_count": len([item for item in response_items if item.get("item_type") == "technical_response"]),
            "placeholder_count": len(coverage.gaps) + len(pricing.issues),
            "pageref_note": "评分索引页码由 Word/LibreOffice 分页引擎更新；无法定位项会保留待定位状态。",
        },
        "context_pack_status": {
            "id": str(context_pack.id) if context_pack else None,
            "status": context_pack.status if context_pack else None,
            "readiness_status": context_pack.readiness_status if context_pack else None,
        },
        "draft_summary": {
            "blocks": draft_review_summary,
            "facts": fact_summary,
            "coverage_review": coverage_review_summary,
        },
        "source": {
            "directory_source": source_meta,
            "procurement_method": outline.procurement_method,
            "document_term": outline.document_term,
            "signals": outline.signals,
        },
    }
