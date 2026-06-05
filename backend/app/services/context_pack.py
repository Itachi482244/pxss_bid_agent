from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    AsyncTask,
    AuditLog,
    BidSection,
    BusinessDraftChapter,
    BusinessDraftEvidenceRef,
    ComplianceEvidenceBinding,
    ComplianceItem,
    Document,
    DocumentVersion,
    DraftBlock,
    DraftContextPack,
    DraftCoverageReview,
    DraftSectionContextPack,
    EnterpriseMaterial,
    EnterpriseProfile,
    Project,
    QualificationDecision,
)
from app.core.observability import observed_task
from app.prompts import get_prompt
from app.services.business_draft import BusinessDraftError, run_fact_checks
from app.services.evidence_policy import (
    enterprise_evidence_not_required,
    enterprise_evidence_not_required_reason,
    requires_enterprise_evidence,
)
from app.services.template_profile import (
    get_template_profile,
    iter_profile_sections,
)

SCHEMA_VERSION = "1.0"


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _evidence_not_required(item: ComplianceItem) -> bool:
    return enterprise_evidence_not_required(item)


def _evidence_not_required_reason(item: ComplianceItem) -> str | None:
    return enterprise_evidence_not_required_reason(item)


def _requires_enterprise_evidence(item: ComplianceItem) -> bool:
    return requires_enterprise_evidence(item)


def _binding_snapshot(binding: ComplianceEvidenceBinding) -> dict[str, Any]:
    snapshot = binding.material_snapshot or {}
    return {
        "binding_id": str(binding.id),
        "compliance_item_id": str(binding.compliance_item_id),
        "enterprise_material_id": str(binding.enterprise_material_id),
        "material_name": snapshot.get("name"),
        "material_type": snapshot.get("material_type"),
        "verification_status": snapshot.get("verification_status"),
        "data_level": snapshot.get("data_level"),
        "certificate_no": snapshot.get("certificate_no"),
        "valid_until": snapshot.get("valid_until"),
        "evidence_text": binding.evidence_text,
        "confidence_score": str(binding.confidence_score) if binding.confidence_score is not None else None,
    }


def _item_snapshot(
    item: ComplianceItem,
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
) -> dict[str, Any]:
    bindings = bindings_by_item.get(item.id, [])
    return {
        "compliance_item_id": str(item.id),
        "item_type": item.item_type,
        "requirement_text": item.requirement_text,
        "normalized_requirement": item.normalized_requirement,
        "response_suggestion": item.response_suggestion,
        "status": item.status,
        "risk_level": item.risk_level,
        "is_mandatory": item.is_mandatory,
        "source_document_id": str(item.source_document_id),
        "source_version_id": str(item.source_version_id),
        "source_chunk_id": str(item.source_chunk_id) if item.source_chunk_id else None,
        "source_page_no": item.source_page_no,
        "source_quote": item.evidence_text,
        "enterprise_evidence_required": _requires_enterprise_evidence(item),
        "enterprise_evidence_not_required": _evidence_not_required(item),
        "enterprise_evidence_not_required_reason": _evidence_not_required_reason(item),
        "bound_evidence_count": len(bindings),
        "bound_evidence": [_binding_snapshot(binding) for binding in bindings],
    }


def _active_items(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> list[ComplianceItem]:
    return db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(ComplianceItem.item_type.asc(), ComplianceItem.risk_level.desc(), ComplianceItem.created_at.asc())
    ).all()


def _active_bindings(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> dict[uuid.UUID, list[ComplianceEvidenceBinding]]:
    bindings = db.scalars(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.status == "active",
        )
    ).all()
    by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]] = {}
    for binding in bindings:
        by_item.setdefault(binding.compliance_item_id, []).append(binding)
    return by_item


def _material_applies_to_project(material: EnterpriseMaterial, project: Project) -> bool:
    fields = material.structured_fields or {}
    project_fit = fields.get("project_fit")
    if not project_fit:
        return True
    project_fit_text = str(project_fit)
    return project_fit_text in project.name or project.name in project_fit_text


def _enterprise_material_facts(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
) -> dict[str, Any]:
    materials = db.scalars(
        select(EnterpriseMaterial)
        .where(
            EnterpriseMaterial.tenant_id == tenant_id,
            EnterpriseMaterial.verification_status == "confirmed",
        )
        .order_by(EnterpriseMaterial.updated_at.desc())
    ).all()
    facts: dict[str, Any] = {}

    def set_fact(field_name: str, value: Any) -> None:
        if value in (None, "") or facts.get(field_name) not in (None, ""):
            return
        facts[field_name] = value

    direct_fields = {
        "authorized_agent_name",
        "legal_representative_title",
        "project_scope",
        "construction_period_days",
        "quality_standard",
        "warranty_period",
        "performance_bond",
        "bid_security_amount",
        "bid_security_form",
        "is_consortium",
        "boq_file",
        "financial_report_years",
    }
    for material in materials:
        if not _material_applies_to_project(material, project):
            continue
        fields = material.structured_fields or {}
        role_text = str(fields.get("role") or "")
        material_text = f"{material.name} {material.evidence_text or ''} {role_text}"
        if material.material_type == "personnel" and any(
            signal in material_text for signal in ("项目负责人", "项目经理")
        ):
            set_fact("project_manager_name", fields.get("person_name") or material.holder_name)
            set_fact(
                "project_manager_id_no",
                fields.get("id_no") or fields.get("identity_no") or fields.get("id_card_no"),
            )
        for field_name in direct_fields:
            set_fact(field_name, fields.get(field_name))
        authorized_agent = fields.get("authorized_agent")
        set_fact("authorized_agent_name", authorized_agent)
    return facts


