from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ApprovalTask,
    BidSection,
    BusinessDraftChapter,
    ComplianceEvidenceBinding,
    ComplianceItem,
    Document,
    DocumentVersion,
    DraftBlock,
    DraftFactCheck,
    Project,
    QualificationDecision,
)
from app.schemas.project import PreflightCheckItem, PreflightCheckRead
from app.services.evidence_policy import requires_enterprise_evidence


@dataclass(frozen=True)
class Readiness:
    preflight: PreflightCheckRead
    blocking_items: list[PreflightCheckItem]
    can_confirm: bool
    can_generate: bool
    reasons: list[str]


def draft_block_review_summary(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> dict[str, int | list[str]]:
    blocks = db.scalars(
        select(DraftBlock).where(
            DraftBlock.tenant_id == tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
        )
    ).all()
    status_counts: dict[str, int] = {}
    for block in blocks:
        status_counts[block.review_status] = status_counts.get(block.review_status, 0) + 1
    unresolved_statuses = sorted(status for status in status_counts if status != "approved")
    return {
        "total": len(blocks),
        "approved": status_counts.get("approved", 0),
        "unresolved": sum(count for status, count in status_counts.items() if status != "approved"),
        "unresolved_statuses": unresolved_statuses,
        "needs_evidence": status_counts.get("needs_evidence", 0),
        "needs_fact": status_counts.get("needs_fact", 0),
        "rejected": status_counts.get("rejected", 0),
        "pending": status_counts.get("pending", 0) + status_counts.get("covered", 0),
    }


def build_preflight_check(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section: BidSection,
) -> PreflightCheckRead:
    documents = db.scalars(
        select(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.project_id == project.id,
            Document.section_id == section.id,
            Document.status != "deleted",
        )
        .order_by(Document.acquired_at.desc(), Document.created_at.desc())
    ).all()
    current_version_ids = {
        document.id: document.current_version_id
        for document in documents
        if document.current_version_id
    }
    current_versions = {
        version.id: version
        for version in db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.id.in_(list(current_version_ids.values()) or [uuid.uuid4()]),
            )
        ).all()
    }
    latest_document = next(
        (document for document in documents if document.doc_type == "tender"),
        documents[0] if documents else None,
    )
    latest_version = current_versions.get(latest_document.current_version_id) if latest_document else None

    items = db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == project.id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(ComplianceItem.created_at.asc())
    ).all()
    evidence_counts = {
        row.compliance_item_id: row.count
        for row in db.execute(
            select(
                ComplianceEvidenceBinding.compliance_item_id,
                func.count(ComplianceEvidenceBinding.id).label("count"),
            )
            .where(
                ComplianceEvidenceBinding.tenant_id == tenant_id,
                ComplianceEvidenceBinding.project_id == project.id,
                ComplianceEvidenceBinding.section_id == section.id,
                ComplianceEvidenceBinding.status == "active",
            )
            .group_by(ComplianceEvidenceBinding.compliance_item_id)
        ).all()
    }

    matrix_version_ids = sorted({item.source_version_id for item in items}, key=str)
    version_labels = {
        version.id: version.version_label
        for version in db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.id.in_(matrix_version_ids or [uuid.uuid4()]),
            )
        ).all()
    }
    outdated_items = [
        item
        for item in items
        if current_version_ids.get(item.source_document_id)
        and current_version_ids[item.source_document_id] != item.source_version_id
    ]
    unresolved_statuses = {"draft", "pending_confirm", "needs_material", "rejected"}
    pending_qualification_count = sum(
        1 for item in items if item.item_type == "qualification" and item.status in unresolved_statuses
    )
    qualification_decision = db.scalar(
        select(QualificationDecision)
        .where(
            QualificationDecision.tenant_id == tenant_id,
            QualificationDecision.project_id == project.id,
            QualificationDecision.section_id == section.id,
            QualificationDecision.status != "superseded",
        )
        .order_by(QualificationDecision.created_at.desc())
    )
    high_risk_unconfirmed_count = sum(
        1 for item in items if item.risk_level == "high" and item.status != "confirmed"
    )
    mandatory_missing_evidence_count = sum(
        1
        for item in items
        if item.is_mandatory
        and requires_enterprise_evidence(item)
        and evidence_counts.get(item.id, 0) == 0
    )
    missing_evidence_count = sum(
        1
        for item in items
        if requires_enterprise_evidence(item)
        and (item.is_mandatory or item.status == "needs_material")
        and evidence_counts.get(item.id, 0) == 0
    )
    technical_signals = ("技术", "设备", "参数", "验收", "净化", "洁净")
    technical_pending_count = sum(
        1
        for item in items
        if item.status != "confirmed"
        and (
            item.item_type in {"technical_response", "scoring"}
            or (item.item_type == "other" and any(signal in item.requirement_text for signal in technical_signals))
        )
    )

    chapters = db.scalars(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == tenant_id,
            BusinessDraftChapter.project_id == project.id,
            BusinessDraftChapter.section_id == section.id,
            BusinessDraftChapter.status != "superseded",
        )
    ).all()
    chapter_ids = [chapter.id for chapter in chapters]
    fact_checks = db.scalars(
        select(DraftFactCheck).where(
            DraftFactCheck.tenant_id == tenant_id,
            DraftFactCheck.chapter_id.in_(chapter_ids or [uuid.uuid4()]),
        )
    ).all()
    unverified_fact_count = sum(1 for check in fact_checks if check.check_status == "unverified")
    failed_fact_count = sum(1 for check in fact_checks if check.check_status == "warning")
    pending_fact_check_chapter_count = sum(
        1 for chapter in chapters if chapter.fact_check_status == "pending"
    )
    block_review = draft_block_review_summary(
        db,
        tenant_id=tenant_id,
        project_id=project.id,
        section_id=section.id,
    )

    approval_tasks = db.scalars(
        select(ApprovalTask).where(
            ApprovalTask.tenant_id == tenant_id,
            ApprovalTask.project_id == project.id,
            ApprovalTask.section_id == section.id,
        )
    ).all()
    pending_approval_count = sum(1 for task in approval_tasks if task.status == "pending")
    rejected_approval_count = sum(1 for task in approval_tasks if task.status == "rejected")

    has_deadline_item = any(item.item_type == "deadline" for item in items)
    missing_bid_deadline = not (section.bid_deadline_at or project.bid_deadline_at)
    missing_deadline_item = bool(items) and not has_deadline_item

    checks: list[PreflightCheckItem] = []

    def add_check(
        code: str,
        title: str,
        check_status: str,
        count: int,
        message: str,
        action_label: str | None = None,
        target: str | None = None,
    ) -> None:
        checks.append(
            PreflightCheckItem(
                code=code,
                title=title,
                status=check_status,
                count=count,
                message=message,
                action_label=action_label,
                target=target,
            )
        )

    add_check(
        "matrix_version",
        "矩阵版本",
        "block" if outdated_items else "pass",
        len(outdated_items),
        "矩阵已落后于最新解析版本，建议重新生成。" if outdated_items else "矩阵基于当前解析版本。",
        "重新生成矩阵" if outdated_items else None,
        "matrix",
    )
    add_check(
        "high_risk",
        "高风险项",
        "block" if high_risk_unconfirmed_count else "pass",
        high_risk_unconfirmed_count,
        f"还有 {high_risk_unconfirmed_count} 条高风险项未确认。" if high_risk_unconfirmed_count else "高风险项已处理。",
        "查看合规矩阵",
        "matrix",
    )
    add_check(
        "mandatory_evidence",
        "强制项证据",
        "block" if mandatory_missing_evidence_count else "pass",
        mandatory_missing_evidence_count,
        f"还有 {mandatory_missing_evidence_count} 条强制项缺少企业资料证据。"
        if mandatory_missing_evidence_count
        else "强制项证据已补齐。",
        "绑定企业资料",
        "evidence",
    )
    add_check(
        "draft_facts",
        "草稿事实",
        "block" if unverified_fact_count else "warn" if failed_fact_count or pending_fact_check_chapter_count else "pass",
        unverified_fact_count + failed_fact_count + pending_fact_check_chapter_count,
        "草稿中存在无法验证或待校验事实。"
        if unverified_fact_count or failed_fact_count or pending_fact_check_chapter_count
        else "草稿事实校验通过。",
        "查看商务草稿",
        "chapter",
    )
    if block_review["total"]:
        add_check(
            "draft_block_review",
            "结构化草稿审阅",
            "block" if block_review["unresolved"] else "pass",
            int(block_review["unresolved"]),
            f"还有 {block_review['unresolved']} 个结构化草稿 block 未人工通过。"
            if block_review["unresolved"]
            else "结构化草稿 block 已全部人工通过。",
            "审阅草稿 block",
            "chapter",
        )
    add_check(
        "qualification",
        "资格项确认",
        "warn" if pending_qualification_count else "pass",
        pending_qualification_count,
        f"还有 {pending_qualification_count} 条资格项待确认。" if pending_qualification_count else "资格项已确认。",
        "查看资格预评估",
        "qualification",
    )
    if qualification_decision is None:
        qualification_decision_status = "block"
        qualification_decision_message = "尚未生成参标建议，需先运行资格预评估并人工确认。"
        qualification_decision_action = "运行资格预评估"
        qualification_decision_count = 1
    elif qualification_decision.status != "confirmed":
        qualification_decision_status = "block"
        qualification_decision_message = "参标建议尚未人工确认，不能进入正式 ContextPack 和草稿生成。"
        qualification_decision_action = "确认参标建议"
        qualification_decision_count = 1
    elif qualification_decision.recommendation == "no_go":
        qualification_decision_status = "block"
        qualification_decision_message = "已确认的参标建议为 No-Go，只能在风险接受后生成内部草稿。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 1
    elif qualification_decision.recommendation == "conditional_go":
        qualification_decision_status = "warn"
        qualification_decision_message = "参标建议为有条件 Go，生成草稿和提交前仍需复核缺材料/待确认事项。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 1
    else:
        qualification_decision_status = "pass"
        qualification_decision_message = "参标建议已确认。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 0
    add_check(
        "qualification_decision",
        "参标建议",
        qualification_decision_status,
        qualification_decision_count,
        qualification_decision_message,
        qualification_decision_action,
        "qualification",
    )
    add_check(
        "technical",
        "技术响应",
        "warn" if technical_pending_count else "pass",
        technical_pending_count,
        f"还有 {technical_pending_count} 条技术/评分项待确认。" if technical_pending_count else "技术响应项无明显阻塞。",
        "查看技术响应",
        "technical",
    )
    add_check(
        "deadline",
        "关键日期",
        "warn" if missing_bid_deadline or missing_deadline_item else "pass",
        int(missing_bid_deadline) + int(missing_deadline_item),
        "项目截止时间或招标文件关键日期缺失，建议人工补充。"
        if missing_bid_deadline or missing_deadline_item
        else "关键日期已有记录。",
        "查看项目文件",
        "documents",
    )
    add_check(
        "approvals",
        "审批任务",
        "warn" if pending_approval_count or rejected_approval_count else "pass",
        pending_approval_count + rejected_approval_count,
        f"待处理审批 {pending_approval_count} 个，退回审批 {rejected_approval_count} 个。"
        if pending_approval_count or rejected_approval_count
        else "审批任务无阻塞。",
        "查看审批",
        "approval",
    )

    if not chapters:
        draft_message = "尚未生成商务/资格草稿。"
        draft_action = "生成草稿"
        draft_target = "chapter"
        if qualification_decision is None or qualification_decision.status != "confirmed":
            draft_message = "尚未完成资格预评估确认，先生成并确认参标建议后再生成草稿。"
            draft_action = "运行资格预评估"
            draft_target = "qualification"
        add_check(
            "draft_exists",
            "商务草稿",
            "warn",
            1,
            draft_message,
            draft_action,
            draft_target,
        )

    if any(item.status == "block" for item in checks):
        overall_status = "block"
        summary = "存在阻塞项，建议先处理版本、风险、证据或事实校验问题。"
    elif any(item.status == "warn" for item in checks):
        overall_status = "warn"
        summary = "主链路可继续推进，但仍有待确认事项需要人工复核。"
    else:
        overall_status = "pass"
        summary = "提交前核验通过，当前无明显阻塞项。"

    suggested_actions = [item.message for item in checks if item.status in {"block", "warn"}][:5]
    if not suggested_actions:
        suggested_actions = ["可进入审批、导出和归档流程。"]

    return PreflightCheckRead(
        project_id=project.id,
        section_id=section.id,
        status=overall_status,
        summary=summary,
        latest_document_version_id=latest_version.id if latest_version else None,
        latest_document_version_label=latest_version.version_label if latest_version else None,
        matrix_version_ids=matrix_version_ids,
        matrix_version_labels=[version_labels.get(version_id, str(version_id)) for version_id in matrix_version_ids],
        matrix_outdated=bool(outdated_items),
        outdated_item_count=len(outdated_items),
        pending_qualification_count=pending_qualification_count,
        high_risk_unconfirmed_count=high_risk_unconfirmed_count,
        mandatory_missing_evidence_count=mandatory_missing_evidence_count,
        technical_pending_count=technical_pending_count,
        missing_evidence_count=missing_evidence_count,
        unverified_fact_count=unverified_fact_count,
        failed_fact_count=failed_fact_count,
        pending_fact_check_chapter_count=pending_fact_check_chapter_count,
        pending_approval_count=pending_approval_count,
        rejected_approval_count=rejected_approval_count,
        missing_bid_deadline=missing_bid_deadline,
        missing_deadline_item=missing_deadline_item,
        checks=checks,
        suggested_actions=suggested_actions,
    )


def compute_section_readiness(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section: BidSection,
) -> Readiness:
    preflight = build_preflight_check(db, tenant_id=tenant_id, project=project, section=section)
    blocking_items = [item for item in preflight.checks if item.status == "block"]
    reasons = [item.message for item in blocking_items]
    can_confirm = not blocking_items
    can_generate = section.assist_stage in {"confirmed", "generated"} and can_confirm
    return Readiness(
        preflight=preflight,
        blocking_items=blocking_items,
        can_confirm=can_confirm,
        can_generate=can_generate,
        reasons=reasons,
    )
