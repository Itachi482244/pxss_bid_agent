from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AgentReviewItem,
    AsyncTask,
    AuditLog,
    BidSection,
    ComplianceEvidenceBinding,
    ComplianceItem,
    DraftBlock,
    EnterpriseMaterial,
    Project,
    QualificationDecision,
    QualificationEvaluation,
)
from app.services.agent.definitions import (
    AssistPlan,
    AssistStepDefinition,
    StepContext,
    base_step_context,
)
from app.services.agent.classifier import (
    EvidenceClassification,
    classify_compliance_item,
    classify_evidence_candidates,
    is_disqualifying_item,
)
from app.services.agent.policy import (
    DEFAULT_ACTION_POLICY,
    AgentActionPolicy,
    ReviewTier,
    confirmation_requires_source_verified as policy_confirmation_requires_source_verified,
    is_technical_item as policy_is_technical_item,
    matrix_confidence as policy_matrix_confidence,
    matrix_escalation_reasons as policy_matrix_escalation_reasons,
    severity_for_compliance_item,
)
from app.services.agent.progress import ProgressReporter, budget_display_payload
from app.services.evidence_policy import (
    enterprise_evidence_not_required,
    enterprise_evidence_not_required_reason,
    requires_enterprise_evidence,
)
from app.services.material_identity import enterprise_material_identity_key, material_snapshot_identity_key
from app.services.material_retrieval import search_material_hits
from app.services.qualification_evaluation import (
    evaluation_snapshot,
    qualification_evaluation_result_snapshot,
    refresh_qualification_after_evidence_change,
    run_qualification_evaluation,
)


AGENT_ASSIST_TASK_TYPE = "agent_assist"
AUTO_PASS_CONFIDENCE = Decimal("0.8800")
DEFAULT_BIND_CONFIDENCE = Decimal("0.7500")
MAX_EVIDENCE_SUGGESTIONS_PER_ITEM = 2


class AgentAssistError(Exception):
    def __init__(self, message: str, *, code: str = "AGENT_ASSIST_ERROR") -> None:
        super().__init__(message)
        self.code = code


def _decimal(value: Decimal | float | int | None, default: Decimal) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.0001"))
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _short_text(text: str | None, limit: int = 90) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def compliance_item_candidate_query(item: ComplianceItem, project: Project, section: BidSection) -> str:
    values = [
        item.requirement_text,
        item.normalized_requirement,
        item.evidence_text,
        item.response_suggestion,
        item.item_type,
        project.region_code,
        project.industry_code,
        section.name,
    ]
    seen: set[str] = set()
    parts: list[str] = []
    for value in values:
        if not value:
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n".join(parts)


def compliance_item_snapshot(item: ComplianceItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "item_type": item.item_type,
        "requirement_text": item.requirement_text,
        "status": item.status,
        "risk_level": item.risk_level,
        "is_mandatory": item.is_mandatory,
        "confidence_score": str(item.confidence_score) if item.confidence_score is not None else None,
        "source_document_id": str(item.source_document_id),
        "source_version_id": str(item.source_version_id),
        "source_chunk_id": str(item.source_chunk_id) if item.source_chunk_id else None,
        "source_page_no": item.source_page_no,
        "explanation_json": item.explanation_json,
    }


def enterprise_material_snapshot(material: EnterpriseMaterial) -> dict[str, Any]:
    return {
        "id": str(material.id),
        "material_type": material.material_type,
        "name": material.name,
        "issuing_authority": material.issuing_authority,
        "certificate_no": material.certificate_no,
        "holder_name": material.holder_name,
        "project_name": material.project_name,
        "amount": material.amount,
        "valid_from": material.valid_from.isoformat() if material.valid_from else None,
        "valid_until": material.valid_until.isoformat() if material.valid_until else None,
        "data_level": material.data_level,
        "verification_status": material.verification_status,
        "structured_fields": material.structured_fields,
        "evidence_text": material.evidence_text,
        "file_name": material.file_name,
        "sha256": material.sha256,
    }


def evidence_binding_snapshot(binding: ComplianceEvidenceBinding) -> dict[str, Any]:
    return {
        "id": str(binding.id),
        "compliance_item_id": str(binding.compliance_item_id),
        "enterprise_material_id": str(binding.enterprise_material_id),
        "material_name": binding.material_snapshot.get("name"),
        "evidence_text": binding.evidence_text,
        "confidence_score": str(binding.confidence_score) if binding.confidence_score is not None else None,
        "bind_reason": binding.bind_reason,
        "status": binding.status,
        "created_by": str(binding.created_by),
    }


def _bind_material_to_item(
    db: Session,
    *,
    item: ComplianceItem,
    material: EnterpriseMaterial,
    actor_user_id: uuid.UUID,
    reason: str,
    evidence_text: str,
    confidence_score: Decimal,
    review_item_id: uuid.UUID | None = None,
    audit_action: str = "agent.evidence_bound",
) -> ComplianceEvidenceBinding:
    if material.verification_status in {"draft", "pending_confirm", "conflict", "expired", "missing_evidence"}:
        raise AgentAssistError("未确认、冲突、过期或缺原始佐证的资料不能绑定为响应证据", code="MATERIAL_NOT_BINDABLE")
    if material.data_level in {"restricted", "confidential"}:
        raise AgentAssistError("受限或机密资料不能直接绑定为响应证据", code="MATERIAL_DATA_LEVEL_BLOCKED")

    active_bindings = list(
        db.scalars(
            select(ComplianceEvidenceBinding).where(
                ComplianceEvidenceBinding.tenant_id == item.tenant_id,
                ComplianceEvidenceBinding.compliance_item_id == item.id,
                ComplianceEvidenceBinding.status == "active",
            )
        ).all()
    )
    material_key = enterprise_material_identity_key(material)
    if any(
        binding.enterprise_material_id == material.id
        or material_snapshot_identity_key(binding.material_snapshot) == material_key
        for binding in active_bindings
    ):
        raise AgentAssistError("等价资料已绑定", code="EQUIVALENT_MATERIAL_ALREADY_BOUND")

    before = {
        "item": compliance_item_snapshot(item),
        "active_evidence_count": len(active_bindings),
    }
    binding = ComplianceEvidenceBinding(
        tenant_id=item.tenant_id,
        project_id=item.project_id,
        section_id=item.section_id,
        compliance_item_id=item.id,
        enterprise_material_id=material.id,
        evidence_text=evidence_text,
        material_snapshot=enterprise_material_snapshot(material),
        confidence_score=confidence_score,
        bind_reason=reason,
        status="active",
        created_by=actor_user_id,
    )
    db.add(binding)
    if enterprise_evidence_not_required(item):
        explanation = dict(item.explanation_json or {})
        explanation["enterprise_evidence_not_required"] = False
        explanation["enterprise_evidence_not_required_cleared_at"] = datetime.now(UTC).isoformat()
        explanation["enterprise_evidence_not_required_cleared_by"] = str(actor_user_id)
        item.explanation_json = explanation
    if item.status == "needs_material":
        now = datetime.now(UTC)
        item.status = "pending_confirm"
        item.modified_by = actor_user_id
        item.modified_at = now
        item.modify_reason = reason
        _refresh_batch_confirm_guard(item)
    db.flush()
    qualification_refresh = None
    if item.item_type == "qualification":
        qualification_refresh = refresh_qualification_after_evidence_change(
            db,
            tenant_id=item.tenant_id,
            project_id=item.project_id,
            section_id=item.section_id,
            actor_user_id=actor_user_id,
        )
    _add_user_audit(
        db,
        tenant_id=item.tenant_id,
        project_id=item.project_id,
        section_id=item.section_id,
        actor_user_id=actor_user_id,
        action=audit_action,
        object_type="compliance_evidence_binding",
        object_id=binding.id,
        before_json=before,
        after_json={
            "binding": evidence_binding_snapshot(binding),
            "material": enterprise_material_snapshot(material),
            "review_item_id": str(review_item_id) if review_item_id else None,
            "qualification_refresh": qualification_refresh,
        },
        reason=reason,
    )
    return binding


def _item_source_ref(item: ComplianceItem) -> dict[str, Any]:
    return {
        "source_document_id": str(item.source_document_id),
        "source_version_id": str(item.source_version_id),
        "source_chunk_id": str(item.source_chunk_id) if item.source_chunk_id else None,
        "source_page_no": item.source_page_no,
        "source_quote": (item.explanation_json or {}).get("source_quote"),
    }


def _material_source_ref(hit) -> dict[str, Any]:
    chunk = hit.chunk
    return {
        "enterprise_material_id": str(hit.material.id),
        "enterprise_material_chunk_id": str(chunk.id) if chunk is not None else None,
        "chunk_index": chunk.chunk_index if chunk is not None else None,
        "snippet": hit.snippet,
        "metadata": chunk.metadata_json if chunk is not None else None,
        "confidence_score": round(float(hit.confidence_score), 4),
        "base_score": round(float(hit.base_score), 4) if hit.base_score is not None else None,
        "rerank_score": round(float(hit.rerank_score), 4) if hit.rerank_score is not None else None,
    }