def _project_facts(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section: BidSection,
) -> dict[str, Any]:
    profile = db.scalar(
        select(EnterpriseProfile).where(
            EnterpriseProfile.tenant_id == tenant_id,
        )
    )
    deadline = section.bid_deadline_at or project.bid_deadline_at
    amount = section.budget_amount or project.budget_amount
    facts = {
        "project_name": project.name,
        "tenderer_name": project.purchaser,
        "agency_name": project.agency,
        "bid_section_name": section.name,
        "tender_project_no": section.code,
        "bid_deadline": deadline,
        "bid_date": date.today().isoformat(),
        "bid_price_amount": amount,
        "region_code": project.region_code,
        "industry_code": project.industry_code,
        "bidder_name": profile.company_name if profile else None,
        "bidder_address": profile.registered_address if profile else None,
        "unified_social_credit_code": profile.unified_social_credit_code if profile else None,
        "legal_representative_name": profile.legal_representative if profile else None,
        "legal_representative_title": None,
        "authorized_agent_name": None,
        "project_scope": None,
        "construction_period_days": None,
        "quality_standard": None,
        "project_manager_name": None,
        "project_manager_id_no": None,
        "warranty_period": None,
        "performance_bond": None,
        "bid_security_amount": None,
        "bid_security_form": None,
        "is_consortium": None,
        "boq_file": None,
        "financial_report_years": None,
    }
    for field_name, value in _enterprise_material_facts(db, tenant_id=tenant_id, project=project).items():
        if facts.get(field_name) in (None, ""):
            facts[field_name] = value
    return _jsonable(facts)