def _active_evidence_counts(db: Session, tenant_id: uuid.UUID, item_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not item_ids:
        return {}
    rows = db.execute(
        select(
            ComplianceEvidenceBinding.compliance_item_id,
            func.count(ComplianceEvidenceBinding.id),
        )
        .where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.compliance_item_id.in_(item_ids),
            ComplianceEvidenceBinding.status == "active",
        )
        .group_by(ComplianceEvidenceBinding.compliance_item_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _matrix_confidence(item: ComplianceItem, evidence_count: int) -> Decimal:
    return policy_matrix_confidence(item, evidence_count)


def _is_technical_item(item: ComplianceItem) -> bool:
    return policy_is_technical_item(item)


def _matrix_escalation_reasons(item: ComplianceItem, evidence_count: int) -> list[str]:
    return policy_matrix_escalation_reasons(item, evidence_count)


def _severity_for_item(item: ComplianceItem, reasons: list[str]) -> str:
    return severity_for_compliance_item(item, reasons)


def _add_agent_audit(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    after_json: dict[str, Any] | None,
    reason: str,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="agent",
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_json=None,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def _add_user_audit(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    reason: str,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def _supersede_previous_open_items(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    steps: list[str],
) -> int:
    if not steps:
        return 0
    items = list(
        db.scalars(
            select(AgentReviewItem).where(
                AgentReviewItem.tenant_id == tenant_id,
                AgentReviewItem.project_id == project_id,
                AgentReviewItem.section_id == section_id,
                AgentReviewItem.step.in_(steps),
                AgentReviewItem.status.in_(["open", "auto_passed"]),
            )
        ).all()
    )
    for item in items:
        item.status = "superseded"
        item.decision_reason = "新一轮 Agent 推进已生成更新结果"
        item.decided_at = datetime.now(UTC)
    return len(items)


def _review_item(
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    run_key: str,
    async_task_id: uuid.UUID | None,
    triggered_by: uuid.UUID,
    step: str,
    action: str,
    status: str,
    severity: str,
    title: str,
    detail: str | None,
    object_type: str,
    object_id: uuid.UUID | None,
    confidence_score: Decimal | None,
    requires_human: bool,
    escalation_reasons: list[str] | None = None,
    recommendation_json: dict[str, Any] | None = None,
    source_ref_json: dict[str, Any] | None = None,
    compliance_item_id: uuid.UUID | None = None,
    enterprise_material_id: uuid.UUID | None = None,
    qualification_evaluation_id: uuid.UUID | None = None,
    qualification_decision_id: uuid.UUID | None = None,
    draft_block_id: uuid.UUID | None = None,
    tier: ReviewTier | None = None,
    is_disqualifying: bool = False,
    conclusion_changed: bool = False,
    auto_applied: bool = False,
) -> AgentReviewItem:
    return AgentReviewItem(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        async_task_id=async_task_id,
        run_key=run_key,
        step=step,
        action=action,
        status=status,
        severity=severity,
        tier=tier,
        is_disqualifying=is_disqualifying,
        conclusion_changed=conclusion_changed,
        auto_applied=auto_applied,
        title=title,
        detail=detail,
        object_type=object_type,
        object_id=object_id,
        compliance_item_id=compliance_item_id,
        enterprise_material_id=enterprise_material_id,
        qualification_evaluation_id=qualification_evaluation_id,
        qualification_decision_id=qualification_decision_id,
        draft_block_id=draft_block_id,
        confidence_score=confidence_score,
        requires_human=requires_human,
        escalation_reasons=escalation_reasons,
        recommendation_json=budget_display_payload(recommendation_json)
        if recommendation_json is not None
        else None,
        source_ref_json=source_ref_json,
        triggered_by=triggered_by,
    )


def _build_qualification_decision(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    evaluations: list[QualificationEvaluation],
) -> tuple[QualificationDecision | None, bool]:
    if not evaluations:
        return None, False
    existing = list(
        db.scalars(
            select(QualificationDecision).where(
                QualificationDecision.tenant_id == tenant_id,
                QualificationDecision.project_id == project_id,
                QualificationDecision.section_id == section_id,
                QualificationDecision.status != "superseded",
            )
        ).all()
    )
    confirmed = next((decision for decision in existing if decision.status == "confirmed"), None)
    if confirmed is not None:
        for decision in existing:
            if decision.status == "draft":
                decision.status = "superseded"
        return confirmed, True

    for decision in existing:
        decision.status = "superseded"

    satisfied = [item for item in evaluations if item.evaluation_status == "satisfied"]
    blocking = [item for item in evaluations if item.is_blocking or item.evaluation_status == "not_satisfied"]
    missing = [item for item in evaluations if item.evaluation_status == "needs_material"]
    pending = [item for item in evaluations if item.evaluation_status == "pending_confirm"]
    if blocking:
        recommendation = "no_go"
        summary = f"存在 {len(blocking)} 项阻断性资格风险，必须人工复核后再决策。"
    elif missing or pending:
        recommendation = "conditional_go"
        summary = f"存在 {len(missing)} 项缺材料、{len(pending)} 项待确认，建议有条件推进并补齐。"
    else:
        recommendation = "go"
        summary = "资格预评估未发现阻断项，可进入后续草稿和提交前审查。"

    decision = QualificationDecision(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        recommendation=recommendation,
        status="draft",
        summary=summary,
        satisfied_count=len(satisfied),
        blocking_count=len(blocking),
        missing_count=len(missing),
        pending_count=len(pending),
        reasons_json={
            "blocking": [evaluation_snapshot(item) for item in blocking[:20]],
            "missing": [evaluation_snapshot(item) for item in missing[:20]],
            "pending": [evaluation_snapshot(item) for item in pending[:20]],
            "generated_by": "agent_assist",
        },
        created_by=actor_user_id,
    )
    db.add(decision)
    db.flush()
    return decision, False


def _add_matrix_review_items(
    db: Session,
    *,
    project: Project,
    section: BidSection,
    items: list[ComplianceItem],
    evidence_counts: dict[uuid.UUID, int],
    run_key: str,
    async_task_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    policy: AgentActionPolicy = DEFAULT_ACTION_POLICY,
    auto_pass_confidence: Decimal = AUTO_PASS_CONFIDENCE,
    preaccepted_evidence_item_ids: set[uuid.UUID] | None = None,
) -> list[AgentReviewItem]:
    review_items: list[AgentReviewItem] = []
    if preaccepted_evidence_item_ids is None:
        preaccepted_evidence_item_ids = set()
    for item in items:
        evidence_count = evidence_counts.get(item.id, 0)
        has_preaccepted_evidence = item.id in preaccepted_evidence_item_ids
        if has_preaccepted_evidence and evidence_count == 0:
            evidence_classification = EvidenceClassification(
                outcome="pre_accept_candidate",
                tier="pre_accepted",
                reasons=["已有预采纳证据候选，确认锁定时生效"],
            )
        else:
            evidence_classification = classify_evidence_candidates(
                item,
                has_active_binding=evidence_count > 0,
            )
        classification = classify_compliance_item(
            item,
            evidence=evidence_classification,
            auto_pass_confidence=auto_pass_confidence,
        )
        effective_evidence_count = 1 if has_preaccepted_evidence else evidence_count
        reasons = policy.matrix_escalation_reasons(item, effective_evidence_count)
        if has_preaccepted_evidence:
            reasons = [reason for reason in reasons if reason != "当前标记为缺材料"]
        if classification.tier == "blocking" and not reasons:
            reasons = classification.reasons
        confidence = policy.matrix_confidence(item, effective_evidence_count)
        severity = policy.severity_for_compliance_item(item, reasons)
        if reasons:
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="matrix_review",
                    action="confirm_matrix_item",
                    status="open",
                    severity=severity,
                    title=f"审阅条款：{_short_text(item.requirement_text)}",
                    detail="；".join(reasons),
                    object_type="compliance_item",
                    object_id=item.id,
                    compliance_item_id=item.id,
                    confidence_score=confidence,
                    requires_human=policy.requires_human("confirm_matrix_item", item),
                    escalation_reasons=reasons,
                    tier="blocking",
                    is_disqualifying=classification.is_disqualifying,
                    recommendation_json={
                        "agent_recommendation": "人工确认后再进入下游",
                        "tier_reasons": classification.reasons,
                        "evidence_outcome": classification.evidence_outcome,
                        "item": compliance_item_snapshot(item),
                    },
                    source_ref_json=_item_source_ref(item),
                )
            )
        elif classification.tier == "silent":
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="matrix_review",
                    action="agent_matrix_low_risk_pass",
                    status="auto_passed",
                    severity="low",
                    title=f"低风险自动核验：{_short_text(item.requirement_text)}",
                    detail="来源明确、非强制非高风险，Agent 仅记录低风险通过，不写入人工确认状态。",
                    object_type="compliance_item",
                    object_id=item.id,
                    compliance_item_id=item.id,
                    confidence_score=confidence,
                    requires_human=policy.requires_human("agent_matrix_low_risk_pass", item),
                    escalation_reasons=None,
                    tier="silent",
                    is_disqualifying=False,
                    auto_applied=True,
                    recommendation_json={
                        "agent_recommendation": "低风险自动核验通过",
                        "business_effect": "不改变 compliance_item.status",
                        "tier_reasons": classification.reasons,
                        "evidence_outcome": classification.evidence_outcome,
                        "item": compliance_item_snapshot(item),
                    },
                    source_ref_json=_item_source_ref(item),
                )
            )
        elif classification.tier == "pre_accepted":
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="matrix_review",
                    action="pre_accept_matrix_item",
                    status="open",
                    severity="low",
                    title=f"预采纳条款：{_short_text(item.requirement_text)}",
                    detail="低风险条款已形成默认采纳草稿，确认锁定时生效；可在最终确认页撤销。",
                    object_type="compliance_item",
                    object_id=item.id,
                    compliance_item_id=item.id,
                    confidence_score=confidence,
                    requires_human=False,
                    escalation_reasons=classification.reasons,
                    tier="pre_accepted",
                    is_disqualifying=False,
                    auto_applied=False,
                    recommendation_json={
                        "agent_recommendation": "默认预采纳，确认锁定时视为通过",
                        "business_effect": "confirm_lock_applies",
                        "tier_reasons": classification.reasons,
                        "evidence_outcome": classification.evidence_outcome,
                        "item": compliance_item_snapshot(item),
                    },
                    source_ref_json=_item_source_ref(item),
                )
            )
    db.add_all(review_items)
    return review_items


def _add_evidence_review_items(
    db: Session,
    *,
    project: Project,
    section: BidSection,
    items: list[ComplianceItem],
    evidence_counts: dict[uuid.UUID, int],
    run_key: str,
    async_task_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    policy: AgentActionPolicy = DEFAULT_ACTION_POLICY,
    preaccepted_evidence_item_ids: set[uuid.UUID] | None = None,
) -> list[AgentReviewItem]:
    review_items: list[AgentReviewItem] = []
    if preaccepted_evidence_item_ids is None:
        preaccepted_evidence_item_ids = set()
    for item in items:
        if evidence_counts.get(item.id, 0) > 0 or not requires_enterprise_evidence(item):
            continue
        query = compliance_item_candidate_query(item, project, section)
        hits = search_material_hits(
            db,
            tenant_id=item.tenant_id,
            query=query,
            verification_statuses={"confirmed"},
            allowed_data_levels={"public", "internal"},
            limit=MAX_EVIDENCE_SUGGESTIONS_PER_ITEM,
        )
        evidence_classification = classify_evidence_candidates(
            item,
            has_active_binding=False,
            candidates=hits,
        )
        selected_hit = evidence_classification.selected_candidate
        if not hits or (evidence_classification.tier == "blocking" and selected_hit is None):
            severity = policy.severity_for_compliance_item(item, ["缺少企业资料证据"])
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="evidence_binding",
                    action="missing_evidence",
                    status="open",
                    severity=severity,
                    title=f"缺少证据：{_short_text(item.requirement_text)}",
                    detail="Agent 未在已确认企业资料中找到可绑定证据，需要补资料或人工标记无需证据。",
                    object_type="compliance_item",
                    object_id=item.id,
                    compliance_item_id=item.id,
                    confidence_score=Decimal("0.0000"),
                    requires_human=policy.requires_human("missing_evidence", item),
                    escalation_reasons=["缺少企业资料证据", "检索无可用候选"],
                    tier="blocking",
                    is_disqualifying=is_disqualifying_item(item),
                    recommendation_json={
                        "agent_recommendation": "补充企业资料或人工标记无需证据",
                        "evidence_not_required_reason": enterprise_evidence_not_required_reason(item),
                        "evidence_outcome": evidence_classification.outcome,
                    },
                    source_ref_json=_item_source_ref(item),
                )
            )
            continue
        if evidence_classification.tier == "silent" and selected_hit is not None:
            hit = selected_hit
            material = hit.material
            confidence = _decimal(hit.confidence_score, DEFAULT_BIND_CONFIDENCE)
            reason = hit.recommend_reason or "低风险要求存在唯一强匹配证据，Agent 静默绑定。"
            evidence_text = hit.snippet or material.evidence_text or material.name
            binding = _bind_material_to_item(
                db,
                item=item,
                material=material,
                actor_user_id=actor_user_id,
                reason=reason,
                evidence_text=evidence_text,
                confidence_score=confidence,
                audit_action="agent.evidence_silent_bound",
            )
            evidence_counts[item.id] = evidence_counts.get(item.id, 0) + 1
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="evidence_binding",
                    action="agent_evidence_silent_bound",
                    status="auto_passed",
                    severity="low",
                    title=f"已自动绑定：{material.name}",
                    detail="低风险要求存在唯一强匹配证据，已在推进时即时绑定。",
                    object_type="compliance_evidence_binding",
                    object_id=binding.id,
                    compliance_item_id=item.id,
                    enterprise_material_id=material.id,
                    confidence_score=confidence,
                    requires_human=False,
                    escalation_reasons=None,
                    tier="silent",
                    is_disqualifying=False,
                    auto_applied=True,
                    recommendation_json={
                        "agent_recommendation": "唯一强匹配证据已自动绑定",
                        "business_effect": "created_active_evidence_binding",
                        "binding": evidence_binding_snapshot(binding),
                        "compliance_item": compliance_item_snapshot(item),
                        "material_snapshot": enterprise_material_snapshot(material),
                        "evidence_text": evidence_text,
                        "reason": reason,
                        "evidence_outcome": evidence_classification.outcome,
                        "top1": str(evidence_classification.top1) if evidence_classification.top1 is not None else None,
                        "top2": str(evidence_classification.top2) if evidence_classification.top2 is not None else None,
                        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    },
                    source_ref_json=_material_source_ref(hit),
                )
            )
            continue
        if evidence_classification.tier == "pre_accepted" and selected_hit is not None:
            hit = selected_hit
            material = hit.material
            confidence = _decimal(hit.confidence_score, DEFAULT_BIND_CONFIDENCE)
            reason = hit.recommend_reason or "明显最优但非唯一证据候选，默认预采纳。"
            evidence_text = hit.snippet or material.evidence_text or material.name
            preaccepted_evidence_item_ids.add(item.id)
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="evidence_binding",
                    action="pre_accept_evidence_binding",
                    status="open",
                    severity="low",
                    title=f"预采纳证据：{material.name}",
                    detail="证据候选明显最优但非唯一，确认锁定时才会正式绑定；可在最终确认页撤销。",
                    object_type="enterprise_material",
                    object_id=material.id,
                    compliance_item_id=item.id,
                    enterprise_material_id=material.id,
                    confidence_score=confidence,
                    requires_human=False,
                    escalation_reasons=evidence_classification.reasons,
                    tier="pre_accepted",
                    is_disqualifying=False,
                    auto_applied=False,
                    recommendation_json={
                        "candidate_rank": 1,
                        "agent_recommendation": "默认预采纳，确认锁定时绑定为响应证据",
                        "business_effect": "confirm_lock_creates_active_evidence_binding",
                        "compliance_item": compliance_item_snapshot(item),
                        "material_snapshot": enterprise_material_snapshot(material),
                        "evidence_text": evidence_text,
                        "reason": reason,
                        "evidence_outcome": evidence_classification.outcome,
                        "top1": str(evidence_classification.top1) if evidence_classification.top1 is not None else None,
                        "top2": str(evidence_classification.top2) if evidence_classification.top2 is not None else None,
                        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    },
                    source_ref_json=_material_source_ref(hit),
                )
            )
            continue
        for rank, hit in enumerate(hits, start=1):
            material = hit.material
            confidence = _decimal(hit.confidence_score, DEFAULT_BIND_CONFIDENCE)
            reason = hit.recommend_reason or "与当前要求存在语义匹配，需人工核对后采纳。"
            evidence_text = hit.snippet or material.evidence_text or material.name
            evidence_reasons = evidence_classification.reasons or ["证据绑定需人工采纳后生效"]
            severity = policy.severity_for_compliance_item(item, evidence_reasons)
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="evidence_binding",
                    action="accept_evidence_binding",
                    status="open",
                    severity=severity,
                    title=f"建议绑定：{material.name}",
                    detail=f"{reason}。采纳后才会正式绑定到条款。",
                    object_type="enterprise_material",
                    object_id=material.id,
                    compliance_item_id=item.id,
                    enterprise_material_id=material.id,
                    confidence_score=confidence,
                    requires_human=policy.requires_human("accept_evidence_binding", material),
                    escalation_reasons=evidence_reasons,
                    tier="blocking",
                    is_disqualifying=is_disqualifying_item(item),
                    recommendation_json={
                        "candidate_rank": rank,
                        "agent_recommendation": "建议人工核对后绑定为响应证据",
                        "compliance_item": compliance_item_snapshot(item),
                        "material_snapshot": enterprise_material_snapshot(material),
                        "evidence_text": evidence_text,
                        "reason": reason,
                        "evidence_outcome": evidence_classification.outcome,
                        "top1": str(evidence_classification.top1) if evidence_classification.top1 is not None else None,
                        "top2": str(evidence_classification.top2) if evidence_classification.top2 is not None else None,
                        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    },
                    source_ref_json=_material_source_ref(hit),
                )
            )
    db.add_all(review_items)
    return review_items