def _source_document_snapshot(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> dict[str, Any]:
    documents = db.scalars(
        select(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.project_id == project_id,
            Document.section_id == section_id,
            Document.doc_type == "tender",
            Document.status != "deleted",
        )
        .order_by(Document.created_at.desc())
    ).all()
    latest_document = documents[0] if documents else None
    latest_version = (
        db.get(DocumentVersion, latest_document.current_version_id)
        if latest_document and latest_document.current_version_id
        else None
    )
    return {
        "document_id": str(latest_document.id) if latest_document else None,
        "title": latest_document.title if latest_document else None,
        "current_version_id": str(latest_version.id) if latest_version else None,
        "current_version_label": latest_version.version_label if latest_version else None,
        "version_status": latest_version.parse_status if latest_version else None,
        "document_count": len(documents),
    }


def _latest_qualification_decision(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> QualificationDecision | None:
    return db.scalar(
        select(QualificationDecision)
        .where(
            QualificationDecision.tenant_id == tenant_id,
            QualificationDecision.project_id == project_id,
            QualificationDecision.section_id == section_id,
            QualificationDecision.status != "superseded",
        )
        .order_by(QualificationDecision.created_at.desc())
    )


def _qualification_decision_snapshot(decision: QualificationDecision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "decision_id": str(decision.id),
        "recommendation": decision.recommendation,
        "status": decision.status,
        "summary": decision.summary,
        "satisfied_count": decision.satisfied_count,
        "blocking_count": decision.blocking_count,
        "missing_count": decision.missing_count,
        "pending_count": decision.pending_count,
        "reasons": decision.reasons_json,
        "confirmed_by": str(decision.confirmed_by) if decision.confirmed_by else None,
        "confirmed_at": decision.confirmed_at,
        "confirm_reason": decision.confirm_reason,
        "created_at": decision.created_at,
    }


def _missing_global_fields(profile: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for field_name in profile.get("global_required_fields") or []:
        if facts.get(field_name) in (None, ""):
            missing.append(
                {
                    "field": field_name,
                    "reason": "TemplateProfile 标记为全局必填，但当前项目/企业资料未提供。",
                }
            )
    return missing


def _matrix_summary(
    items: list[ComplianceItem],
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
) -> dict[str, int]:
    return {
        "total": len(items),
        "confirmed": sum(1 for item in items if item.status == "confirmed"),
        "pending": sum(1 for item in items if item.status == "pending_confirm"),
        "high_risk": sum(1 for item in items if item.risk_level == "high"),
        "mandatory": sum(1 for item in items if item.is_mandatory or item.item_type == "mandatory_response"),
        "qualification": sum(1 for item in items if item.item_type == "qualification"),
        "missing_evidence": sum(
            1
            for item in items
            if _requires_enterprise_evidence(item) and not bindings_by_item.get(item.id)
        ),
    }


def _readiness_checks(
    *,
    items: list[ComplianceItem],
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
    missing_fields: list[dict[str, str]],
    source_document: dict[str, Any],
    qualification_decision: QualificationDecision | None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    if not items:
        checks.append(
            {
                "code": "matrix.empty",
                "status": "block",
                "summary": "当前标段没有合规矩阵项，无法构建可追溯生成上下文。",
                "action": "先生成并审阅合规矩阵。",
            }
        )

    unconfirmed_guard_items = [
        item
        for item in items
        if item.status != "confirmed"
        and (item.risk_level == "high" or item.is_mandatory or item.item_type in {"qualification", "mandatory_response"})
    ]
    if unconfirmed_guard_items:
        checks.append(
            {
                "code": "matrix.guard_items_unconfirmed",
                "status": "block",
                "summary": f"还有 {len(unconfirmed_guard_items)} 条高风险/强制/资格项未确认。",
                "action": "回到矩阵审阅，完成原文核对和人工确认。",
                "sample_item_ids": [str(item.id) for item in unconfirmed_guard_items[:8]],
            }
        )

    missing_evidence_items = [
        item
        for item in items
        if _requires_enterprise_evidence(item) and not bindings_by_item.get(item.id)
    ]
    if missing_evidence_items:
        checks.append(
            {
                "code": "evidence.missing_required",
                "status": "block",
                "summary": f"还有 {len(missing_evidence_items)} 条强制/资格/高风险项缺少企业资料证据。",
                "action": "绑定企业资料，或明确填写无需绑定证据说明。",
                "sample_item_ids": [str(item.id) for item in missing_evidence_items[:8]],
            }
        )

    if missing_fields:
        checks.append(
            {
                "code": "project_fields.missing",
                "status": "warn",
                "summary": f"还有 {len(missing_fields)} 个 TemplateProfile 全局字段缺失。",
                "action": "补齐项目/企业关键字段，或允许生成带占位的内部草稿。",
                "sample_fields": [item["field"] for item in missing_fields[:10]],
            }
        )

    if not source_document.get("current_version_id"):
        checks.append(
            {
                "code": "source_document.missing_current_version",
                "status": "warn",
                "summary": "当前没有可识别的招标文件当前版本快照。",
                "action": "确认招标文件是否已上传并解析；继续生成时会标记来源版本缺失。",
            }
        )

    if qualification_decision is None:
        checks.append(
            {
                "code": "qualification.decision_missing",
                "status": "block",
                "summary": "尚未生成参标资格预评估结论。",
                "action": "先运行资格预评估，生成并人工确认 Go/No-Go 参标建议。",
            }
        )
    elif qualification_decision.status != "confirmed":
        checks.append(
            {
                "code": "qualification.decision_not_confirmed",
                "status": "block",
                "summary": "参标建议尚未人工确认。",
                "action": "回到资格预评估，确认 Go/No-Go 结论后再确认 ContextPack。",
                "decision_id": str(qualification_decision.id),
            }
        )
    elif qualification_decision.recommendation == "no_go":
        checks.append(
            {
                "code": "qualification.no_go_confirmed",
                "status": "block",
                "summary": "已确认的参标建议为 No-Go。",
                "action": "建议先处理阻断项；如仍继续，只能生成带风险接受记录的内部草稿。",
                "decision_id": str(qualification_decision.id),
            }
        )
    elif qualification_decision.recommendation == "conditional_go":
        checks.append(
            {
                "code": "qualification.conditional_go_confirmed",
                "status": "warn",
                "summary": "参标建议为有条件 Go，仍有缺材料或待确认事项。",
                "action": "生成草稿时保留待补占位，并在提交前复核资格风险。",
                "decision_id": str(qualification_decision.id),
            }
        )

    status = "pass"
    if any(check["status"] == "block" for check in checks):
        status = "block"
    elif any(check["status"] == "warn" for check in checks):
        status = "warn"
    return {"status": status, "checks": checks}


def _section_matches_item(section_def: dict[str, Any], item: ComplianceItem) -> bool:
    covers = set(section_def.get("covers_item_types") or [])
    if item.item_type in covers:
        return True
    text = item.requirement_text or ""
    section_type = section_def.get("section_type")
    if section_type == "bid_security" and "保证金" in text:
        return True
    if section_type == "consortium_agreement" and "联合体" in text:
        return True
    if section_type in {"project_management_team", "project_manager_resume"} and any(
        keyword in text for keyword in ("项目经理", "项目负责人", "建造师", "人员", "社保")
    ):
        return True
    if section_type in {"qualification_performance_summary", "scoring_performance_summary"} and "业绩" in text:
        return True
    return False


def _items_for_section(section_def: dict[str, Any], items: list[ComplianceItem]) -> list[ComplianceItem]:
    return [item for item in items if _section_matches_item(section_def, item)]


def _build_outline_plan(
    *,
    profile: dict[str, Any],
    items: list[ComplianceItem],
    section_types: list[str] | None,
) -> dict[str, Any]:
    requested = set(section_types or [])
    sections: list[dict[str, Any]] = []
    for section_def in iter_profile_sections(profile):
        matched_items = _items_for_section(section_def, items)
        include = bool(section_def.get("required")) or bool(matched_items)
        if requested:
            include = section_def["section_type"] in requested
        if not include:
            continue
        sections.append(
            {
                "section_type": section_def["section_type"],
                "title": section_def["title"],
                "volume_id": section_def.get("volume_id"),
                "volume_title": section_def.get("volume_title"),
                "required": bool(section_def.get("required")),
                "generation_mode": section_def.get("generation_mode"),
                "order_index": section_def.get("order_index"),
                "required_fields": list(section_def.get("required_fields") or []),
                "covers_item_types": list(section_def.get("covers_item_types") or []),
                "compliance_item_ids": [str(item.id) for item in matched_items],
                "evidence_required": any(_requires_enterprise_evidence(item) for item in matched_items),
                "output_format": "structured_blocks",
                "review_policy": "manual_required",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "template_profile + compliance_matrix",
        "sections": sections,
    }


def build_context_pack_preview(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    profile_id: str | None = None,
    section_types: list[str] | None = None,
) -> dict[str, Any]:
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    if project is None or section is None:
        raise BusinessDraftError("项目或标段不存在")

    try:
        profile = get_template_profile(profile_id)
    except ValueError as exc:
        raise BusinessDraftError(str(exc)) from exc

    items = _active_items(db, tenant_id=tenant_id, project_id=project_id, section_id=section_id)
    bindings_by_item = _active_bindings(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    facts = _project_facts(db, tenant_id=tenant_id, project=project, section=section)
    source_document = _source_document_snapshot(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    qualification_decision = _latest_qualification_decision(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    missing_fields = _missing_global_fields(profile, facts)
    readiness = _readiness_checks(
        items=items,
        bindings_by_item=bindings_by_item,
        missing_fields=missing_fields,
        source_document=source_document,
        qualification_decision=qualification_decision,
    )
    outline_plan = _build_outline_plan(profile=profile, items=items, section_types=section_types)
    matrix_items = [_item_snapshot(item, bindings_by_item) for item in items]
    context_json = {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "project_id": str(project.id),
            "project_name": project.name,
            "bid_section_id": str(section.id),
            "bid_section_name": section.name,
        },
        "project_facts": facts,
        "qualification_decision": _qualification_decision_snapshot(qualification_decision),
        "source_document": source_document,
        "template_profile": {
            "profile_id": profile["profile_id"],
            "profile_name": profile["profile_name"],
            "profile_version": profile["version"],
            "generation_mode": profile["generation_mode"],
        },
        "matrix_summary": _matrix_summary(items, bindings_by_item),
        "matrix_items": matrix_items,
        "bound_evidence": [
            _binding_snapshot(binding)
            for bindings in bindings_by_item.values()
            for binding in bindings
        ],
        "manual_notes": [
            {
                "compliance_item_id": str(item.id),
                "reason": _evidence_not_required_reason(item),
                "type": "enterprise_evidence_not_required",
            }
            for item in items
            if _evidence_not_required(item)
        ],
        "missing_facts": missing_fields,
        "generation_constraints": {
            "hard_blockers": profile.get("hard_blockers") or [],
            "qualification_policy": (
                "生成正式商务/资格草稿前，必须已有人工确认的 Go 或 Conditional Go 参标建议；"
                "No-Go 仅允许在风险接受后生成内部草稿。"
            ),
            "forbidden_claims": [
                "不得编造未在 ContextPack 中出现的证书编号、人员、业绩、金额或日期。",
                "没有绑定证据的资格/强制事实必须输出待确认占位。",
                "报价清单正文不由 LLM 生成，只允许引用外部报价文件或占位。",
            ],
        },
    }
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["version"],
        "schema_version": SCHEMA_VERSION,
        "readiness_status": readiness["status"],
        "context_json": _jsonable(context_json),
        "readiness_json": _jsonable(readiness),
        "outline_plan_json": _jsonable(outline_plan),
    }


def _qualification_gate_codes(readiness_json: dict[str, Any]) -> set[str]:
    return {
        str(check.get("code"))
        for check in readiness_json.get("checks") or []
        if str(check.get("code")).startswith("qualification.")
    }


def _assert_context_pack_can_be_confirmed(preview: dict[str, Any]) -> None:
    qualification_codes = _qualification_gate_codes(preview["readiness_json"])
    if "qualification.decision_missing" in qualification_codes:
        raise BusinessDraftError("请先运行资格预评估，生成并人工确认参标建议后再确认 ContextPack")
    if "qualification.decision_not_confirmed" in qualification_codes:
        raise BusinessDraftError("参标建议尚未人工确认，请先完成资格预评估确认")


def _section_context_from_outline(
    *,
    context_pack_id: uuid.UUID,
    outline_section: dict[str, Any],
    global_context: dict[str, Any],
) -> dict[str, Any]:
    draft_prompt = get_prompt("business_draft_section", "1.2.0")
    item_ids = set(outline_section.get("compliance_item_ids") or [])
    matrix_items = [
        item
        for item in global_context.get("matrix_items") or []
        if item.get("compliance_item_id") in item_ids
    ]
    bound_evidence = [
        evidence
        for item in matrix_items
        for evidence in item.get("bound_evidence") or []
    ]
    required_fields = outline_section.get("required_fields") or []
    project_facts = global_context.get("project_facts") or {}
    missing_facts = [
        {
            "field": field_name,
            "reason": "本章节必填字段缺失，生成稿必须保留待补占位。",
        }
        for field_name in required_fields
        if project_facts.get(field_name) in (None, "")
    ]
    missing_facts.extend(
        [
            {
                "compliance_item_id": item.get("compliance_item_id"),
                "reason": "该条款需要企业证据，但当前未绑定证据。",
            }
            for item in matrix_items
            if item.get("enterprise_evidence_required") and not item.get("bound_evidence_count")
        ]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "context_pack_id": str(context_pack_id),
        "section": {
            "section_type": outline_section["section_type"],
            "title": outline_section["title"],
            "required": outline_section["required"],
            "generation_mode": outline_section["generation_mode"],
            "required_fields": outline_section.get("required_fields") or [],
        },
        "project_facts": project_facts,
        "qualification_decision": global_context.get("qualification_decision"),
        "matrix_items": matrix_items,
        "bound_evidence": bound_evidence,
        "manual_notes": [
            note
            for note in global_context.get("manual_notes") or []
            if note.get("compliance_item_id") in item_ids
        ],
        "missing_facts": missing_facts,
        "candidate_evidence": [],
        "output_schema": {
            "prompt_version": draft_prompt.prompt_version,
            "schema": draft_prompt.output_schema,
        },
        "forbidden_claims": (global_context.get("generation_constraints") or {}).get("forbidden_claims") or [],
    }


def create_context_pack(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    profile_id: str | None = None,
    section_types: list[str] | None = None,
) -> DraftContextPack:
    preview = build_context_pack_preview(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        profile_id=profile_id,
        section_types=section_types,
    )
    _assert_context_pack_can_be_confirmed(preview)
    existing = db.scalars(
        select(DraftContextPack).where(
            DraftContextPack.tenant_id == tenant_id,
            DraftContextPack.project_id == project_id,
            DraftContextPack.section_id == section_id,
            DraftContextPack.status != "superseded",
        )
    ).all()
    for context_pack in existing:
        context_pack.status = "superseded"

    context_pack = DraftContextPack(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        profile_id=preview["profile_id"],
        profile_version=preview["profile_version"],
        schema_version=preview["schema_version"],
        status="confirmed",
        readiness_status=preview["readiness_status"],
        context_json=preview["context_json"],
        readiness_json=preview["readiness_json"],
        outline_plan_json=preview["outline_plan_json"],
        created_by=actor_user_id,
        confirmed_by=actor_user_id,
        confirmed_at=datetime.now(UTC),
    )
    db.add(context_pack)
    db.flush()

    for sort_order, outline_section in enumerate(preview["outline_plan_json"]["sections"], start=1):
        section_context = _section_context_from_outline(
            context_pack_id=context_pack.id,
            outline_section=outline_section,
            global_context=preview["context_json"],
        )
        db.add(
            DraftSectionContextPack(
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                context_pack_id=context_pack.id,
                section_type=outline_section["section_type"],
                title=outline_section["title"],
                sort_order=sort_order,
                generation_mode=outline_section["generation_mode"],
                status="blocked" if section_context["missing_facts"] else "ready",
                context_json=_jsonable(section_context),
                created_by=actor_user_id,
            )
        )
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="business_draft.context_pack_created",
            object_type="draft_context_pack",
            object_id=context_pack.id,
            after_json={
                "readiness_status": context_pack.readiness_status,
                "profile_id": context_pack.profile_id,
                "section_count": len(preview["outline_plan_json"]["sections"]),
            },
            reason="构建商务/资格草稿生成 ContextPack",
            severity="warning" if context_pack.readiness_status == "block" else "info",
        )
    )
    return context_pack


def _chapter_type_for_section(section_type: str) -> str:
    if section_type.startswith("qualification") or section_type in {
        "bidder_basic_info",
        "financial_status",
        "scoring_performance_summary",
        "project_management_team",
        "project_manager_resume",
        "team_supporting_materials",
    }:
        return "qualification_response"
    if section_type in {"bid_commitment", "consortium_agreement"}:
        return "commitment"
    if "deviation" in section_type:
        return "deviation_table"
    if section_type in {"priced_boq", "other_business_materials"}:
        return "other"
    return "business_response"


def _section_value_lines(context_json: dict[str, Any], required_fields: list[str]) -> list[str]:
    facts = context_json.get("project_facts") or {}
    lines: list[str] = []
    for field_name in required_fields:
        value = facts.get(field_name)
        if value in (None, ""):
            value = f"[请人工补充：{field_name}]"
        lines.append(f"- {field_name}：{value}")
    return lines


def _build_section_draft_content(section_pack: DraftSectionContextPack) -> tuple[str, list[dict[str, Any]]]:
    context_json = section_pack.context_json
    section = context_json.get("section") or {}
    matrix_items = context_json.get("matrix_items") or []
    required_fields = section.get("required_fields") or []
    lines = [
        str(section.get("title") or section_pack.title),
        "说明：本章由 MVP1.2 ContextPack 生成，正式投标前必须人工审阅。",
        "",
    ]
    if section.get("generation_mode") in {"fixed_form", "structured_table", "conditional_form"}:
        lines.append("字段填充草稿：")
        lines.extend(_section_value_lines(context_json, required_fields))
        lines.append("")
    elif section.get("generation_mode") == "external_attachment":
        lines.append("本章节应绑定外部报价或附件文件，系统不自动编造清单、报价和附件内容。")
        lines.append("[请人工绑定或确认外部附件]")
        lines.append("")
    else:
        facts = context_json.get("project_facts") or {}
        project_name = facts.get("project_name") or "[请人工补充：project_name]"
        bidder_name = facts.get("bidder_name") or "[请人工补充：bidder_name]"
        lines.append(f"我方 {bidder_name} 将按《{project_name}》招标文件要求完成本章节响应。")
        lines.append("")

    refs: list[dict[str, Any]] = []
    if matrix_items:
        lines.append("关联条款响应：")
    for index, item in enumerate(matrix_items, start=1):
        evidence = item.get("bound_evidence") or []
        lines.append(f"{index}. 招标要求：{item.get('requirement_text')}")
        suggestion = item.get("response_suggestion") or "我方将按该条款要求响应，具体事实以已绑定证据和人工确认结果为准。"
        if item.get("enterprise_evidence_required") and not evidence:
            suggestion = f"{suggestion} [请人工补充证据]"
        lines.append(f"   响应草稿：{suggestion}")
        if evidence:
            material_names = [str(ref.get("material_name") or "企业资料") for ref in evidence]
            lines.append(f"   已绑定证据：{'；'.join(material_names)}。")
        else:
            lines.append("   已绑定证据：无。")
        refs.append(
            {
                "compliance_item_id": item.get("compliance_item_id"),
                "source_chunk_id": item.get("source_chunk_id"),
                "source_type": "compliance_item",
                "source_snapshot": item,
                "quote_text": item.get("source_quote") or item.get("requirement_text"),
            }
        )
        for evidence_ref in evidence:
            refs.append(
                {
                    "compliance_item_id": item.get("compliance_item_id"),
                    "evidence_binding_id": evidence_ref.get("binding_id"),
                    "enterprise_material_id": evidence_ref.get("enterprise_material_id"),
                    "source_type": "enterprise_material",
                    "source_snapshot": evidence_ref,
                    "quote_text": evidence_ref.get("evidence_text"),
                }
            )
        lines.append("")
    return "\n".join(lines).strip(), refs


def _add_draft_blocks(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    chapter: BusinessDraftChapter,
    section_pack: DraftSectionContextPack,
) -> list[DraftBlock]:
    context_json = section_pack.context_json
    matrix_items = context_json.get("matrix_items") or []
    missing_facts = context_json.get("missing_facts") or []
    evidence_refs = [
        evidence
        for item in matrix_items
        for evidence in item.get("bound_evidence") or []
    ]
    links = {
        "context_pack_id": str(section_pack.context_pack_id),
        "section_context_pack_id": str(section_pack.id),
        "section_type": section_pack.section_type,
        "compliance_item_ids": [item.get("compliance_item_id") for item in matrix_items],
        "evidence_binding_ids": [evidence.get("binding_id") for evidence in evidence_refs],
        "enterprise_material_ids": [evidence.get("enterprise_material_id") for evidence in evidence_refs],
        "source_chunk_ids": [
            item.get("source_chunk_id")
            for item in matrix_items
            if item.get("source_chunk_id")
        ],
    }
    review_status = "covered"
    if any(item.get("compliance_item_id") for item in missing_facts):
        review_status = "needs_evidence"
    elif missing_facts:
        review_status = "needs_fact"

    blocks = [
        DraftBlock(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            chapter_id=chapter.id,
            section_context_pack_id=section_pack.id,
            block_type="heading",
            content_text=chapter.title,
            sort_order=1,
            links_json=links,
            fact_claims_json=[],
            missing_fact_placeholders_json=[],
            risk_flags_json=[],
            review_status="covered",
        ),
        DraftBlock(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            chapter_id=chapter.id,
            section_context_pack_id=section_pack.id,
            block_type="paragraph",
            content_text=chapter.content_text,
            sort_order=2,
            links_json=links,
            fact_claims_json=[],
            missing_fact_placeholders_json=missing_facts,
            risk_flags_json=[
                {
                    "compliance_item_id": item.get("compliance_item_id"),
                    "risk_level": item.get("risk_level"),
                    "status": item.get("status"),
                }
                for item in matrix_items
                if item.get("risk_level") == "high" or item.get("status") != "confirmed"
            ],
            review_status=review_status,
        ),
    ]
    for block in blocks:
        db.add(block)
    return blocks


def generate_draft_from_context_pack(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    allow_blocked_internal_draft: bool = False,
) -> tuple[list[BusinessDraftChapter], list[DraftBlock], DraftCoverageReview]:
    context_pack = db.get(DraftContextPack, context_pack_id)
    project = db.get(Project, project_id)
    if context_pack is None or project is None:
        raise BusinessDraftError("ContextPack 或项目不存在")
    if (
        context_pack.tenant_id != tenant_id
        or context_pack.project_id != project_id
        or context_pack.section_id != section_id
        or context_pack.status == "superseded"
    ):
        raise BusinessDraftError("ContextPack 不属于当前项目标段或已失效")
    qualification_decision = _latest_qualification_decision(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    if qualification_decision is None:
        raise BusinessDraftError("请先运行资格预评估，生成并人工确认参标建议后再生成草稿")
    if qualification_decision.status != "confirmed":
        raise BusinessDraftError("参标建议尚未人工确认，请先完成资格预评估确认")
    if qualification_decision.recommendation == "no_go" and not allow_blocked_internal_draft:
        raise BusinessDraftError("参标建议为 No-Go；如仅生成内部草稿，需显式填写风险接受并允许阻塞草稿")
    if context_pack.readiness_status == "block" and not allow_blocked_internal_draft:
        raise BusinessDraftError("当前 ContextPack 存在阻塞项，需处理后生成；如仅生成内部草稿需显式允许")

    section_packs = db.scalars(
        select(DraftSectionContextPack)
        .where(
            DraftSectionContextPack.tenant_id == tenant_id,
            DraftSectionContextPack.context_pack_id == context_pack_id,
            DraftSectionContextPack.status != "superseded",
        )
        .order_by(DraftSectionContextPack.sort_order.asc())
    ).all()
    if not section_packs:
        raise BusinessDraftError("当前 ContextPack 没有章节上下文")

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

    db.execute(
        delete(DraftBlock).where(
            DraftBlock.tenant_id == tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
        )
    )

    chapters: list[BusinessDraftChapter] = []
    blocks: list[DraftBlock] = []
    for sort_order, section_pack in enumerate(section_packs, start=1):
        content_text, refs = _build_section_draft_content(section_pack)
        matrix_items = section_pack.context_json.get("matrix_items") or []
        missing_facts = section_pack.context_json.get("missing_facts") or []
        chapter = BusinessDraftChapter(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            chapter_type=_chapter_type_for_section(section_pack.section_type),
            title=section_pack.title,
            sort_order=sort_order,
            content_text=content_text,
            outline_json={
                "section_type": section_pack.section_type,
                "generation_mode": section_pack.generation_mode,
                "context_pack_id": str(context_pack.id),
                "section_context_pack_id": str(section_pack.id),
                "required": (section_pack.context_json.get("section") or {}).get("required"),
            },
            evidence_summary_json={
                "compliance_item_count": len(matrix_items),
                "bound_evidence_count": sum(
                    len(item.get("bound_evidence") or []) for item in matrix_items
                ),
                "missing_fact_count": len(missing_facts),
            },
            fact_check_status="pending",
            status="pending_review",
            version_no=1,
            generated_from_json={
                "source": "mvp1.2_context_pack",
                "context_pack_id": str(context_pack.id),
                "section_context_pack_id": str(section_pack.id),
                "profile_id": context_pack.profile_id,
                "profile_version": context_pack.profile_version,
                "generated_at": datetime.now(UTC).isoformat(),
                "internal_draft": context_pack.readiness_status == "block",
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
        blocks.extend(
            _add_draft_blocks(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                chapter=chapter,
                section_pack=section_pack,
            )
        )

    db.flush()
    coverage_review = create_coverage_review(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        context_pack_id=context_pack.id,
        actor_user_id=actor_user_id,
    )
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="business_draft.context_pack_generated",
            object_type="draft_context_pack",
            object_id=context_pack.id,
            after_json={
                "chapter_count": len(chapters),
                "block_count": len(blocks),
                "coverage_status": coverage_review.status,
            },
            reason="基于 MVP1.2 ContextPack 生成结构化商务/资格草稿",
            severity="warning" if coverage_review.status != "pass" else "info",
        )
    )
    return chapters, blocks, coverage_review


def create_coverage_review(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> DraftCoverageReview:
    context_pack = db.get(DraftContextPack, context_pack_id)
    if context_pack is None or context_pack.tenant_id != tenant_id:
        raise BusinessDraftError("ContextPack 不存在")
    section_packs = db.scalars(
        select(DraftSectionContextPack).where(
            DraftSectionContextPack.tenant_id == tenant_id,
            DraftSectionContextPack.context_pack_id == context_pack_id,
            DraftSectionContextPack.status != "superseded",
        )
    ).all()
    section_pack_ids = [pack.id for pack in section_packs]
    blocks = (
        db.scalars(
            select(DraftBlock).where(
                DraftBlock.tenant_id == tenant_id,
                DraftBlock.section_context_pack_id.in_(section_pack_ids),
            )
        ).all()
        if section_pack_ids
        else []
    )
    expected_item_ids = {
        item.get("compliance_item_id")
        for item in context_pack.context_json.get("matrix_items") or []
        if item.get("enterprise_evidence_required") or item.get("risk_level") == "high"
    }
    covered_item_ids: set[str] = set()
    for block in blocks:
        for item_id in (block.links_json or {}).get("compliance_item_ids") or []:
            if item_id:
                covered_item_ids.add(str(item_id))

    issues: list[dict[str, Any]] = []
    missing_coverage = sorted(item_id for item_id in expected_item_ids if item_id not in covered_item_ids)
    if missing_coverage:
        issues.append(
            {
                "code": "coverage.required_items_missing",
                "severity": "block",
                "summary": f"{len(missing_coverage)} 条强制/资格/高风险矩阵项未覆盖到生成 block。",
                "compliance_item_ids": missing_coverage[:20],
            }
        )
    needs_evidence = [block for block in blocks if block.review_status == "needs_evidence"]
    if needs_evidence:
        issues.append(
            {
                "code": "coverage.blocks_need_evidence",
                "severity": "block",
                "summary": f"{len(needs_evidence)} 个 block 缺少必需证据。",
                "block_ids": [str(block.id) for block in needs_evidence[:20]],
            }
        )
    needs_fact = [block for block in blocks if block.review_status == "needs_fact"]
    if needs_fact:
        issues.append(
            {
                "code": "coverage.blocks_need_fact",
                "severity": "warn",
                "summary": f"{len(needs_fact)} 个 block 存在待补事实占位。",
                "block_ids": [str(block.id) for block in needs_fact[:20]],
            }
        )
    if context_pack.readiness_status == "block":
        issues.append(
            {
                "code": "coverage.context_pack_blocked",
                "severity": "block",
                "summary": "生成所用 ContextPack 本身仍存在阻塞项，只能作为内部草稿。",
            }
        )

    status = "pass"
    if any(issue["severity"] == "block" for issue in issues):
        status = "block"
    elif issues:
        status = "warn"
    expected_count = len(expected_item_ids)
    # Count only the *expected* items that were covered so the rate stays within
    # [0, 1] and ``covered + missing == expected`` holds. Blocks routinely
    # reference compliance items outside the expected (evidence-required / high
    # risk) population, so the raw reference count is not a valid numerator.
    covered_count = len(expected_item_ids & covered_item_ids)
    coverage_rate = round(covered_count / expected_count, 4) if expected_count else 1.0
    evidence_ref_count = sum(
        len((block.links_json or {}).get("evidence_binding_ids") or [])
        for block in blocks
    )
    evidence_reference_rate = round(evidence_ref_count / len(blocks), 4) if blocks else 1.0
    block_issue_count = len(needs_evidence) + len(needs_fact) + len(missing_coverage)
    quality_score = max(
        0,
        min(
            100,
            round(
                100
                - (100 - coverage_rate * 100) * 0.45
                - min(block_issue_count, 20) * 3
                - (0 if status == "pass" else 12 if status == "warn" else 24)
            ),
        ),
    )
    review = DraftCoverageReview(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        context_pack_id=context_pack_id,
        status=status,
        summary_json={
            "section_context_pack_count": len(section_packs),
            "block_count": len(blocks),
            "expected_coverage_item_count": expected_count,
            "covered_item_count": covered_count,
            "coverage_rate": coverage_rate,
            "evidence_ref_count": evidence_ref_count,
            "evidence_reference_rate": evidence_reference_rate,
            "needs_evidence_count": len(needs_evidence),
            "needs_fact_count": len(needs_fact),
            "missing_coverage_count": len(missing_coverage),
            "issue_count": len(issues),
            "quality_score": quality_score,
        },
        issues_json=_jsonable(issues),
        created_by=actor_user_id,
    )
    db.add(review)
    return review


def _coerce_uuid(value: uuid.UUID | str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


@observed_task("business_draft_generate")
def execute_business_draft_generation_task(
    db: Session,
    task_id: uuid.UUID | str,
) -> dict[str, str | int]:
    """Run an async MVP1.2 ContextPack draft generation task.

    Mirrors :func:`execute_compliance_matrix_generation_task`: drives the
    ``async_tasks`` row through running -> succeeded/failed, persists a summary
    in ``output_json``, and never re-raises so an inline caller can return the
    failed task for the client to poll.
    """
    task_uuid = _coerce_uuid(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "business_draft_generate":
        raise BusinessDraftError("商务草稿生成任务不存在")

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = 20
    db.commit()

    payload = task.input_json or {}
    try:
        context_pack_id = _coerce_uuid(payload["context_pack_id"])
        chapters, blocks, coverage_review = generate_draft_from_context_pack(
            db,
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            context_pack_id=context_pack_id,
            actor_user_id=task.created_by,
            allow_blocked_internal_draft=bool(payload.get("allow_blocked_internal_draft")),
        )
        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "context_pack_id": str(context_pack_id),
            "chapter_count": len(chapters),
            "block_count": len(blocks),
            "coverage_status": coverage_review.status,
            "coverage_review_id": str(coverage_review.id),
        }
        task.finished_at = datetime.now(UTC)
        db.add(
            AuditLog(
                tenant_id=task.tenant_id,
                project_id=task.project_id,
                section_id=task.section_id,
                actor_user_id=task.created_by,
                actor_type="system",
                action="business_draft.context_pack_generate_task_succeeded",
                object_type="async_task",
                object_id=task.id,
                after_json=task.output_json,
                reason="异步 ContextPack 商务/资格草稿生成完成",
                severity="info" if coverage_review.status == "pass" else "warning",
            )
        )
        db.commit()
        return {"status": "succeeded", "block_count": len(blocks)}
    except Exception as exc:  # noqa: BLE001 - record and surface via task row
        if db.is_active:
            db.rollback()
        error_code = "BUSINESS_DRAFT_GENERATION_BLOCKED" if isinstance(exc, BusinessDraftError) else "BUSINESS_DRAFT_GENERATION_FAILED"
        task = db.get(AsyncTask, task_uuid)
        if task is not None:
            task.status = "failed"
            task.progress = 100
            task.error_code = error_code
            task.error_message = str(exc)[:1000]
            task.finished_at = datetime.now(UTC)
            db.add(
                AuditLog(
                    tenant_id=task.tenant_id,
                    project_id=task.project_id,
                    section_id=task.section_id,
                    actor_user_id=task.created_by,
                    actor_type="system",
                    action="business_draft.context_pack_generate_task_failed",
                    object_type="async_task",
                    object_id=task.id,
                    after_json={"error_code": error_code, "error_message": str(exc)[:1000]},
                    reason="异步 ContextPack 草稿生成失败，不保存为有效草稿",
                    severity="warning",
                )
            )
            db.commit()
        return {"status": "failed", "error_code": error_code}