def _add_qualification_technical_review_items(
    db: Session,
    *,
    project: Project,
    section: BidSection,
    items: list[ComplianceItem],
    run_key: str,
    async_task_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    policy: AgentActionPolicy = DEFAULT_ACTION_POLICY,
    qualification_item_ids: set[uuid.UUID] | None = None,
    include_technical_items: bool = True,
    include_draft_blocks: bool = True,
) -> list[AgentReviewItem]:
    review_items: list[AgentReviewItem] = []
    qualification_items = [item for item in items if item.item_type == "qualification"]
    evaluations: list[QualificationEvaluation] = []
    decision: QualificationDecision | None = None
    decision_preserved = False
    if qualification_items:
        evaluations = run_qualification_evaluation(
            db,
            tenant_id=project.tenant_id,
            project_id=project.id,
            section_id=section.id,
            actor_user_id=actor_user_id,
        )
        db.flush()
        decision, decision_preserved = _build_qualification_decision(
            db,
            tenant_id=project.tenant_id,
            project_id=project.id,
            section_id=section.id,
            actor_user_id=actor_user_id,
            evaluations=evaluations,
        )
        for evaluation in evaluations:
            if qualification_item_ids is not None and evaluation.compliance_item_id not in qualification_item_ids:
                continue
            confirmation_stale = bool(getattr(evaluation, "_confirmation_stale", False))
            if confirmation_stale:
                review_items.append(
                    _review_item(
                        tenant_id=evaluation.tenant_id,
                        project_id=evaluation.project_id,
                        section_id=evaluation.section_id,
                        run_key=run_key,
                        async_task_id=async_task_id,
                        triggered_by=actor_user_id,
                        step="qualification_technical",
                        action="review_qualification_evaluation",
                        status="open",
                        severity=policy.qualification_evaluation_severity(evaluation),
                        title=f"资格预评估结论已变化：{_short_text(evaluation.requirement_text)}",
                        detail="该资格评估项已有人工确认，但本轮评估结论发生变化，请复核后重新确认。",
                        object_type="qualification_evaluation",
                        object_id=evaluation.id,
                        compliance_item_id=evaluation.compliance_item_id,
                        qualification_evaluation_id=evaluation.id,
                        confidence_score=Decimal("0.5000"),
                        requires_human=True,
                        escalation_reasons=["已确认资格评估的底层结论发生变化"],
                        tier="blocking",
                        is_disqualifying=True,
                        conclusion_changed=True,
                        recommendation_json={
                            "business_effect": "preserve_confirmation_and_request_review",
                            "previous_evaluation": getattr(
                                evaluation,
                                "_previous_evaluation_snapshot",
                                None,
                            ),
                            "current_evaluation": evaluation_snapshot(evaluation),
                        },
                        source_ref_json={
                            "matched_material_id": str(evaluation.matched_material_id)
                            if evaluation.matched_material_id
                            else None
                        },
                    )
                )
                continue
            if evaluation.confirmed_by is not None:
                review_items.append(
                    _review_item(
                        tenant_id=evaluation.tenant_id,
                        project_id=evaluation.project_id,
                        section_id=evaluation.section_id,
                        run_key=run_key,
                        async_task_id=async_task_id,
                        triggered_by=actor_user_id,
                        step="qualification_technical",
                        action="qualification_evaluation_preserved",
                        status="auto_passed",
                        severity="low",
                        title=f"资格预评估已确认：{_short_text(evaluation.requirement_text)}",
                        detail="该资格评估项已有人工确认且本轮评估结果未变化，Agent 未重新打开待办。",
                        object_type="qualification_evaluation",
                        object_id=evaluation.id,
                        compliance_item_id=evaluation.compliance_item_id,
                        qualification_evaluation_id=evaluation.id,
                        confidence_score=Decimal("1.0000"),
                        requires_human=policy.requires_human(
                            "qualification_evaluation_preserved",
                            evaluation,
                        ),
                        escalation_reasons=None,
                        tier="silent",
                        is_disqualifying=False,
                        auto_applied=True,
                        recommendation_json={
                            "business_effect": "preserved_confirmed_evaluation",
                            "evaluation": evaluation_snapshot(evaluation),
                        },
                        source_ref_json={
                            "matched_material_id": str(evaluation.matched_material_id)
                            if evaluation.matched_material_id
                            else None
                        },
                    )
                )
                continue
            requires_human = policy.requires_human("review_qualification_evaluation", evaluation)
            status = "open" if requires_human else "auto_passed"
            severity = policy.qualification_evaluation_severity(evaluation)
            review_items.append(
                _review_item(
                    tenant_id=evaluation.tenant_id,
                    project_id=evaluation.project_id,
                    section_id=evaluation.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="qualification_technical",
                    action="review_qualification_evaluation",
                    status=status,
                    severity=severity,
                    title=f"资格预评估：{_short_text(evaluation.requirement_text)}",
                    detail=evaluation.reason,
                    object_type="qualification_evaluation",
                    object_id=evaluation.id,
                    compliance_item_id=evaluation.compliance_item_id,
                    qualification_evaluation_id=evaluation.id,
                    confidence_score=Decimal("0.9000") if not requires_human else Decimal("0.6200"),
                    requires_human=requires_human,
                    escalation_reasons=["资格项影响参标结论"] if requires_human else None,
                    tier="blocking" if requires_human else "silent",
                    is_disqualifying=requires_human,
                    auto_applied=not requires_human,
                    recommendation_json=evaluation_snapshot(evaluation),
                    source_ref_json={"matched_material_id": str(evaluation.matched_material_id) if evaluation.matched_material_id else None},
                )
            )
        if decision is not None:
            if decision_preserved:
                review_items.append(
                    _review_item(
                        tenant_id=decision.tenant_id,
                        project_id=decision.project_id,
                        section_id=decision.section_id,
                        run_key=run_key,
                        async_task_id=async_task_id,
                        triggered_by=actor_user_id,
                        step="qualification_technical",
                        action="qualification_decision_preserved",
                        status="auto_passed",
                        severity="low",
                        title="参标资格建议已人工确认",
                        detail="已存在人工确认的 Go/No-Go 结论，本轮 Agent 未重建或覆盖。",
                        object_type="qualification_decision",
                        object_id=decision.id,
                        qualification_decision_id=decision.id,
                        confidence_score=Decimal("1.0000"),
                        requires_human=policy.requires_human(
                            "qualification_decision_preserved",
                            decision,
                        ),
                        escalation_reasons=None,
                        tier="silent",
                        is_disqualifying=False,
                        auto_applied=True,
                        recommendation_json={
                            "business_effect": "preserved_confirmed_decision",
                            "recommendation": decision.recommendation,
                            "summary": decision.summary,
                            "status": decision.status,
                            "confirmed_by": str(decision.confirmed_by) if decision.confirmed_by else None,
                            "confirmed_at": decision.confirmed_at.isoformat() if decision.confirmed_at else None,
                        },
                        source_ref_json=None,
                    )
                )
                decision = None
            else:
                review_items.append(
                    _review_item(
                        tenant_id=decision.tenant_id,
                        project_id=decision.project_id,
                        section_id=decision.section_id,
                        run_key=run_key,
                        async_task_id=async_task_id,
                        triggered_by=actor_user_id,
                        step="qualification_technical",
                        action="confirm_qualification_decision",
                        status="open",
                        severity="critical" if decision.recommendation == "no_go" else "high",
                        title="确认参标资格建议",
                        detail=decision.summary,
                        object_type="qualification_decision",
                        object_id=decision.id,
                        qualification_decision_id=decision.id,
                        confidence_score=Decimal("0.7000"),
                        requires_human=policy.requires_human(
                            "confirm_qualification_decision",
                            decision,
                        ),
                        escalation_reasons=["Go/No-Go 参标建议必须人工确认"],
                        tier="blocking",
                        is_disqualifying=True,
                        recommendation_json={
                            "recommendation": decision.recommendation,
                            "summary": decision.summary,
                            "satisfied_count": decision.satisfied_count,
                            "blocking_count": decision.blocking_count,
                            "missing_count": decision.missing_count,
                            "pending_count": decision.pending_count,
                            "reasons_json": decision.reasons_json,
                        },
                        source_ref_json=None,
                    )
                )

    if include_technical_items:
        for item in items:
            if not _is_technical_item(item) or item.status == "confirmed":
                continue
            review_items.append(
                _review_item(
                    tenant_id=item.tenant_id,
                    project_id=item.project_id,
                    section_id=item.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="qualification_technical",
                    action="review_technical_response",
                    status="open",
                    severity="high" if item.risk_level == "high" else "medium",
                    title=f"技术/评分待确认：{_short_text(item.requirement_text)}",
                    detail="技术响应、评分点或设备参数不能由 Agent 自动形成最终承诺。",
                    object_type="compliance_item",
                    object_id=item.id,
                    compliance_item_id=item.id,
                    confidence_score=_matrix_confidence(item, 0),
                    requires_human=policy.requires_human("review_technical_response", item),
                    escalation_reasons=["技术/评分项需要人工确认"],
                    tier="blocking",
                    is_disqualifying=is_disqualifying_item(item),
                    recommendation_json={"agent_recommendation": "转交业务/技术人员确认响应策略"},
                    source_ref_json=_item_source_ref(item),
                )
            )

    if include_draft_blocks:
        draft_blocks = list(
            db.scalars(
                select(DraftBlock).where(
                    DraftBlock.tenant_id == project.tenant_id,
                    DraftBlock.project_id == project.id,
                    DraftBlock.section_id == section.id,
                    DraftBlock.review_status.in_(["pending", "needs_evidence", "needs_fact", "needs_confirm"]),
                )
            ).all()
        )
        for block in draft_blocks:
            review_items.append(
                _review_item(
                    tenant_id=block.tenant_id,
                    project_id=block.project_id,
                    section_id=block.section_id,
                    run_key=run_key,
                    async_task_id=async_task_id,
                    triggered_by=actor_user_id,
                    step="qualification_technical",
                    action="review_draft_block",
                    status="open",
                    severity="high" if block.review_status in {"needs_evidence", "needs_fact"} else "medium",
                    title=f"草稿 block 待审：{_short_text(block.content_text)}",
                    detail=f"当前审阅状态：{block.review_status}",
                    object_type="draft_block",
                    object_id=block.id,
                    draft_block_id=block.id,
                    confidence_score=Decimal("0.5000"),
                    requires_human=policy.requires_human("review_draft_block", block),
                    escalation_reasons=["生成式草稿内容必须人工审阅"],
                    tier="blocking",
                    is_disqualifying=block.review_status in {"needs_evidence", "needs_fact"},
                    recommendation_json={
                        "review_status": block.review_status,
                        "links_json": block.links_json,
                        "risk_flags_json": block.risk_flags_json,
                    },
                    source_ref_json=block.links_json,
                )
            )
    db.add_all(review_items)
    return review_items


def agent_assist_summary_from_items(
    *,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    run_key: str,
    task_id: uuid.UUID | None,
    items: list[AgentReviewItem],
) -> dict[str, Any]:
    status_counts = Counter(item.status for item in items)
    severity_counts = Counter(item.severity for item in items)
    step_counts = Counter(item.step for item in items)
    tier_counts = Counter(item.tier or ("silent" if item.status == "auto_passed" else "blocking") for item in items)
    open_action_counts = Counter(item.action for item in items if item.status == "open")
    suggested_actions: list[str] = []
    if open_action_counts["confirm_matrix_item"]:
        suggested_actions.append(f"先处理 {open_action_counts['confirm_matrix_item']} 条条款例外")
    if open_action_counts["accept_evidence_binding"] or open_action_counts["missing_evidence"]:
        suggested_actions.append(
            f"核对 {open_action_counts['accept_evidence_binding']} 条证据建议，补齐 {open_action_counts['missing_evidence']} 条缺证据"
        )
    if open_action_counts["confirm_qualification_decision"]:
        suggested_actions.append("人工确认 Go/No-Go 参标建议")
    if open_action_counts["review_technical_response"]:
        suggested_actions.append(f"转交确认 {open_action_counts['review_technical_response']} 条技术/评分项")
    llm_advice_count = open_action_counts["ack_llm_technical_advice"] + open_action_counts["ack_llm_draft_advice"]
    if llm_advice_count:
        suggested_actions.append(f"查看 {llm_advice_count} 条 LLM 只读建议")
    if not suggested_actions:
        suggested_actions.append("当前没有需要人工拍板的 Agent 例外项")
    return {
        "project_id": str(project_id),
        "section_id": str(section_id),
        "task_id": str(task_id) if task_id else None,
        "run_key": run_key,
        "total_count": len(items),
        "open_count": status_counts["open"],
        "auto_passed_count": status_counts["auto_passed"],
        "critical_count": severity_counts["critical"],
        "high_count": severity_counts["high"],
        "medium_count": severity_counts["medium"],
        "low_count": severity_counts["low"],
        "blocking_count": tier_counts["blocking"],
        "pre_accepted_count": tier_counts["pre_accepted"],
        "silent_count": tier_counts["silent"],
        "matrix_review_count": step_counts["matrix_review"],
        "evidence_binding_count": step_counts["evidence_binding"],
        "qualification_technical_count": step_counts["qualification_technical"],
        "missing_evidence_count": open_action_counts["missing_evidence"],
        "qualification_decision_count": open_action_counts["confirm_qualification_decision"],
        "technical_review_count": open_action_counts["review_technical_response"],
        "llm_advice_count": llm_advice_count,
        "suggested_actions": suggested_actions,
    }


_summary_from_items = agent_assist_summary_from_items


def _run_matrix_review_step(ctx: StepContext) -> list[AgentReviewItem]:
    return _add_matrix_review_items(
        ctx.db,
        project=ctx.project,
        section=ctx.section,
        items=ctx.items,
        evidence_counts=ctx.evidence_counts,
        preaccepted_evidence_item_ids=ctx.preaccepted_evidence_item_ids,
        run_key=ctx.run_key,
        async_task_id=ctx.async_task_id,
        actor_user_id=ctx.actor_user_id,
        policy=ctx.policy,
        auto_pass_confidence=ctx.auto_pass_confidence,
    )


def _run_evidence_binding_step(ctx: StepContext) -> list[AgentReviewItem]:
    return _add_evidence_review_items(
        ctx.db,
        project=ctx.project,
        section=ctx.section,
        items=ctx.items,
        evidence_counts=ctx.evidence_counts,
        preaccepted_evidence_item_ids=ctx.preaccepted_evidence_item_ids,
        run_key=ctx.run_key,
        async_task_id=ctx.async_task_id,
        actor_user_id=ctx.actor_user_id,
        policy=ctx.policy,
    )


def _run_qualification_technical_step(ctx: StepContext) -> list[AgentReviewItem]:
    return _add_qualification_technical_review_items(
        ctx.db,
        project=ctx.project,
        section=ctx.section,
        items=ctx.items,
        run_key=ctx.run_key,
        async_task_id=ctx.async_task_id,
        actor_user_id=ctx.actor_user_id,
        policy=ctx.policy,
    )


def default_assist_plan() -> AssistPlan:
    return AssistPlan(
        steps=(
            AssistStepDefinition(
                step="evidence_binding",
                when_to_use="缺证据暴露与候选证据建议",
                runner=_run_evidence_binding_step,
                progress_start=20,
                progress_end=45,
            ),
            AssistStepDefinition(
                step="matrix_review",
                when_to_use="条款例外审阅与低风险自动核验",
                runner=_run_matrix_review_step,
                progress_start=45,
                progress_end=70,
                auto_pass_confidence=AUTO_PASS_CONFIDENCE,
            ),
            AssistStepDefinition(
                step="qualification_technical",
                when_to_use="资格/技术/草稿人工拍板项",
                runner=_run_qualification_technical_step,
                progress_start=70,
                progress_end=90,
            ),
        )
    )


def execute_agent_assist_task(db: Session, task_id: uuid.UUID | str) -> dict[str, Any]:
    task_uuid = uuid.UUID(str(task_id))
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != AGENT_ASSIST_TASK_TYPE:
        raise AgentAssistError("Agent 推进任务不存在", code="TASK_NOT_FOUND")
    if task.project_id is None or task.section_id is None:
        raise AgentAssistError("Agent 推进任务缺少项目或标段", code="TASK_CONTEXT_MISSING")

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    reporter = ProgressReporter(db, task)
    reporter.report(percent=5, step=None, activity="Agent 推进任务已开始", commit=True)
    run_key = str((task.input_json or {}).get("run_key") or f"assist-{task.id}")
    previous_assist_stage: str | None = None

    try:
        project = db.get(Project, task.project_id)
        section = db.get(BidSection, task.section_id)
        if project is None or section is None:
            raise AgentAssistError("项目或标段不存在", code="PROJECT_OR_SECTION_NOT_FOUND")
        previous_assist_stage = section.assist_stage
        if section.assist_stage in {"confirmed", "generated"}:
            raise AgentAssistError(
                "标段已确认或已生成，重新推进前请先撤回确认。",
                code="SECTION_ASSIST_LOCKED",
            )
        section.assist_stage = "advancing"
        reporter.report(percent=8, step="advancing", activity="标段已进入 Agent 推进中", commit=True)

        requested_steps = (task.input_json or {}).get("steps")
        requested_step_names = requested_steps if isinstance(requested_steps, list) else None
        plan = default_assist_plan()
        enabled_steps = plan.enabled_steps(requested_step_names)
        if not enabled_steps:
            raise AgentAssistError("Agent 推进任务没有可执行步骤", code="ASSIST_PLAN_EMPTY")
        enabled_step_names = [step.step for step in enabled_steps]

        reporter.report(percent=10, step="load_context", activity="加载项目、标段和历史待办")
        superseded_count = _supersede_previous_open_items(
            db,
            tenant_id=task.tenant_id,
            project_id=project.id,
            section_id=section.id,
            steps=enabled_step_names,
        )
        items = list(
            db.scalars(
                select(ComplianceItem)
                .where(
                    ComplianceItem.tenant_id == task.tenant_id,
                    ComplianceItem.project_id == project.id,
                    ComplianceItem.section_id == section.id,
                    ComplianceItem.deleted_at.is_(None),
                )
                .order_by(ComplianceItem.risk_level.desc(), ComplianceItem.created_at.asc())
            ).all()
        )
        evidence_counts = _active_evidence_counts(db, task.tenant_id, [item.id for item in items])

        reporter.report(
            percent=15,
            step="load_context",
            activity=f"已加载 {len(items)} 条合规条款，准备执行 {len(enabled_steps)} 个步骤",
            current=0,
            total=len(enabled_steps),
        )
        created_items: list[AgentReviewItem] = []
        base_ctx = base_step_context(
            db=db,
            project=project,
            section=section,
            items=items,
            evidence_counts=evidence_counts,
            run_key=run_key,
            async_task_id=task.id,
            actor_user_id=task.created_by,
            reporter=reporter,
            policy=DEFAULT_ACTION_POLICY,
        )
        for index, step in enumerate(enabled_steps, start=1):
            reporter.report(
                percent=step.progress_start,
                step=step.step,
                activity=step.when_to_use,
                current=index - 1,
                total=len(enabled_steps),
            )
            step_items = step.runner(base_ctx.for_step(step))
            created_items.extend(step_items)
            db.flush()
            reporter.report(
                percent=step.progress_end,
                step=step.step,
                activity=f"{step.when_to_use}完成，新增 {len(step_items)} 条待办/记录",
                current=index,
                total=len(enabled_steps),
            )

        summary = _summary_from_items(
            project_id=project.id,
            section_id=section.id,
            run_key=run_key,
            task_id=task.id,
            items=created_items,
        )
        summary["superseded_previous_count"] = superseded_count
        _add_agent_audit(
            db,
            tenant_id=task.tenant_id,
            project_id=project.id,
            section_id=section.id,
            actor_user_id=task.created_by,
            action="agent.assist_finished",
            object_type="async_task",
            object_id=task.id,
            after_json=summary,
            reason="Agent 完成 4/5/6 步半自主推进，产出例外式审阅清单",
            severity="warning" if summary["open_count"] else "info",
        )
        section.assist_stage = "awaiting_confirm"
        task.status = "succeeded"
        final_progress = reporter.report(
            percent=100,
            step="finished",
            activity="Agent 推进完成",
            current=len(enabled_steps),
            total=len(enabled_steps),
        )
        summary["progress"] = final_progress
        task.output_json = summary
        task.finished_at = datetime.now(UTC)
        db.commit()
        return summary
    except Exception as exc:
        db.rollback()
        failed_at = datetime.now(UTC)
        code = getattr(exc, "code", "AGENT_ASSIST_FAILED")
        task = db.get(AsyncTask, task_uuid) or task
        failed_section = db.get(BidSection, task.section_id) if task.section_id else None
        if failed_section is not None and previous_assist_stage is not None:
            failed_section.assist_stage = previous_assist_stage
        task.status = "failed"
        task.progress = 100
        task.error_code = code
        task.error_message = str(exc)
        task.output_json = {
            **(task.output_json or {}),
            "status": "failed",
            "progress": {
                "percent": 100,
                "step": "failed",
                "activity": "Agent 推进失败，业务产物已回滚",
                "updated_at": failed_at.isoformat(),
            },
        }
        task.finished_at = failed_at
        db.commit()
        return {"status": "failed", "error_code": code, "error_message": str(exc)}


def _load_open_review_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    review_item_id: uuid.UUID,
) -> AgentReviewItem:
    item = db.scalar(
        select(AgentReviewItem).where(
            AgentReviewItem.tenant_id == tenant_id,
            AgentReviewItem.project_id == project_id,
            AgentReviewItem.section_id == section_id,
            AgentReviewItem.id == review_item_id,
        )
    )
    if item is None:
        raise AgentAssistError("Agent 待拍板项不存在", code="REVIEW_ITEM_NOT_FOUND")
    if item.status != "open":
        raise AgentAssistError("只有 open 状态的待拍板项可以处理", code="REVIEW_ITEM_NOT_OPEN")
    return item


def _load_review_item_compliance_item(
    db: Session,
    review_item: AgentReviewItem,
) -> ComplianceItem:
    if review_item.compliance_item_id is None:
        raise AgentAssistError(
            "该 Agent 待办没有关联条款，不能执行补救型处理",
            code="REVIEW_ITEM_COMPLIANCE_ITEM_REQUIRED",
        )
    item = db.get(ComplianceItem, review_item.compliance_item_id)
    if item is None or item.tenant_id != review_item.tenant_id:
        raise AgentAssistError("待处理条款不存在", code="COMPLIANCE_ITEM_NOT_FOUND")
    return item


def _mark_review_item_accepted(
    review_item: AgentReviewItem,
    *,
    actor_user_id: uuid.UUID,
    reason: str,
) -> None:
    review_item.status = "accepted"
    if review_item.tier == "pre_accepted":
        review_item.auto_applied = True
    review_item.decided_by = actor_user_id
    review_item.decided_at = datetime.now(UTC)
    review_item.decision_reason = reason


def _rerun_steps_for_compliance_item(item: ComplianceItem) -> list[str]:
    steps = ["evidence_binding", "matrix_review"]
    if item.item_type == "qualification":
        steps.append("qualification_technical")
    return steps


def _supersede_open_items_for_compliance_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    compliance_item_id: uuid.UUID,
    steps: list[str],
    reason: str,
    exclude_review_item_id: uuid.UUID | None = None,
) -> int:
    if not steps:
        return 0
    now = datetime.now(UTC)
    stmt = select(AgentReviewItem).where(
        AgentReviewItem.tenant_id == tenant_id,
        AgentReviewItem.project_id == project_id,
        AgentReviewItem.section_id == section_id,
        AgentReviewItem.compliance_item_id == compliance_item_id,
        AgentReviewItem.step.in_(steps),
        AgentReviewItem.status.in_(["open", "auto_passed"]),
    )
    if exclude_review_item_id is not None:
        stmt = stmt.where(AgentReviewItem.id != exclude_review_item_id)
    related_items = list(db.scalars(stmt).all())
    for item in related_items:
        item.status = "superseded"
        item.decision_reason = reason
        item.decided_at = now
    return len(related_items)


def _supersede_open_qualification_decision_items(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    reason: str,
) -> int:
    now = datetime.now(UTC)
    decision_items = list(
        db.scalars(
            select(AgentReviewItem).where(
                AgentReviewItem.tenant_id == tenant_id,
                AgentReviewItem.project_id == project_id,
                AgentReviewItem.section_id == section_id,
                AgentReviewItem.step == "qualification_technical",
                AgentReviewItem.qualification_decision_id.is_not(None),
                AgentReviewItem.status.in_(["open", "auto_passed"]),
            )
        ).all()
    )
    for item in decision_items:
        item.status = "superseded"
        item.decision_reason = reason
        item.decided_at = now
    return len(decision_items)


def _rerun_review_for_compliance_item(
    db: Session,
    *,
    project: Project,
    section: BidSection,
    item: ComplianceItem,
    run_key: str,
    actor_user_id: uuid.UUID,
) -> list[AgentReviewItem]:
    evidence_counts = _active_evidence_counts(db, project.tenant_id, [item.id])
    preaccepted_evidence_item_ids: set[uuid.UUID] = set()
    created_items = _add_evidence_review_items(
        db,
        project=project,
        section=section,
        items=[item],
        evidence_counts=evidence_counts,
        preaccepted_evidence_item_ids=preaccepted_evidence_item_ids,
        run_key=run_key,
        async_task_id=None,
        actor_user_id=actor_user_id,
    )
    created_items.extend(
        _add_matrix_review_items(
            db,
            project=project,
            section=section,
            items=[item],
            evidence_counts=evidence_counts,
            preaccepted_evidence_item_ids=preaccepted_evidence_item_ids,
            run_key=run_key,
            async_task_id=None,
            actor_user_id=actor_user_id,
        )
    )
    if item.item_type == "qualification":
        created_items.extend(
            _add_qualification_technical_review_items(
                db,
                project=project,
                section=section,
                items=[item],
                run_key=run_key,
                async_task_id=None,
                actor_user_id=actor_user_id,
                qualification_item_ids={item.id},
                include_technical_items=False,
                include_draft_blocks=False,
            )
        )
    db.flush()
    return created_items


def refresh_agent_review_for_compliance_item(
    db: Session,
    *,
    project: Project,
    section: BidSection,
    item: ComplianceItem,
    actor_user_id: uuid.UUID,
    reason: str,
    exclude_review_item_id: uuid.UUID | None = None,
    run_key_prefix: str = "agent-rerun",
    force: bool = False,
) -> dict[str, Any]:
    steps = _rerun_steps_for_compliance_item(item)
    has_existing_item = (
        db.scalar(
            select(AgentReviewItem.id)
            .where(
                AgentReviewItem.tenant_id == item.tenant_id,
                AgentReviewItem.project_id == item.project_id,
                AgentReviewItem.section_id == item.section_id,
                AgentReviewItem.compliance_item_id == item.id,
                AgentReviewItem.status.in_(["open", "auto_passed"]),
            )
            .limit(1)
        )
        is not None
    )
    if not force and not has_existing_item:
        return {
            "superseded_related_count": 0,
            "rerun_created_count": 0,
            "rerun_steps": steps,
            "skipped": True,
        }
    superseded_count = _supersede_open_items_for_compliance_item(
        db,
        tenant_id=item.tenant_id,
        project_id=item.project_id,
        section_id=item.section_id,
        compliance_item_id=item.id,
        steps=steps,
        reason=reason,
        exclude_review_item_id=exclude_review_item_id,
    )
    if item.item_type == "qualification":
        superseded_count += _supersede_open_qualification_decision_items(
            db,
            tenant_id=item.tenant_id,
            project_id=item.project_id,
            section_id=item.section_id,
            reason=reason,
        )
    rerun_items = _rerun_review_for_compliance_item(
        db,
        project=project,
        section=section,
        item=item,
        run_key=f"{run_key_prefix}:{item.id}:{uuid.uuid4().hex[:8]}",
        actor_user_id=actor_user_id,
    )
    return {
        "superseded_related_count": superseded_count,
        "rerun_created_count": len(rerun_items),
        "rerun_steps": steps,
        "skipped": False,
    }


def _confirmation_requires_source_verified(item: ComplianceItem) -> bool:
    return policy_confirmation_requires_source_verified(item)


def _refresh_batch_confirm_guard(item: ComplianceItem) -> None:
    item.is_batch_confirm_allowed = (
        item.risk_level != "high" and not item.is_mandatory and item.status != "needs_material"
    )


def _confirm_compliance_item(
    db: Session,
    *,
    review_item: AgentReviewItem,
    actor_user_id: uuid.UUID,
    reason: str,
    source_verified: bool,
) -> None:
    item = db.get(ComplianceItem, review_item.compliance_item_id)
    if item is None or item.tenant_id != review_item.tenant_id:
        raise AgentAssistError("待确认条款不存在", code="COMPLIANCE_ITEM_NOT_FOUND")
    if item.source_chunk_id is None:
        raise AgentAssistError("缺少原文来源，不能确认条款", code="COMPLIANCE_ITEM_SOURCE_MISSING")
    if _confirmation_requires_source_verified(item) and not source_verified:
        raise AgentAssistError("高风险、强制或资格项确认前必须核验来源", code="SOURCE_VERIFICATION_REQUIRED")
    before = compliance_item_snapshot(item)
    now = datetime.now(UTC)
    item.status = "confirmed"
    item.confirmed_by = actor_user_id
    item.confirmed_at = now
    item.modified_by = actor_user_id
    item.modified_at = now
    item.modify_reason = reason
    _refresh_batch_confirm_guard(item)
    _add_user_audit(
        db,
        tenant_id=review_item.tenant_id,
        project_id=review_item.project_id,
        section_id=review_item.section_id,
        actor_user_id=actor_user_id,
        action="agent.matrix_item_accepted",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json={"item": compliance_item_snapshot(item), "review_item_id": str(review_item.id)},
        reason=reason,
    )


def _bind_evidence(
    db: Session,
    *,
    review_item: AgentReviewItem,
    actor_user_id: uuid.UUID,
    reason: str,
) -> None:
    if review_item.compliance_item_id is None or review_item.enterprise_material_id is None:
        raise AgentAssistError("证据建议缺少条款或资料引用", code="EVIDENCE_SUGGESTION_INCOMPLETE")
    item = db.get(ComplianceItem, review_item.compliance_item_id)
    material = db.get(EnterpriseMaterial, review_item.enterprise_material_id)
    if item is None or item.tenant_id != review_item.tenant_id:
        raise AgentAssistError("待绑定条款不存在", code="COMPLIANCE_ITEM_NOT_FOUND")
    if material is None or material.tenant_id != review_item.tenant_id:
        raise AgentAssistError("企业资料不存在", code="ENTERPRISE_MATERIAL_NOT_FOUND")
    recommendation = review_item.recommendation_json or {}
    evidence_text = str(recommendation.get("evidence_text") or material.evidence_text or material.name)
    try:
        _bind_material_to_item(
            db,
            item=item,
            material=material,
            actor_user_id=actor_user_id,
            reason=reason,
            evidence_text=evidence_text,
            confidence_score=review_item.confidence_score or DEFAULT_BIND_CONFIDENCE,
            review_item_id=review_item.id,
            audit_action="agent.evidence_suggestion_accepted",
        )
    except AgentAssistError as exc:
        if exc.code != "EQUIVALENT_MATERIAL_ALREADY_BOUND":
            raise
        _add_user_audit(
            db,
            tenant_id=review_item.tenant_id,
            project_id=review_item.project_id,
            section_id=review_item.section_id,
            actor_user_id=actor_user_id,
            action="agent.evidence_suggestion_already_bound",
            object_type="agent_review_item",
            object_id=review_item.id,
            before_json=None,
            after_json={
                "review_item_id": str(review_item.id),
                "compliance_item_id": str(item.id),
                "enterprise_material_id": str(material.id),
                "business_effect": "equivalent_binding_already_active",
            },
            reason=reason,
        )


def _confirm_qualification_evaluation(
    db: Session,
    *,
    review_item: AgentReviewItem,
    actor_user_id: uuid.UUID,
    reason: str,
) -> None:
    evaluation = db.get(QualificationEvaluation, review_item.qualification_evaluation_id)
    if evaluation is None or evaluation.tenant_id != review_item.tenant_id:
        raise AgentAssistError("资格评估项不存在", code="QUALIFICATION_EVALUATION_NOT_FOUND")
    before = evaluation_snapshot(evaluation)
    evaluation.confirmed_by = actor_user_id
    evaluation.confirmed_at = datetime.now(UTC)
    evaluation.confirm_reason = reason
    evaluation.confirmed_snapshot_json = qualification_evaluation_result_snapshot(evaluation)
    evaluation.updated_by = actor_user_id
    _add_user_audit(
        db,
        tenant_id=review_item.tenant_id,
        project_id=review_item.project_id,
        section_id=review_item.section_id,
        actor_user_id=actor_user_id,
        action="agent.qualification_evaluation_accepted",
        object_type="qualification_evaluation",
        object_id=evaluation.id,
        before_json=before,
        after_json={**evaluation_snapshot(evaluation), "review_item_id": str(review_item.id)},
        reason=reason,
    )


def _confirm_qualification_decision(
    db: Session,
    *,
    review_item: AgentReviewItem,
    actor_user_id: uuid.UUID,
    reason: str,
) -> bool:
    decision = db.get(QualificationDecision, review_item.qualification_decision_id)
    if decision is None or decision.tenant_id != review_item.tenant_id:
        raise AgentAssistError("参标资格建议不存在", code="QUALIFICATION_DECISION_NOT_FOUND")
    if decision.status == "superseded":
        review_item.status = "superseded"
        review_item.decided_by = actor_user_id
        review_item.decided_at = datetime.now(UTC)
        review_item.decision_reason = f"{reason}（关联参标建议已失效，待办自动关闭）"
        _add_user_audit(
            db,
            tenant_id=review_item.tenant_id,
            project_id=review_item.project_id,
            section_id=review_item.section_id,
            actor_user_id=actor_user_id,
            action="agent.qualification_decision_stale_closed",
            object_type="agent_review_item",
            object_id=review_item.id,
            before_json={
                "review_item_id": str(review_item.id),
                "qualification_decision_id": str(decision.id),
                "decision_status": decision.status,
            },
            after_json={
                "review_item_id": str(review_item.id),
                "status": "superseded",
                "business_effect": "stale_decision_review_item_closed",
            },
            reason=reason,
        )
        return False
    before = {
        "id": str(decision.id),
        "recommendation": decision.recommendation,
        "status": decision.status,
        "summary": decision.summary,
    }
    decision.status = "confirmed"
    decision.confirmed_by = actor_user_id
    decision.confirmed_at = datetime.now(UTC)
    decision.confirm_reason = reason
    _add_user_audit(
        db,
        tenant_id=review_item.tenant_id,
        project_id=review_item.project_id,
        section_id=review_item.section_id,
        actor_user_id=actor_user_id,
        action="agent.qualification_decision_accepted",
        object_type="qualification_decision",
        object_id=decision.id,
        before_json=before,
        after_json={
            "id": str(decision.id),
            "recommendation": decision.recommendation,
            "status": decision.status,
            "confirmed_by": str(actor_user_id),
            "review_item_id": str(review_item.id),
        },
        reason=reason,
    )
    return True


def _approve_draft_block(
    db: Session,
    *,
    review_item: AgentReviewItem,
    actor_user_id: uuid.UUID,
    reason: str,
) -> None:
    block = db.get(DraftBlock, review_item.draft_block_id)
    if block is None or block.tenant_id != review_item.tenant_id:
        raise AgentAssistError("草稿 block 不存在", code="DRAFT_BLOCK_NOT_FOUND")
    before = {"id": str(block.id), "review_status": block.review_status, "content_text": block.content_text}
    block.review_status = "approved"
    _add_user_audit(
        db,
        tenant_id=review_item.tenant_id,
        project_id=review_item.project_id,
        section_id=review_item.section_id,
        actor_user_id=actor_user_id,
        action="agent.draft_block_accepted",
        object_type="draft_block",
        object_id=block.id,
        before_json=before,
        after_json={"id": str(block.id), "review_status": block.review_status, "review_item_id": str(review_item.id)},
        reason=reason,
    )


def accept_agent_review_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    review_item_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str,
    source_verified: bool = False,
) -> AgentReviewItem:
    review_item = _load_open_review_item(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        review_item_id=review_item_id,
    )
    should_mark_accepted = True
    if review_item.action in {"confirm_matrix_item", "review_technical_response"}:
        _confirm_compliance_item(
            db,
            review_item=review_item,
            actor_user_id=actor_user_id,
            reason=reason,
            source_verified=source_verified,
        )
    elif review_item.action == "pre_accept_matrix_item":
        _confirm_compliance_item(
            db,
            review_item=review_item,
            actor_user_id=actor_user_id,
            reason=reason,
            source_verified=False,
        )
    elif review_item.action in {"accept_evidence_binding", "pre_accept_evidence_binding"}:
        _bind_evidence(db, review_item=review_item, actor_user_id=actor_user_id, reason=reason)
    elif review_item.action == "review_qualification_evaluation":
        _confirm_qualification_evaluation(
            db,
            review_item=review_item,
            actor_user_id=actor_user_id,
            reason=reason,
        )
    elif review_item.action == "confirm_qualification_decision":
        should_mark_accepted = _confirm_qualification_decision(
            db,
            review_item=review_item,
            actor_user_id=actor_user_id,
            reason=reason,
        )
    elif review_item.action == "review_draft_block":
        _approve_draft_block(db, review_item=review_item, actor_user_id=actor_user_id, reason=reason)
    elif review_item.action == "missing_evidence":
        raise AgentAssistError(
            "缺证据待办必须通过绑定证据或标记无需证据来补救，不能直接采纳。",
            code="REVIEW_ITEM_REQUIRES_RESOLVE",
        )
    elif review_item.action in {"ack_llm_technical_advice", "ack_llm_draft_advice"}:
        _add_user_audit(
            db,
            tenant_id=review_item.tenant_id,
            project_id=review_item.project_id,
            section_id=review_item.section_id,
            actor_user_id=actor_user_id,
            action="agent.llm_advice_acknowledged",
            object_type="agent_review_item",
            object_id=review_item.id,
            before_json=None,
            after_json={
                "review_item_id": str(review_item.id),
                "action": review_item.action,
                "business_effect": "ack_only",
            },
            reason=reason,
        )
    else:
        raise AgentAssistError("该 Agent 待办不支持采纳", code="REVIEW_ITEM_ACTION_UNSUPPORTED")

    if should_mark_accepted:
        _mark_review_item_accepted(
            review_item,
            actor_user_id=actor_user_id,
            reason=reason,
        )
    db.flush()
    return review_item


def resolve_agent_review_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    review_item_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    resolution: str,
    reason: str,
    source_verified: bool = False,
    enterprise_material_id: uuid.UUID | None = None,
    evidence_text: str | None = None,
    confidence_score: Decimal | None = None,
) -> AgentReviewItem:
    if resolution == "accept":
        return accept_agent_review_item(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            review_item_id=review_item_id,
            actor_user_id=actor_user_id,
            reason=reason,
            source_verified=source_verified,
        )
    if resolution == "dismiss":
        return dismiss_agent_review_item(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            review_item_id=review_item_id,
            actor_user_id=actor_user_id,
            reason=reason,
        )

    review_item = _load_open_review_item(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        review_item_id=review_item_id,
    )
    item = _load_review_item_compliance_item(db, review_item)
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    if project is None or section is None or project.tenant_id != tenant_id or section.tenant_id != tenant_id:
        raise AgentAssistError("项目或标段不存在", code="PROJECT_OR_SECTION_NOT_FOUND")

    if resolution == "bind_evidence":
        material_id = enterprise_material_id or review_item.enterprise_material_id
        if material_id is None:
            raise AgentAssistError(
                "绑定证据补救缺少企业资料",
                code="EVIDENCE_SUGGESTION_INCOMPLETE",
            )
        material = db.get(EnterpriseMaterial, material_id)
        if material is None or material.tenant_id != tenant_id:
            raise AgentAssistError("企业资料不存在", code="ENTERPRISE_MATERIAL_NOT_FOUND")
        recommendation = review_item.recommendation_json or {}
        resolved_evidence_text = (
            evidence_text.strip()
            if evidence_text and evidence_text.strip()
            else str(recommendation.get("evidence_text") or material.evidence_text or material.name)
        )
        _bind_material_to_item(
            db,
            item=item,
            material=material,
            actor_user_id=actor_user_id,
            reason=reason,
            evidence_text=resolved_evidence_text,
            confidence_score=confidence_score or review_item.confidence_score or DEFAULT_BIND_CONFIDENCE,
            review_item_id=review_item.id,
            audit_action="agent.evidence_resolved_bound",
        )
    elif resolution == "evidence_not_required":
        before = compliance_item_snapshot(item)
        now = datetime.now(UTC)
        explanation = dict(item.explanation_json or {})
        explanation["enterprise_evidence_not_required"] = True
        explanation["enterprise_evidence_not_required_reason"] = reason
        explanation["enterprise_evidence_not_required_at"] = now.isoformat()
        explanation["enterprise_evidence_not_required_by"] = str(actor_user_id)
        item.explanation_json = explanation
        if item.status == "needs_material":
            item.status = "pending_confirm"
        item.modified_by = actor_user_id
        item.modified_at = now
        item.modify_reason = reason
        _refresh_batch_confirm_guard(item)
        db.flush()
        qualification_refresh = None
        if item.item_type == "qualification":
            qualification_refresh = refresh_qualification_after_evidence_change(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                actor_user_id=actor_user_id,
            )
        _add_user_audit(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            action="agent.evidence_not_required_resolved",
            object_type="compliance_item",
            object_id=item.id,
            before_json=before,
            after_json={
                "item": compliance_item_snapshot(item),
                "review_item_id": str(review_item.id),
                "qualification_refresh": qualification_refresh,
            },
            reason=reason,
        )
    else:
        raise AgentAssistError(
            "该 Agent 待办不支持此补救方式",
            code="REVIEW_ITEM_RESOLUTION_UNSUPPORTED",
        )

    refresh_result = refresh_agent_review_for_compliance_item(
        db,
        item=item,
        project=project,
        section=section,
        actor_user_id=actor_user_id,
        reason="补救型处理已触发单条定向重评，旧待办已撤回",
        exclude_review_item_id=review_item.id,
        run_key_prefix=f"agent-resolve:{review_item.id}",
        force=True,
    )
    recommendation = dict(review_item.recommendation_json or {})
    recommendation["resolution"] = resolution
    recommendation["superseded_related_count"] = refresh_result["superseded_related_count"]
    recommendation["rerun_created_count"] = refresh_result["rerun_created_count"]
    recommendation["rerun_steps"] = refresh_result["rerun_steps"]
    review_item.recommendation_json = recommendation
    _mark_review_item_accepted(
        review_item,
        actor_user_id=actor_user_id,
        reason=reason,
    )
    db.flush()
    return review_item


def dismiss_agent_review_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    review_item_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str,
) -> AgentReviewItem:
    review_item = _load_open_review_item(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        review_item_id=review_item_id,
    )
    if review_item.action == "missing_evidence":
        raise AgentAssistError(
            "缺证据待办必须通过绑定证据或标记无需证据来补救，不能直接忽略。",
            code="REVIEW_ITEM_REQUIRES_RESOLVE",
        )
    review_item.status = "dismissed"
    review_item.decided_by = actor_user_id
    review_item.decided_at = datetime.now(UTC)
    review_item.decision_reason = reason
    _add_user_audit(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=actor_user_id,
        action="agent.review_item_dismissed",
        object_type="agent_review_item",
        object_id=review_item.id,
        before_json=None,
        after_json={
            "review_item_id": str(review_item.id),
            "step": review_item.step,
            "action": review_item.action,
            "status": review_item.status,
        },
        reason=reason,
    )
    db.flush()
    return review_item
