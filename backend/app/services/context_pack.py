from __future__ import annotations

import json
import uuid
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
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
from app.services.business_draft import (
    BusinessDraftError,
    LLMBusinessDraftResponse,
    _json_from_model_text,
    run_fact_checks,
)
from app.services.llm_gateway import LLMGatewayError, chat_completion
from app.services.evidence_policy import (
    enterprise_evidence_not_required,
    enterprise_evidence_not_required_reason,
    requires_enterprise_evidence,
)
from app.services.material_identity import enterprise_material_identity_key, material_snapshot_identity_key
from app.services.material_retrieval import MaterialSearchHit, search_material_hits
from app.services.template_profile import (
    get_template_profile,
    iter_profile_sections,
)

SCHEMA_VERSION = "1.0"
CONTEXT_PACK_CANDIDATE_ITEM_LIMIT = 25
CONTEXT_PACK_CANDIDATE_LIMIT_PER_ITEM = 3
_GAS_TECHNICAL_SECTION_TYPES = {
    "gas_project_understanding",
    "gas_epc_organization",
    "gas_limit_design_cost_control",
    "gas_pipeline_construction_method",
    "gas_material_procurement_quality",
    "gas_trench_connection_backfill_restore",
    "gas_pressure_test_purge_acceptance",
    "gas_existing_pipeline_traffic_safety",
    "gas_schedule_resource_plan",
    "gas_completion_handover_service",
}


def _unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _context_source_text(project: Project, section: BidSection, items: list[ComplianceItem]) -> str:
    values: list[str] = [
        project.name or "",
        project.purchaser or "",
        project.industry_code or "",
        project.region_code or "",
        section.name or "",
        section.code or "",
    ]
    for item in items:
        values.extend(
            [
                item.requirement_text or "",
                item.normalized_requirement or "",
                item.response_suggestion or "",
                item.evidence_text or "",
                item.item_type or "",
            ]
        )
    return "\n".join(value for value in values if value)


def _infer_content_domain(project: Project, section: BidSection, items: list[ComplianceItem]) -> str:
    source_text = _context_source_text(project, section, items)
    gas_signals = ("燃气", "天然气", "管网", "中压", "GB1", "压力管道", "DN90", "DN110", "DN160")
    epc_signals = ("EPC", "工程总承包", "设计、施工", "设计施工")
    if any(signal in source_text for signal in gas_signals) and any(
        signal in source_text for signal in epc_signals
    ):
        return "municipal_gas_pipeline_epc"
    if any(signal in source_text for signal in gas_signals):
        return "municipal_gas_pipeline"
    if any(signal in source_text for signal in epc_signals):
        return "engineering_epc"
    return "engineering_general"


def _engineering_tender_facts(project: Project, section: BidSection, items: list[ComplianceItem]) -> dict[str, Any]:
    source_text = _context_source_text(project, section, items)
    return {
        "pipeline_lengths": _unique_texts(
            re.findall(r"\d+(?:\.\d+)?\s*(?:km|KM|公里)", source_text)
        ),
        "pipe_diameters": _unique_texts(re.findall(r"DN\s*\d{2,4}", source_text)),
        "pressure_levels": _unique_texts(
            re.findall(r"(?:中压\s*[AB]?|低压|高压|设计压力\s*\d+(?:\.\d+)?\s*MPa|\d+(?:\.\d+)?\s*MPa)", source_text)
        ),
        "license_or_standards": _unique_texts(
            re.findall(r"(?:GB\s*\d{4,5}(?:-\d{4})?|GB1\s*级?|压力管道)", source_text)
        ),
        "period_terms": _unique_texts(
            re.findall(r"\d+\s*(?:日历日|日历天|天|日)", source_text)
        ),
        "source_policy": "仅收录招标原文/矩阵条款中出现的工程事实；缺失项不得反推。",
    }


def _content_quality_policy(project: Project, section: BidSection, items: list[ComplianceItem]) -> dict[str, Any]:
    domain = _infer_content_domain(project, section, items)
    policy: dict[str, Any] = {
        "policy_version": "1.0",
        "mode": "evidence_first_bid_writing",
        "domain": domain,
        "source_discipline": [
            "每一处项目事实、工程参数、金额、日期、人员、证书、业绩必须来自招标原文、项目事实或已绑定企业证据。",
            "招标文件未给出的工程量、分段长度、道路街区、管材型号、设备型号、人员数量不得写成确定事实。",
            "人工指令只能改变表达和侧重，不能作为新增事实来源。",
        ],
        "missing_material_strategy": [
            "缺工程量清单时，不得拆分各路段长度、清单工程量或综合单价；写为“以招标人审定的施工图、图纸及工程量清单为准”。",
            "缺评分细则时，不得虚构评分点；只写“按评审办法逐项响应，待补评分细则后细化得分点”。",
            "缺图纸/现场踏勘记录时，不得使用“经实地勘察”“根据详细测量”等确定性表述。",
        ],
        "forbidden_inferences": [
            "不得虚构项目代号或简称。",
            "不得虚构路段/街区分段长度、穿越长度、管径分布比例。",
            "不得虚构施工队伍数量、人员配置、设备型号、材料品牌或单价。",
            "不得把模板化规范、工艺、标准写成已由招标文件确认的事实。",
        ],
        "quality_target": [
            "先准确响应招标条款，再扩写专业方案；宁可保留待确认，也不要用看似完整的内容填充。",
            "章节表达应围绕“我方如何组织、控制、检查、闭环”，避免空泛承诺。",
        ],
    }
    if domain in {"municipal_gas_pipeline", "municipal_gas_pipeline_epc"}:
        policy["industry_focus"] = [
            "围绕 GB1/中压燃气管道、设计压力、DN 管径、特种设备许可、压力试验、吹扫置换、监检验收、竣工资料组织内容。",
            "未明确管材时，不得单独判定为钢管或 PE 管；应写为“管材、连接方式及防腐要求以施工图和工程量清单为准”。",
            "不得把中压 A 管道描述成更高压力等级或长输输气场景；压力等级必须与招标原文一致。",
            "安全风险重点写既有管线保护、沟槽作业、动火作业、交通导改、燃气专项应急处置。",
        ]
        policy["recommended_technical_chapters"] = [
            "项目理解与招标要求响应",
            "EPC 总承包组织与设计施工协同",
            "限额设计与施工图预算控制",
            "中压 GB1 燃气管道施工组织方案",
            "管材、阀门及设备采购质量控制",
            "沟槽开挖、管道连接、防腐、回填及路面恢复",
            "压力试验、吹扫、置换、验收移交",
            "既有管线保护、交通组织与安全文明施工",
            "270 天进度计划与资源配置",
            "缺陷责任期服务和竣工资料移交",
        ]
    return policy


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


def _deduplicated_binding_snapshots(
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
) -> list[dict[str, Any]]:
    snapshots_by_material: dict[str, dict[str, Any]] = {}
    for bindings in bindings_by_item.values():
        for binding in bindings:
            material_key = material_snapshot_identity_key(binding.material_snapshot)
            existing = snapshots_by_material.get(material_key)
            if existing is None:
                existing = _binding_snapshot(binding)
                existing["binding_ids"] = []
                existing["compliance_item_ids"] = []
                snapshots_by_material[material_key] = existing
            binding_id = str(binding.id)
            compliance_item_id = str(binding.compliance_item_id)
            if binding_id not in existing["binding_ids"]:
                existing["binding_ids"].append(binding_id)
            if compliance_item_id not in existing["compliance_item_ids"]:
                existing["compliance_item_ids"].append(compliance_item_id)
    return list(snapshots_by_material.values())


def _candidate_query(item: ComplianceItem, project: Project, section: BidSection) -> str:
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


def _candidate_snapshot(item: ComplianceItem, hit: MaterialSearchHit) -> dict[str, Any]:
    material = hit.material
    return {
        "compliance_item_id": str(item.id),
        "enterprise_material_id": str(material.id),
        "material_name": material.name,
        "material_type": material.material_type,
        "verification_status": material.verification_status,
        "data_level": material.data_level,
        "certificate_no": material.certificate_no,
        "valid_until": material.valid_until,
        "chunk_id": str(hit.chunk.id) if hit.chunk else None,
        "snippet": hit.snippet,
        "confidence_score": hit.confidence_score,
        "base_score": hit.base_score,
        "rerank_score": hit.rerank_score,
        "rerank_used": hit.rerank_used,
        "rerank_fallback_used": hit.rerank_fallback_used,
        "recommend_reason": hit.recommend_reason,
        "matched_terms": hit.matched_terms,
        "confirmation_status": "pending_user_confirmation",
        "can_enter_context_pack": False,
        "reason": "候选证据需人工绑定后才会进入 ContextPack。",
    }


def _candidate_evidence_by_item(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section: BidSection,
    items: list[ComplianceItem],
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    allowed_data_levels = {"public", "internal"}
    verification_statuses = {"confirmed"}
    candidates_by_item: dict[uuid.UUID, list[dict[str, Any]]] = {}
    searched_item_count = 0
    for item in items:
        if not _requires_enterprise_evidence(item) or _evidence_not_required(item):
            continue
        bound_material_keys = {
            material_snapshot_identity_key(binding.material_snapshot)
            for binding in bindings_by_item.get(item.id, [])
        }
        if bound_material_keys:
            continue
        searched_item_count += 1
        if searched_item_count > CONTEXT_PACK_CANDIDATE_ITEM_LIMIT:
            break
        hits = search_material_hits(
            db,
            tenant_id=tenant_id,
            query=_candidate_query(item, project, section),
            verification_statuses=verification_statuses,
            allowed_data_levels=allowed_data_levels,
            limit=CONTEXT_PACK_CANDIDATE_LIMIT_PER_ITEM * 4,
        )
        seen_material_keys: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for hit in hits:
            material_key = enterprise_material_identity_key(hit.material)
            if material_key in seen_material_keys or material_key in bound_material_keys:
                continue
            seen_material_keys.add(material_key)
            candidates.append(_candidate_snapshot(item, hit))
            if len(candidates) >= CONTEXT_PACK_CANDIDATE_LIMIT_PER_ITEM:
                break
        if candidates:
            candidates_by_item[item.id] = candidates
    return candidates_by_item


def _flatten_candidate_evidence(
    candidates_by_item: dict[uuid.UUID, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        candidate
        for item_candidates in candidates_by_item.values()
        for candidate in item_candidates
    ]


def _item_snapshot(
    item: ComplianceItem,
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]],
    candidate_evidence_by_item: dict[uuid.UUID, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    bindings = bindings_by_item.get(item.id, [])
    candidates = (candidate_evidence_by_item or {}).get(item.id, [])
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
        "candidate_evidence_count": len(candidates),
        "candidate_evidence": candidates,
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
        select(ComplianceEvidenceBinding)
        .where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.status == "active",
        )
        .order_by(ComplianceEvidenceBinding.created_at.desc())
    ).all()
    by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]] = {}
    seen_keys_by_item: dict[uuid.UUID, set[str]] = {}
    for binding in bindings:
        material_key = material_snapshot_identity_key(binding.material_snapshot)
        seen_keys = seen_keys_by_item.setdefault(binding.compliance_item_id, set())
        if material_key in seen_keys:
            continue
        seen_keys.add(material_key)
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


def _outline_section_from_def(
    section_def: dict[str, Any],
    matched_items: list[ComplianceItem],
    *,
    title: str | None = None,
    order_index: int | None = None,
) -> dict[str, Any]:
    return {
        "section_type": section_def["section_type"],
        "title": title or section_def["title"],
        "volume_id": section_def.get("volume_id"),
        "volume_title": section_def.get("volume_title"),
        "required": bool(section_def.get("required")),
        "generation_mode": section_def.get("generation_mode"),
        "order_index": section_def.get("order_index") if order_index is None else order_index,
        "required_fields": list(section_def.get("required_fields") or []),
        "covers_item_types": list(section_def.get("covers_item_types") or []),
        "compliance_item_ids": [str(item.id) for item in matched_items],
        "evidence_required": any(_requires_enterprise_evidence(item) for item in matched_items),
        "output_format": "structured_blocks",
        "review_policy": "manual_required",
        "custom": False,
    }


def _custom_outline_section(*, section_type: str, title: str, order_index: int) -> dict[str, Any]:
    return {
        "section_type": section_type,
        "title": title,
        "volume_id": None,
        "volume_title": None,
        "required": False,
        "generation_mode": "manual_placeholder",
        "order_index": order_index,
        "required_fields": [],
        "covers_item_types": [],
        "compliance_item_ids": [],
        "evidence_required": False,
        "output_format": "structured_blocks",
        "review_policy": "manual_required",
        "custom": True,
    }


def _build_outline_plan(
    *,
    profile: dict[str, Any],
    items: list[ComplianceItem],
    section_types: list[str] | None,
    content_quality_policy: dict[str, Any] | None = None,
    outline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    section_defs = {
        section_def["section_type"]: section_def for section_def in iter_profile_sections(profile)
    }
    domain = (content_quality_policy or {}).get("domain")
    gas_technical_enabled = domain in {"municipal_gas_pipeline", "municipal_gas_pipeline_epc"}

    if outline:
        sections: list[dict[str, Any]] = []
        for order, chapter in enumerate(outline, start=1):
            section_type = str(chapter.get("section_type") or "").strip()
            if not section_type:
                raise BusinessDraftError("章节类型不能为空")
            title = (chapter.get("title") or "").strip() or None
            if chapter.get("custom"):
                if not title:
                    raise BusinessDraftError(f"自定义章节需提供标题：{section_type}")
                sections.append(
                    _custom_outline_section(
                        section_type=section_type, title=title, order_index=order * 10
                    )
                )
                continue
            section_def = section_defs.get(section_type)
            if section_def is None:
                raise BusinessDraftError(f"未知章节类型：{section_type}")
            matched_items = _items_for_section(section_def, items)
            sections.append(
                _outline_section_from_def(
                    section_def, matched_items, title=title, order_index=order * 10
                )
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "source": "template_profile + compliance_matrix + manual_outline",
            "sections": sections,
        }

    requested = set(section_types or [])
    sections = []
    for section_def in section_defs.values():
        section_type = section_def["section_type"]
        is_gas_technical = section_type in _GAS_TECHNICAL_SECTION_TYPES
        if is_gas_technical and not (gas_technical_enabled or section_type in requested):
            continue
        matched_items = _items_for_section(section_def, items)
        include = bool(section_def.get("required")) or bool(matched_items)
        if is_gas_technical and gas_technical_enabled:
            include = True
        if requested:
            include = section_type in requested
        if not include:
            continue
        sections.append(_outline_section_from_def(section_def, matched_items))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "template_profile + compliance_matrix",
        "sections": sections,
    }


DIRECTIVE_TYPES = {"style", "emphasis", "mandatory_text"}
AUTHOR_MANDATORY_TEXT_SOURCE = "author_mandatory_text"


def _normalize_directives(
    directives: list[dict[str, Any]] | None,
    *,
    valid_section_types: set[str],
    actor_user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Validate + stamp author directives before they enter a pack snapshot.

    ``scope`` must be ``"pack"`` or one of the pack's section types; type must be
    one of :data:`DIRECTIVE_TYPES`. Each directive gets a stable id plus author /
    timestamp provenance so instruction edits stay auditable.
    """
    if not directives:
        return []
    normalized: list[dict[str, Any]] = []
    stamped_at = datetime.now(UTC).isoformat()
    for raw in directives:
        scope = str(raw.get("scope") or "pack").strip() or "pack"
        directive_type = str(raw.get("directive_type") or "").strip()
        text = str(raw.get("text") or "").strip()
        if directive_type not in DIRECTIVE_TYPES:
            raise BusinessDraftError(f"未知指令类型：{directive_type or '(空)'}")
        if not text:
            raise BusinessDraftError("指令内容不能为空")
        if scope != "pack" and scope not in valid_section_types:
            raise BusinessDraftError(f"指令作用域不在当前目录章节内：{scope}")
        normalized.append(
            {
                "id": str(raw.get("id") or uuid.uuid4()),
                "scope": scope,
                "directive_type": directive_type,
                "text": text,
                "author_user_id": str(actor_user_id),
                "created_at": str(raw.get("created_at") or stamped_at),
            }
        )
    return normalized


def _section_directives(
    directives: list[dict[str, Any]] | None, section_type: str
) -> list[dict[str, Any]]:
    """Directives that apply to a section: pack-scoped + same section_type."""
    return [
        directive
        for directive in directives or []
        if directive.get("scope") in ("pack", section_type)
    ]


def _directive_counts(directives: list[dict[str, Any]] | None) -> dict[str, int]:
    counts = {directive_type: 0 for directive_type in DIRECTIVE_TYPES}
    for directive in directives or []:
        directive_type = directive.get("directive_type")
        if directive_type in counts:
            counts[directive_type] += 1
    return counts


def build_context_pack_preview(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    profile_id: str | None = None,
    section_types: list[str] | None = None,
    outline: list[dict[str, Any]] | None = None,
    directives: list[dict[str, Any]] | None = None,
    actor_user_id: uuid.UUID | None = None,
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
    content_quality_policy = _content_quality_policy(project, section, items)
    tender_engineering_facts = _engineering_tender_facts(project, section, items)
    outline_plan = _build_outline_plan(
        profile=profile,
        items=items,
        section_types=section_types,
        content_quality_policy=content_quality_policy,
        outline=outline,
    )
    valid_section_types = {
        section["section_type"] for section in outline_plan.get("sections") or []
    }
    author_directives = _normalize_directives(
        directives,
        valid_section_types=valid_section_types,
        actor_user_id=actor_user_id or uuid.UUID(int=0),
    )
    candidate_evidence_by_item = _candidate_evidence_by_item(
        db,
        tenant_id=tenant_id,
        project=project,
        section=section,
        items=items,
        bindings_by_item=bindings_by_item,
    )
    candidate_evidence = _flatten_candidate_evidence(candidate_evidence_by_item)
    matrix_items = [
        _item_snapshot(item, bindings_by_item, candidate_evidence_by_item)
        for item in items
    ]
    forbidden_claims = [
        "不得编造未在 ContextPack 中出现的证书编号、人员、业绩、金额或日期。",
        "没有绑定证据的资格/强制事实必须输出待确认占位。",
        "报价清单正文不由 LLM 生成，只允许引用外部报价文件或占位。",
        *content_quality_policy.get("forbidden_inferences", []),
        *content_quality_policy.get("missing_material_strategy", []),
    ]
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
        "author_directives": author_directives,
        "matrix_items": matrix_items,
        "bound_evidence": _deduplicated_binding_snapshots(bindings_by_item),
        "candidate_evidence": candidate_evidence,
        "content_quality_policy": content_quality_policy,
        "tender_engineering_facts": tender_engineering_facts,
        "candidate_evidence_policy": {
            "status": "preview_only_requires_manual_binding",
            "allowed_data_levels": ["public", "internal"],
            "verification_statuses": ["confirmed"],
            "candidate_limit_per_item": CONTEXT_PACK_CANDIDATE_LIMIT_PER_ITEM,
            "searched_item_limit": CONTEXT_PACK_CANDIDATE_ITEM_LIMIT,
        },
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
            "content_quality_policy_version": content_quality_policy.get("policy_version"),
            "source_discipline": content_quality_policy.get("source_discipline") or [],
            "missing_material_strategy": content_quality_policy.get("missing_material_strategy") or [],
            "industry_focus": content_quality_policy.get("industry_focus") or [],
            "forbidden_claims": list(dict.fromkeys(forbidden_claims)),
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
    readiness_json = preview["readiness_json"]
    qualification_codes = _qualification_gate_codes(readiness_json)
    if "qualification.decision_missing" in qualification_codes:
        raise BusinessDraftError("请先运行资格预评估，生成并人工确认参标建议后再确认 ContextPack")
    if "qualification.decision_not_confirmed" in qualification_codes:
        raise BusinessDraftError("参标建议尚未人工确认，请先完成资格预评估确认")

    blocking_checks = [
        check
        for check in readiness_json.get("checks") or []
        if check.get("status") == "block"
        and check.get("code") != "qualification.no_go_confirmed"
    ]
    if blocking_checks:
        details = "；".join(
            f"{check.get('summary', '存在未处理阻断项')} {check.get('action', '')}".strip()
            for check in blocking_checks[:3]
        )
        raise BusinessDraftError(f"ContextPack 仍存在阻断项，暂不能确认：{details}")


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
    candidate_evidence = [
        evidence
        for item in matrix_items
        for evidence in item.get("candidate_evidence") or []
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
    content_quality_policy = global_context.get("content_quality_policy") or {}
    generation_constraints = global_context.get("generation_constraints") or {}
    forbidden_claims = list(
        dict.fromkeys(
            [
                *(generation_constraints.get("forbidden_claims") or []),
                *(content_quality_policy.get("forbidden_inferences") or []),
                *(content_quality_policy.get("missing_material_strategy") or []),
            ]
        )
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
        "tender_engineering_facts": global_context.get("tender_engineering_facts") or {},
        "qualification_decision": global_context.get("qualification_decision"),
        "author_directives": _section_directives(
            global_context.get("author_directives"), outline_section["section_type"]
        ),
        "content_quality_policy": content_quality_policy,
        "generation_constraints": {
            "source_discipline": content_quality_policy.get("source_discipline") or [],
            "missing_material_strategy": content_quality_policy.get("missing_material_strategy") or [],
            "industry_focus": content_quality_policy.get("industry_focus") or [],
            "recommended_technical_chapters": content_quality_policy.get(
                "recommended_technical_chapters"
            )
            or [],
        },
        "matrix_items": matrix_items,
        "bound_evidence": bound_evidence,
        "manual_notes": [
            note
            for note in global_context.get("manual_notes") or []
            if note.get("compliance_item_id") in item_ids
        ],
        "missing_facts": missing_facts,
        "candidate_evidence": candidate_evidence,
        "output_schema": {
            "prompt_version": draft_prompt.prompt_version,
            "schema": draft_prompt.output_schema,
        },
        "forbidden_claims": forbidden_claims,
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
    outline: list[dict[str, Any]] | None = None,
    directives: list[dict[str, Any]] | None = None,
) -> DraftContextPack:
    preview = build_context_pack_preview(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        profile_id=profile_id,
        section_types=section_types,
        outline=outline,
        directives=directives,
        actor_user_id=actor_user_id,
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
                "outline_edited": bool(outline),
                "custom_section_count": sum(
                    1
                    for section in preview["outline_plan_json"]["sections"]
                    if section.get("custom")
                ),
                "directive_count": len(preview["context_json"].get("author_directives") or []),
                "directive_counts": _directive_counts(
                    preview["context_json"].get("author_directives")
                ),
            },
            reason="构建商务/资格草稿生成 ContextPack",
            severity="warning" if context_pack.readiness_status == "block" else "info",
        )
    )
    return context_pack


def update_context_pack_directives(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    directives: list[dict[str, Any]] | None,
) -> DraftContextPack:
    """Replace a confirmed pack's instruction layer via a lightweight rebuild.

    The prior fact snapshot (matrix / evidence / facts / readiness / outline) is
    reused *verbatim* — no upstream re-query — so editing directives can never
    silently pull in new facts. The prior pack and its section packs are
    superseded and a fresh immutable version is produced carrying only the new
    directives, keeping "one generation = one fully reproducible frozen pack".
    """
    prior = db.get(DraftContextPack, context_pack_id)
    if (
        prior is None
        or prior.tenant_id != tenant_id
        or prior.project_id != project_id
        or prior.section_id != section_id
    ):
        raise BusinessDraftError("ContextPack 不属于当前项目标段")
    if prior.status == "superseded":
        raise BusinessDraftError("该 ContextPack 已失效，请基于最新版本编辑指令")

    valid_section_types = {
        section["section_type"]
        for section in (prior.outline_plan_json or {}).get("sections") or []
    }
    normalized = _normalize_directives(
        directives,
        valid_section_types=valid_section_types,
        actor_user_id=actor_user_id,
    )

    prior_section_packs = db.scalars(
        select(DraftSectionContextPack)
        .where(
            DraftSectionContextPack.tenant_id == tenant_id,
            DraftSectionContextPack.context_pack_id == prior.id,
            DraftSectionContextPack.status != "superseded",
        )
        .order_by(DraftSectionContextPack.sort_order.asc())
    ).all()

    new_context_json = dict(prior.context_json or {})
    new_context_json["author_directives"] = normalized

    prior_section_status = {pack.id: pack.status for pack in prior_section_packs}
    prior.status = "superseded"
    for section_pack in prior_section_packs:
        section_pack.status = "superseded"

    context_pack = DraftContextPack(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        profile_id=prior.profile_id,
        profile_version=prior.profile_version,
        schema_version=prior.schema_version,
        status="confirmed",
        readiness_status=prior.readiness_status,
        context_json=_jsonable(new_context_json),
        readiness_json=prior.readiness_json,
        outline_plan_json=prior.outline_plan_json,
        created_by=actor_user_id,
        confirmed_by=actor_user_id,
        confirmed_at=datetime.now(UTC),
    )
    db.add(context_pack)
    db.flush()

    for section_pack in prior_section_packs:
        section_context = dict(section_pack.context_json or {})
        section_context["author_directives"] = _section_directives(
            normalized, section_pack.section_type
        )
        db.add(
            DraftSectionContextPack(
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                context_pack_id=context_pack.id,
                section_type=section_pack.section_type,
                title=section_pack.title,
                sort_order=section_pack.sort_order,
                generation_mode=section_pack.generation_mode,
                status=prior_section_status.get(section_pack.id, "ready"),
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
            action="business_draft.context_pack_directives_updated",
            object_type="draft_context_pack",
            object_id=context_pack.id,
            before_json={
                "context_pack_id": str(prior.id),
                "directive_count": len((prior.context_json or {}).get("author_directives") or []),
            },
            after_json={
                "context_pack_id": str(context_pack.id),
                "directive_count": len(normalized),
                "directive_counts": _directive_counts(normalized),
                "lightweight_rebuild": True,
            },
            reason="编辑 ContextPack 指令层（轻量重建，复用事实快照）",
            severity="info",
        )
    )
    return context_pack


def _chapter_type_for_section(section_type: str) -> str:
    if section_type in _GAS_TECHNICAL_SECTION_TYPES or section_type.startswith("technical_"):
        return "technical_response"
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


_FIELD_LABELS = {
    "agency_name": "招标代理机构",
    "authorized_agent_name": "委托代理人",
    "bid_date": "投标日期",
    "bid_deadline": "投标截止时间",
    "bid_price_amount": "投标报价",
    "bid_security_amount": "投标保证金金额",
    "bid_security_form": "投标保证金形式",
    "bid_section_name": "标段名称",
    "bidder_address": "投标人地址",
    "bidder_name": "投标人",
    "boq_file": "已标价工程量清单",
    "construction_period_days": "计划工期",
    "financial_report_years": "财务报告年度",
    "is_consortium": "联合体投标",
    "legal_representative_name": "法定代表人",
    "legal_representative_title": "职务",
    "performance_bond": "履约担保",
    "project_manager_id_no": "项目负责人身份证号",
    "project_manager_name": "项目负责人",
    "project_name": "项目名称",
    "project_scope": "工程范围",
    "quality_standard": "质量标准",
    "region_code": "项目地区",
    "tender_project_no": "招标项目编号",
    "tenderer_name": "招标人",
    "unified_social_credit_code": "统一社会信用代码",
    "warranty_period": "保修期",
}


def _field_label(field_name: str) -> str:
    return _FIELD_LABELS.get(field_name, "相关信息")


def _format_field_value(field_name: str, value: Any) -> str:
    if field_name == "bid_date":
        return "[请人工填写投标日期]"
    if field_name == "bid_price_amount":
        return "[请人工填写投标报价]"
    if value in (None, ""):
        return f"[请人工补充：{_field_label(field_name)}]"
    text = str(value).strip()
    if not text:
        return f"[请人工补充：{_field_label(field_name)}]"
    if field_name in {"bid_date", "bid_deadline"}:
        match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if match:
            year, month, day = match.groups()
            return f"{year}年{int(month)}月{int(day)}日"
    if field_name == "construction_period_days" and re.fullmatch(r"\d+", text):
        return f"{text}日历日"
    if field_name == "is_consortium":
        lowered = text.lower()
        if lowered in {"false", "no", "0", "否", "不接受", "非联合体"}:
            return "否"
        if lowered in {"true", "yes", "1", "是", "接受", "联合体"}:
            return "是"
    if field_name == "bid_price_amount" and re.fullmatch(r"\d+(?:\.\d+)?", text):
        return f"{text}元"
    return text


def _verified_form_facts(facts: dict[str, Any]) -> dict[str, Any]:
    excluded = {"bid_date", "bid_price_amount", "boq_file"}
    return {
        field_name: value
        for field_name, value in facts.items()
        if field_name not in excluded and value not in (None, "")
    }


# 实质内容章节：接入 LLM 实质撰写（基于条款要求+绑定证据原文+项目事实）。
# 封面/目录、固定法律文书（身份证明/授权委托书）、纯附件占位、外部清单等仍走确定性规则拼接，
# 保证格式可控与可追溯。
_LLM_SUBSTANTIVE_SECTION_TYPES = {
    "bid_letter",
    "bid_commitment",
    "consortium_agreement",
    "boq_pricing_explanation",
    "qualification_performance_summary",
    "bidder_basic_info",
    "scoring_performance_summary",
    "project_management_team",
    "project_manager_resume",
    *_GAS_TECHNICAL_SECTION_TYPES,
}

_QUALIFICATION_LIKE_SECTION_TYPES = {
    "qualification_performance_summary",
    "qualification_other_materials",
    "bidder_basic_info",
    "financial_status",
    "scoring_performance_summary",
    "project_management_team",
    "project_manager_resume",
    "team_supporting_materials",
}

_REVIEW_ONLY_TEXT_REPLACEMENTS = {
    "字段填充草稿": "待填内容",
    "响应草稿": "响应内容",
    "已绑定证据": "证明材料",
    "事实性校验": "事实复核",
    "ContextPack": "资料依据",
    "MVP1.3": "",
    "招标要求：": "要求内容：",
    "招标要求:": "要求内容：",
    "我方响应：": "",
    "我方响应:": "",
    "投标响应：": "",
}


def _sanitize_bid_draft_language(text: str) -> str:
    value = text
    for source, target in _REVIEW_ONLY_TEXT_REPLACEMENTS.items():
        value = value.replace(source, target)
    value = value.replace("招标文件要求及投标响应", "招标文件要求及响应内容")
    value = re.sub(r"燃气项目模拟-[^，。；）\]\s]+", "相关证明材料", value)
    value = re.sub(r"（招标项目编号[:：]\s*section-\d+）", "", value)
    value = re.sub(r"招标项目编号[:：]\s*section-\d+[，,]?", "", value)
    value = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", value)
    return value.strip()


def _facts_label_value_map(facts: dict[str, Any]) -> dict[str, str]:
    """把项目事实整理成 {中文标签: 已格式化值}，缺失值保留占位符供 LLM 识别。"""
    result: dict[str, str] = {}
    for field_name in _FIELD_LABELS:
        if field_name in facts:
            result[_field_label(field_name)] = _format_field_value(field_name, facts.get(field_name))
    return result


def _section_writing_guidance(section_type: str) -> str:
    if section_type in _GAS_TECHNICAL_SECTION_TYPES:
        return (
            "撰写燃气管网 EPC 技术标章节正文。必须围绕招标要求、招标原文工程事实摘要和内容质量策略展开；"
            "可以写组织方法、控制流程、检查闭环和资料移交要求，但不得虚构路线分段、工程量清单、管材型号、"
            "材料品牌、设备型号、施工队伍数量、现场踏勘结论或评分细则。"
            "涉及管材、连接、防腐、沟槽尺寸、穿越方式、分段长度、综合单价等未给定信息时，写为以施工图、"
            "图纸、工程量清单和招标人审定资料为准。"
        )
    if section_type == "bid_letter":
        return (
            "撰写一份正式《投标函》。需顺序包含：致招标人；我方已仔细研究招标文件（写明项目名称、招标项目编号）"
            "并研究合同条款、已提供图纸及工程量清单；愿以【投标报价】承包本项目的施工、竣工及缺陷保修；"
            "计划工期【计划工期】；质量标准达到【质量标准】；投标有效期；中标后将提交【履约担保】并按规定签订合同；"
            "承诺遵守招标文件全部规定。结尾另起行附：投标人（盖单位章）、法定代表人或其委托代理人（签字或盖章）、日期。"
            "现场踏勘、图纸、工程量清单等资料未在上下文出现时，不得写成已经完成或已经掌握。"
            "所有具体数值一律取自【项目事实】中的实际值；事实中为占位符的，原样保留占位符。"
        )
    if section_type == "bid_commitment":
        return (
            "撰写一份正式《投标承诺书》。以投标人名义，围绕本项目逐条作出真实、有效的郑重承诺"
            "（例如：遵守招投标及工程建设法律法规；所提交资料真实有效、无弄虚作假；中标后按招标文件、投标文件与合同约定履约；"
            "接受招标人及主管部门监督；违反承诺依法担责）。如已绑定证据中含具体承诺事项，应据实融入。结尾附署名与日期。"
        )
    if section_type == "consortium_agreement":
        return (
            "撰写《联合体协议书 / 联合体投标说明》。如为联合体投标，应载明各成员单位名称、牵头人、分工与责任承担方式，"
            "并据【已绑定证据】写明各成员的具体资质或承担内容；如非联合体投标，则明确说明本项目为独立投标、不组成联合体。"
            "信息缺失处保留占位符。"
        )
    if section_type == "boq_pricing_explanation":
        return (
            "撰写《已标价工程量清单及报价说明》。结合项目事实中的投标报价、计划工期、质量标准等，说明报价的编制依据、"
            "范围、价格构成与不平衡报价控制原则等；具体报价数值取自项目事实，缺失处保留占位符。"
            "缺工程量清单时，只能说明以招标人最终发布或审定的工程量清单为准，不得编造清单工程量、综合单价或分项金额。"
        )
    if section_type in _QUALIFICATION_LIKE_SECTION_TYPES or section_type.startswith("qualification"):
        return (
            "撰写资格审查 / 业绩 / 人员类章节正文。对每一条招标资格、业绩或人员要求逐条响应，"
            "明确写出我方对应的资质名称、证书编号、有效期，或类似业绩的项目名称、合同金额、完成时间，"
            "或项目负责人/团队成员的姓名、执业资格、社保业绩等具体信息（这些信息只能取自【已绑定证据】原文），"
            "并给出明确的响应结论（如“满足该项要求”“无偏离”）。"
            "按“招标要求 → 我方响应（具体证据信息）→ 结论”的逐条结构组织，使其成为可逐项核对的实质性响应，而非笼统表态。"
        )
    return (
        "撰写正式的投标文件章节正文，针对每条招标要求逐条作出实质响应，并引用【已绑定证据】中的具体信息，"
        "避免空泛表态。"
    )


def _list_or_placeholder(values: list[str], placeholder: str) -> str:
    return "、".join(values) if values else placeholder


def _gas_engineering_summary(context_json: dict[str, Any]) -> str:
    tender_facts = context_json.get("tender_engineering_facts") or {}
    lengths = _list_or_placeholder(tender_facts.get("pipeline_lengths") or [], "未提供可直接引用的线路长度")
    diameters = _list_or_placeholder(tender_facts.get("pipe_diameters") or [], "未提供可直接引用的管径")
    pressures = _list_or_placeholder(tender_facts.get("pressure_levels") or [], "未提供可直接引用的压力等级/设计压力")
    standards = _list_or_placeholder(tender_facts.get("license_or_standards") or [], "未提供可直接引用的许可/标准信息")
    return (
        f"当前资料可引用的工程事实为：线路规模/长度：{lengths}；管径：{diameters}；"
        f"压力等级/设计压力：{pressures}；许可或标准信息：{standards}。"
    )


def _gas_period_text(context_json: dict[str, Any]) -> str:
    facts = context_json.get("project_facts") or {}
    period = facts.get("construction_period_days")
    if period not in (None, ""):
        return _format_field_value("construction_period_days", period)
    tender_facts = context_json.get("tender_engineering_facts") or {}
    period_terms = tender_facts.get("period_terms") or []
    return period_terms[0] if period_terms else "[请人工补充：计划工期]"


def _gas_quality_text(context_json: dict[str, Any]) -> str:
    facts = context_json.get("project_facts") or {}
    return _format_field_value("quality_standard", facts.get("quality_standard"))


def _gas_technical_section_lines(section_type: str, context_json: dict[str, Any]) -> list[str]:
    facts = context_json.get("project_facts") or {}
    project_name = _format_field_value("project_name", facts.get("project_name"))
    fact_summary = _gas_engineering_summary(context_json)
    period_text = _gas_period_text(context_json)
    quality_text = _gas_quality_text(context_json)
    unknowns = (
        "未在当前资料中明确的施工图、工程量清单、管材、连接方式、防腐等级、分段长度、沟槽尺寸、"
        "穿越方式、材料品牌、设备型号和综合单价，均以招标人最终发布或审定资料为准。"
    )
    if section_type == "gas_project_understanding":
        return [
            f"我方理解《{project_name}》属于燃气管网工程总承包类项目，技术响应应覆盖设计、采购、施工、试验、验收和移交全过程。",
            fact_summary,
            f"本项目计划工期按 {period_text} 控制，质量目标按 {quality_text} 执行；缺失或待确认内容不写成确定事实。",
            unknowns,
        ]
    if section_type == "gas_epc_organization":
        return [
            "我方拟按 EPC 总承包管理思路建立设计、采购、施工、试验、验收和资料移交的一体化协同机制。",
            "设计阶段重点完成招标要求复核、施工图深化配合、接口条件确认和限额目标校核；施工阶段按图纸会审、技术交底、样板确认、过程检查和问题闭环组织实施。",
            "采购、施工和验收计划应与设计成果联动，任何影响工期、质量、安全或造价的变更均按招标文件和合同约定履行确认程序。",
            unknowns,
        ]
    if section_type == "gas_limit_design_cost_control":
        return [
            "限额设计和施工图预算控制以招标文件、合同价格边界、审定施工图和工程量清单为基础。",
            "设计优化应优先围绕管线路由合理性、既有管线避让、施工可实施性、材料设备适配性和运维便利性展开，不以降低安全、质量和验收标准为代价。",
            "涉及工程量、综合单价、暂估价、变更签证和清单调整的内容，均按招标人确认的图纸、清单及合同计价规则执行，不自行拆分或推算金额。",
        ]
    if section_type == "gas_pipeline_construction_method":
        return [
            fact_summary,
            "燃气管道施工组织以测量放线、地下管线探查、沟槽开挖与支护、管道安装、接口质量控制、回填压实、路面恢复和竣工测量为主线。",
            "压力等级、管径、管材、连接方式、防腐及警示标识等技术要求必须与施工图、设计说明和工程量清单一致；未明确管材时不得单独判定为钢管或 PE 管，具体以施工图和工程量清单为准。",
            "中压燃气管道不得写成其他压力等级或长输输气场景，施工、试验和验收按招标文件及现行燃气工程规范执行。",
        ]
    if section_type == "gas_material_procurement_quality":
        return [
            "管材、阀门及设备采购应执行招标文件、设计文件、施工图预算和工程量清单要求，进场前完成规格型号、质量证明文件、检验报告和外观质量核验。",
            "材料设备品牌、型号、规格、数量和单价未在当前资料中给出时，不写成确定配置；采购计划以招标人确认的设计成果和清单为准。",
            "进场材料按报验、见证取样或复验、台账登记、标识保护和不合格品处置流程管理，确保采购资料可追溯并满足验收移交要求。",
        ]
    if section_type == "gas_trench_connection_backfill_restore":
        return [
            "沟槽作业按施工图、专项方案和现场条件组织，重点控制既有管线探查、边坡或支护、降排水、槽底验收和安全防护。",
            "管道连接、防腐、警示带敷设、分层回填、压实检测和路面恢复应按设计及规范要求逐项检查，形成隐蔽验收和过程影像资料。",
            "沟槽尺寸、支护形式、穿越方式、回填材料和路面结构未明确时，均以施工图、工程量清单和现场审批方案为准。",
        ]
    if section_type == "gas_pressure_test_purge_acceptance":
        return [
            fact_summary,
            "压力试验、吹扫、置换和验收移交应按设计文件、专项方案、燃气工程规范及主管部门要求组织，关键参数不得脱离招标原文和施工图自行设定。",
            "试验前完成管线完整性、接口质量、阀门状态、仪表校验、隔离警戒和应急准备检查；试验过程记录压力、时间、环境和异常处置情况。",
            "吹扫、置换、通气和移交阶段重点控制安全隔离、检测记录、验收签认、竣工图和质量资料归档，确保满足运行接收条件。",
        ]
    if section_type == "gas_existing_pipeline_traffic_safety":
        return [
            "既有管线保护以资料核查、探测复核、人工探挖、保护标识、旁站监护和应急处置为主线，禁止在资料不足时直接按经验确定管线位置。",
            "交通组织应结合道路占用、沟槽施工、材料堆放、夜间照明和行人车辆通行条件编制专项措施，并按主管部门审批意见执行。",
            "安全文明施工重点控制动火作业、有限空间、沟槽坍塌、燃气泄漏、机械伤害、临时用电和扬尘噪声，形成检查、整改和复查闭环。",
        ]
    if section_type == "gas_schedule_resource_plan":
        return [
            f"本项目进度计划按 {period_text} 目标组织，采用设计成果、采购到货、施工工作面、试验验收和资料移交联动控制。",
            "资源配置应依据施工图、工程量清单、现场条件和审批后的施工组织设计确定；当前资料未明确时，不预设施工队伍数量、设备型号或分段工期。",
            "进度控制采用里程碑计划、周计划滚动、关键线路复核和滞后纠偏机制，重点保障设计确认、材料采购、沟槽作业、管道安装、试验置换和竣工移交节点。",
        ]
    if section_type == "gas_completion_handover_service":
        return [
            "竣工资料移交应围绕施工图会审、设计变更、材料报验、隐蔽验收、压力试验、吹扫置换、质量评定、竣工图和验收签认文件形成完整闭环。",
            "缺陷责任期服务按招标文件和合同约定执行，建立响应、核查、维修、复验和归档机制，保障燃气管网运行接收后的质量追溯。",
            "保修期限、服务范围和响应时限未在当前资料中明确时，保留待确认并以合同及招标文件最终约定为准。",
        ]
    return [
        f"我方将按《{project_name}》招标文件、设计文件和合同要求组织本章技术响应。",
        fact_summary,
        unknowns,
    ]


def _substantive_section_messages(
    section_pack: DraftSectionContextPack,
    project: Project,
    rule_draft: str,
) -> list[dict[str, str]]:
    context_json = section_pack.context_json or {}
    facts = context_json.get("project_facts") or {}
    tender_engineering_facts = context_json.get("tender_engineering_facts") or {}
    matrix_items = context_json.get("matrix_items") or []
    content_quality_policy = context_json.get("content_quality_policy") or {}
    generation_constraints = context_json.get("generation_constraints") or {}
    missing_facts = context_json.get("missing_facts") or []
    forbidden_claims = context_json.get("forbidden_claims") or []

    requirements: list[dict[str, Any]] = []
    for item in matrix_items[:40]:
        evidence: list[dict[str, Any]] = []
        for bound in (item.get("bound_evidence") or [])[:5]:
            evidence.append(
                {
                    "证据名称": bound.get("material_name"),
                    "证书编号": bound.get("certificate_no"),
                    "有效期至": bound.get("valid_until"),
                    "证据原文": (bound.get("evidence_text") or "").strip()[:600],
                }
            )
        requirements.append(
            {
                "招标要求": item.get("requirement_text") or item.get("source_quote"),
                "招标原文摘录": item.get("source_quote") or item.get("evidence_text"),
                "要求类型": item.get("item_type"),
                "是否实质性条款": bool(item.get("is_mandatory")),
                "需企业证据": bool(item.get("enterprise_evidence_required")),
                "已绑定证据": evidence,
            }
        )

    facts_map = _facts_label_value_map(facts)
    guidance = _section_writing_guidance(section_pack.section_type)
    return [
        {
            "role": "system",
            "content": (
                "你是资深中文工程投标文件撰写专家，负责撰写正式商务标书的章节正文。\n"
                "铁律（必须严格遵守）：\n"
                "1. 只能使用【项目事实】【招标要求与已绑定证据】中明确给出的信息；严禁编造或臆测任何企业名称、"
                "资质名称、证书编号、人员姓名、金额、日期、业绩等事实。\n"
                "2. 任何无法从给定信息确认的关键值，必须原样保留形如 [请人工补充：xxx] 或 [请人工填写xxx] 的占位符，"
                "不得用虚构内容替换。\n"
                "3. 禁止输出无信息量的空泛套话（例如“我方承诺全面响应招标文件的实质性要求”这类不含具体信息的句子）；"
                "每一句都要承载针对本条款或本章节的实质内容。\n"
                "4. 针对每条招标要求逐条作出实质响应，并在响应中引用对应已绑定证据中的具体信息"
                "（资质名称、证书编号、业绩名称与金额、有效期等）。\n"
                "5. 工程参数、工程量、管径、压力等级、道路/片区分段、材料型号、设备型号、规范编号、项目编号等"
                "必须来自输入信息；输入未给出时必须写为待确认或以施工图、图纸、工程量清单为准。\n"
                "6. 未提供工程量清单、评分细则、图纸或现场踏勘记录时，不得虚构清单、得分点、图纸内容，"
                "不得使用“经实地勘察”“根据详细测量”等确定性表述。\n"
                "7. 如为燃气管网项目，不得把中压 A / 0.4MPa 描述为更高压力等级或长输输气场景；未明确管材时不得判定为钢管或 PE 管。\n"
                "8. 正文不得出现“已绑定证据”“ContextPack”“响应草稿”等系统内部术语，应写为正式标书语言。\n"
                "9. 使用正式、规范的中文投标文件书面语。\n"
                '只输出 JSON：{"content_text": "章节正文"}，不要输出任何解释性文字。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"项目名称：{project.name}\n"
                f"章节标题：{section_pack.title}\n"
                f"章节类型：{section_pack.section_type}\n\n"
                f"【写作要求】\n{guidance}\n\n"
                f"【项目事实】\n{json.dumps(facts_map, ensure_ascii=False, indent=2)}\n\n"
                f"【招标原文工程事实摘要】\n{json.dumps(tender_engineering_facts, ensure_ascii=False, indent=2)}\n\n"
                f"【招标要求与已绑定证据】\n{json.dumps(requirements, ensure_ascii=False, indent=2)}\n\n"
                f"【缺失事实/待补资料】\n{json.dumps(missing_facts, ensure_ascii=False, indent=2)}\n\n"
                f"【内容质量策略】\n{json.dumps(content_quality_policy, ensure_ascii=False, indent=2)}\n\n"
                f"【章节生成约束】\n{json.dumps(generation_constraints, ensure_ascii=False, indent=2)}\n\n"
                f"【禁写项】\n{json.dumps(forbidden_claims, ensure_ascii=False, indent=2)}\n\n"
                "【规则版骨架草稿（仅供参考章节结构与固定格式，请勿照抄其中的空泛套话）】\n"
                f"{rule_draft}\n\n"
                '请据此撰写本章节正文，输出 JSON：{"content_text":"..."}'
            ),
        },
    ]


def _compose_section_with_llm(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    section_pack: DraftSectionContextPack,
    rule_draft: str,
) -> str | None:
    """对代表章节调用 LLM 进行实质撰写，失败时返回 None 以回退规则版。"""
    context_json = section_pack.context_json or {}
    matrix_items = context_json.get("matrix_items") or []
    messages = _substantive_section_messages(section_pack, project, rule_draft)
    try:
        result = chat_completion(
            db,
            tenant_id=tenant_id,
            project_id=project.id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            task_type="business_draft_generation",
            prompt_version="business-draft-section-substantive@2026-06-14",
            messages=messages,
            complexity="complex" if len(matrix_items) >= 6 else "simple",
            temperature=0.2,
            response_format={"type": "json_object"},
            evidence_refs={
                "compliance_item_ids": [
                    str(item["compliance_item_id"])
                    for item in matrix_items
                    if item.get("compliance_item_id")
                ],
            },
        )
        parsed = LLMBusinessDraftResponse.model_validate(_json_from_model_text(result.content))
        text = parsed.content_text.strip()
        return _sanitize_bid_draft_language(text) or None
    except (LLMGatewayError, ValidationError, ValueError, KeyError, TypeError):
        return None


def _fact_value(facts: dict[str, Any], field_name: str) -> str:
    return _format_field_value(field_name, facts.get(field_name))


def _section_value_lines(context_json: dict[str, Any], required_fields: list[str]) -> list[str]:
    facts = context_json.get("project_facts") or {}
    lines: list[str] = []
    for field_name in required_fields:
        lines.append(f"{_field_label(field_name)}：{_fact_value(facts, field_name)}")
    return lines


def _section_fixed_form_lines(
    section_type: str,
    title: str,
    facts: dict[str, Any],
    required_fields: list[str],
) -> list[str]:
    value = lambda field_name: _fact_value(facts, field_name)
    common_signature = [
        f"投标人：{value('bidder_name')}（盖单位章）",
        f"法定代表人或其委托代理人：{value('legal_representative_name')}（签字或盖章）",
        f"日期：{value('bid_date')}",
    ]
    if section_type == "business_cover":
        return [
            "投 标 文 件",
            f"项目名称：{value('project_name')}",
            f"标段名称：{value('bid_section_name')}",
            "文件内容：商务标",
            f"投标人：{value('bidder_name')}（盖单位章）",
            f"法定代表人或其委托代理人：{value('legal_representative_name')}（签字或盖章）",
            f"日期：{value('bid_date')}",
        ]
    if section_type == "business_directory":
        return [
            "目录",
            "一、法定代表人身份证明书",
            "二、授权委托书",
            "三、投标函及投标函附录",
            "四、投标保证金",
            "五、投标承诺书",
            "六、已标价工程量清单及报价说明",
            "七、资格审查资料",
            "八、招标文件要求提交的其他资料",
        ]
    if section_type == "legal_representative_identity":
        return [
            f"{value('bidder_name')}：",
            f"{value('legal_representative_name')}，职务：{value('legal_representative_title')}，"
            f"系我单位法定代表人。",
            "特此证明。",
            "",
            f"投标人地址：{value('bidder_address')}",
            *common_signature,
        ]
    if section_type == "authorization_letter":
        return [
            f"本人 {value('legal_representative_name')} 系 {value('bidder_name')} 的法定代表人，"
            f"现委托 {value('authorized_agent_name')} 为我方代理人。",
            f"代理人根据授权，以我方名义签署、澄清、说明、补正、递交、撤回、修改"
            f"《{value('project_name')}》投标文件、签订合同和处理有关事宜，其法律后果由我方承担。",
            "委托期限：自本授权委托书签署之日起至本项目投标有效期届满。",
            "代理人无转委托权。",
            "",
            *common_signature,
        ]
    if section_type == "bid_letter":
        return [
            f"致：{value('tenderer_name')}",
            f"1. 我方已仔细研究《{value('project_name')}》招标文件及有关补充文件，"
            "愿按招标文件规定承担本项目相应工作。",
            f"2. 我方投标报价为：{value('bid_price_amount')}；计划工期："
            f"{value('construction_period_days')}；质量标准：{value('quality_standard')}。",
            f"3. 我方拟派项目负责人为：{value('project_manager_name')}。",
            "4. 我方承诺投标文件所载资料真实、准确、完整，并响应招标文件的实质性要求。",
            "5. 如我方中标，我方承诺按招标文件和合同约定履行全部义务。",
            "",
            *common_signature,
        ]
    if section_type == "bid_letter_appendix":
        return [
            "投标函附录",
            f"计划工期：{value('construction_period_days')}",
            f"质量标准：{value('quality_standard')}",
            f"保修期：{value('warranty_period')}",
            f"履约担保：{value('performance_bond')}",
        ]
    if section_type == "bid_security":
        return [
            "我方已按招标文件要求提交投标保证金。",
            f"投标保证金金额：{value('bid_security_amount')}",
            f"投标保证金形式：{value('bid_security_form')}",
            "投标保证金凭证详见本投标文件所附资料。",
        ]
    if section_type == "bid_commitment":
        return [
            f"我方作为《{value('project_name')}》投标人，郑重承诺如下：",
            "一、严格遵守国家和地方有关招标投标、工程建设、质量安全和廉洁从业的法律法规。",
            "二、投标文件所提交的资料真实、有效，不存在弄虚作假或以他人名义投标情形。",
            "三、若我方中标，将按招标文件、投标文件和合同约定组织实施，接受招标人及有关主管部门监督。",
            "四、如违反上述承诺，我方愿依法承担相应责任。",
            "",
            *common_signature,
        ]
    if section_type == "consortium_agreement":
        consortium = value("is_consortium")
        if consortium == "否":
            return [
                "我方确认本项目不以联合体形式投标。",
                "本投标文件由我方独立提交，相关法律责任由我方自行承担。",
                "",
                *common_signature,
            ]
        return [
            f"联合体投标情况：{consortium}",
            "联合体协议及各成员职责分工应按招标文件格式另行签署并随投标文件提交。",
        ]
    if section_type == "bid_price_cover":
        return [
            "投标总价",
            f"项目名称：{value('project_name')}",
            f"招标人：{value('tenderer_name')}",
            f"投标总价：{value('bid_price_amount')}",
            f"投标人：{value('bidder_name')}（盖单位章）",
            f"日期：{value('bid_date')}",
        ]
    if section_type == "boq_pricing_explanation":
        return [
            f"我方将依据《{value('project_name')}》招标文件、已提供的设计资料、工程量清单及相关计价规定编制投标报价；"
            "缺少或待确认的计价资料以招标人最终发布或审定文件为准。",
            f"本报价覆盖范围：{value('project_scope')}。",
            f"投标报价以已标价工程量清单汇总金额为准，金额为：{value('bid_price_amount')}。",
            f"我方承诺按招标文件和合同约定达到质量标准：{value('quality_standard')}。",
        ]
    if section_type == "priced_boq":
        return [
            "已标价工程量清单作为本投标文件组成部分另册或随附提交。",
            f"附件名称：{value('boq_file')}",
        ]
    if section_type == "qualification_performance_summary":
        return [
            "资格业绩汇总表",
            f"投标人：{value('bidder_name')}",
            "类似业绩及证明材料按招标文件要求随本投标文件资格审查资料提交。",
        ]
    if section_type == "bidder_basic_info":
        return [
            "投标人基本情况表",
            f"投标人名称：{value('bidder_name')}",
            f"注册地址：{value('bidder_address')}",
            f"统一社会信用代码：{value('unified_social_credit_code')}",
            f"法定代表人：{value('legal_representative_name')}",
        ]
    if section_type in {"project_management_team", "project_manager_resume"}:
        return [
            title,
            f"项目负责人：{value('project_manager_name')}",
            f"身份证号：{value('project_manager_id_no')}",
            "相关执业资格、社保及业绩证明材料详见本投标文件所附资料。",
        ]
    if section_type == "financial_status":
        return [
            "近年财务状况资料按招标文件要求随本投标文件提交。",
            f"报告年度：{value('financial_report_years')}",
        ]
    if section_type in {
        "other_business_materials",
        "qualification_other_materials",
        "team_supporting_materials",
    }:
        return ["本章按招标文件要求汇集并提交相关证明、承诺及补充资料。"]
    return _section_value_lines({"project_facts": facts}, required_fields)


def _normalize_bid_sentence(item: dict[str, Any]) -> str:
    item_type = str(item.get("item_type") or "")
    suggestion = str(item.get("response_suggestion") or "").strip()
    generic_markers = [
        "请在投标文件中逐项响应",
        "绑定对应证据来源",
        "绑定证明材料",
        "企业资质库",
        "人员库",
        "联合体资料",
        "已绑定证据",
        "响应草稿",
        "合规矩阵",
    ]
    defaults = {
        "qualification": "我方具备招标文件规定的相应资格条件，相关证明材料随本投标文件提交。",
        "mandatory_response": "我方承诺全面响应招标文件的实质性要求，并按招标文件及合同约定履行义务。",
        "format": "我方将按招标文件规定的格式、签章、加密和递交流程编制并提交投标文件。",
        "deadline": "我方承诺遵守招标文件规定的投标截止时间、投标有效期及相关时间安排。",
        "scoring": "我方已按评审办法要求编制相关响应资料，具体内容详见本投标文件相应章节。",
        "reference_info": "我方已充分理解招标文件相关说明，并将在履约过程中按招标人要求执行。",
        "other": "我方承诺按招标文件及相关补充文件要求提交本项目所需资料。",
    }
    if not suggestion or any(marker in suggestion for marker in generic_markers):
        suggestion = defaults.get(
            item_type,
            "我方承诺按招标文件要求提交本项目投标文件并履行相应义务。",
        )
    suggestion = re.sub(r"\s+", " ", suggestion).strip()
    suggestion = suggestion.replace(" [请人工补充证据]", "")
    suggestion = suggestion.replace("[请人工补充证据]", "")
    if suggestion and suggestion[-1] not in "。；;":
        suggestion += "。"
    return suggestion


def _item_bid_paragraph(item: dict[str, Any]) -> str:
    evidence = item.get("bound_evidence") or []
    if item.get("enterprise_evidence_required") and not evidence:
        return "本项涉及需由企业资料证明的响应内容，当前未绑定可核验材料，暂不写成已满足结论。[请人工补充相关证明材料]"

    sentence = _normalize_bid_sentence(item)
    parts = [sentence]
    if item.get("enterprise_evidence_required"):
        proof_sentence = "相关证明材料详见本投标文件资格审查资料或附件。"
        if proof_sentence not in sentence:
            parts.append(proof_sentence)
    return "".join(parts)


def _supplement_heading(section_type: str) -> str:
    if section_type in {
        "qualification_performance_summary",
        "qualification_other_materials",
        "bidder_basic_info",
        "project_management_team",
        "project_manager_resume",
        "financial_status",
        "scoring_performance_summary",
        "team_supporting_materials",
    }:
        return "资格审查资料说明："
    if section_type in {"bid_commitment", "authorization_letter", "bid_letter"}:
        return "承诺事项："
    return "补充说明："


def _build_section_draft_content(section_pack: DraftSectionContextPack) -> tuple[str, list[dict[str, Any]]]:
    context_json = section_pack.context_json
    section = context_json.get("section") or {}
    matrix_items = context_json.get("matrix_items") or []
    required_fields = section.get("required_fields") or []
    generation_mode = section.get("generation_mode") or section_pack.generation_mode
    section_type = str(section.get("section_type") or section_pack.section_type)
    title = str(section.get("title") or section_pack.title)
    facts = context_json.get("project_facts") or {}
    form_modes = {
        "fixed_form",
        "structured_table",
        "conditional_form",
        "generated_paragraph",
        "deterministic",
        "attachment_placeholder",
        "external_attachment",
    }
    lines: list[str] = []
    if section_type in _GAS_TECHNICAL_SECTION_TYPES:
        lines.extend(_gas_technical_section_lines(section_type, context_json))
        lines.append("")
    elif generation_mode in form_modes:
        lines.extend(_section_fixed_form_lines(section_type, title, facts, required_fields))
        lines.append("")
    elif generation_mode == "manual_placeholder":
        lines.append(f"[请人工撰写：{title}]")
        lines.append("")
    else:
        project_name = _fact_value(facts, "project_name")
        bidder_name = _fact_value(facts, "bidder_name")
        lines.append(f"我方 {bidder_name} 将按《{project_name}》招标文件要求完成本章节响应。")
        lines.append("")

    refs: list[dict[str, Any]] = []
    if matrix_items:
        lines.append(_supplement_heading(section_type))
    rendered_item_paragraphs: set[str] = set()
    for item in matrix_items:
        evidence = item.get("bound_evidence") or []
        paragraph = _item_bid_paragraph(item)
        paragraph_key = _normalize_bid_sentence(item)
        if paragraph_key not in rendered_item_paragraphs:
            rendered_item_paragraphs.add(paragraph_key)
            lines.append(f"{len(rendered_item_paragraphs)}. {paragraph}")
            lines.append("")
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
    mandatory = [
        directive
        for directive in context_json.get("author_directives") or []
        if directive.get("directive_type") == "mandatory_text"
    ]
    if mandatory:
        lines.append("补充承诺：")
        for directive in mandatory:
            lines.append(str(directive.get("text") or ""))
        lines.append("")
    return _sanitize_bid_draft_language("\n".join(lines).strip()), refs


def _section_level_links(section_pack: DraftSectionContextPack) -> dict[str, Any]:
    """Structural identifiers shared by heading / field / placeholder blocks.

    Structural blocks intentionally carry an empty ``compliance_item_ids`` so the
    coverage review counts an expected matrix item as *covered* only when it owns
    a dedicated per-clause block, never because it appeared in an aggregate list.
    """
    return {
        "context_pack_id": str(section_pack.context_pack_id),
        "section_context_pack_id": str(section_pack.id),
        "section_type": section_pack.section_type,
        "compliance_item_ids": [],
        "evidence_binding_ids": [],
        "enterprise_material_ids": [],
        "source_chunk_ids": [],
    }


def _item_block_content(item: dict[str, Any]) -> str:
    return _item_bid_paragraph(item)


def _add_draft_blocks(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    chapter: BusinessDraftChapter,
    section_pack: DraftSectionContextPack,
) -> list[DraftBlock]:
    """Emit per-clause structured blocks with per-block backlinks (MVP1.3 #4/#5).

    One ``heading`` block per chapter, one field-fill ``table`` (or external
    ``placeholder``) block when the section is form-like, and then one
    ``paragraph`` block per matrix item. Every clause block links back only to
    its own matrix item, source chunk and bound evidence so the review view can
    locate a single clause and the coverage review can reason per item.
    """
    context_json = section_pack.context_json
    section = context_json.get("section") or {}
    generation_mode = section.get("generation_mode") or section_pack.generation_mode
    matrix_items = context_json.get("matrix_items") or []
    missing_facts = context_json.get("missing_facts") or []
    required_fields = section.get("required_fields") or []
    project_facts = context_json.get("project_facts") or {}
    field_missing = [fact for fact in missing_facts if fact.get("field")]

    blocks: list[DraftBlock] = []
    sort_order = 0

    def add_block(**kwargs: Any) -> None:
        nonlocal sort_order
        sort_order += 1
        block = DraftBlock(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            chapter_id=chapter.id,
            section_context_pack_id=section_pack.id,
            sort_order=sort_order,
            **kwargs,
        )
        db.add(block)
        blocks.append(block)

    add_block(
        block_type="heading",
        content_text=chapter.title,
        links_json=_section_level_links(section_pack),
        fact_claims_json=[],
        missing_fact_placeholders_json=[],
        risk_flags_json=[],
        review_status="covered",
    )

    if generation_mode in {"fixed_form", "structured_table", "conditional_form"} and required_fields:
        field_lines = _section_fixed_form_lines(
            section_pack.section_type,
            section_pack.title,
            project_facts,
            required_fields,
        )
        add_block(
            block_type="table",
            content_text="\n".join(field_lines),
            links_json=_section_level_links(section_pack),
            fact_claims_json=[],
            missing_fact_placeholders_json=field_missing,
            risk_flags_json=[],
            review_status="needs_fact" if field_missing else "covered",
        )
    elif generation_mode in {"external_attachment", "attachment_placeholder"}:
        add_block(
            block_type="placeholder",
            content_text="\n".join(
                _section_fixed_form_lines(
                    section_pack.section_type,
                    section_pack.title,
                    project_facts,
                    required_fields,
                )
            ),
            links_json=_section_level_links(section_pack),
            fact_claims_json=[],
            missing_fact_placeholders_json=[],
            risk_flags_json=[],
            review_status="needs_evidence",
        )
    elif generation_mode == "manual_placeholder":
        add_block(
            block_type="placeholder",
            content_text="[请人工撰写本章内容] 本章为人工新增章节，系统不自动生成正文。",
            links_json=_section_level_links(section_pack),
            fact_claims_json=[],
            missing_fact_placeholders_json=[],
            risk_flags_json=[],
            review_status="needs_fact",
        )

    for item in matrix_items:
        item_id = item.get("compliance_item_id")
        evidence = item.get("bound_evidence") or []
        evidence_required = bool(item.get("enterprise_evidence_required"))
        item_links = {
            "context_pack_id": str(section_pack.context_pack_id),
            "section_context_pack_id": str(section_pack.id),
            "section_type": section_pack.section_type,
            "compliance_item_ids": [item_id] if item_id else [],
            "evidence_binding_ids": [
                ref.get("binding_id") for ref in evidence if ref.get("binding_id")
            ],
            "enterprise_material_ids": [
                ref.get("enterprise_material_id")
                for ref in evidence
                if ref.get("enterprise_material_id")
            ],
            "source_chunk_ids": [item.get("source_chunk_id")] if item.get("source_chunk_id") else [],
        }
        item_missing = [
            fact for fact in missing_facts if fact.get("compliance_item_id") == item_id
        ]
        risk_flags = (
            [
                {
                    "compliance_item_id": item_id,
                    "risk_level": item.get("risk_level"),
                    "status": item.get("status"),
                }
            ]
            if item.get("risk_level") == "high" or item.get("status") != "confirmed"
            else []
        )
        if evidence_required and not evidence:
            review_status = "needs_evidence"
        else:
            review_status = "covered"
        add_block(
            block_type="paragraph",
            content_text=_item_block_content(item),
            links_json=item_links,
            fact_claims_json=[
                {
                    "claim_type": "response_suggestion",
                    "compliance_item_id": item_id,
                    "text": item.get("response_suggestion"),
                }
            ],
            missing_fact_placeholders_json=item_missing,
            risk_flags_json=risk_flags,
            review_status=review_status,
        )

    # Author "forced phrasing" (强制措辞) becomes a dedicated, verbatim block that
    # is explicitly marked author-sourced, defaults to needs_confirm so the final
    # preflight forces a per-block human confirmation, and is still fact-checked
    # via the recomposed chapter text (smuggled hard facts cannot backlink).
    for directive in context_json.get("author_directives") or []:
        if directive.get("directive_type") != "mandatory_text":
            continue
        mandatory_links = _section_level_links(section_pack)
        mandatory_links["source"] = AUTHOR_MANDATORY_TEXT_SOURCE
        mandatory_links["directive_id"] = directive.get("id")
        add_block(
            block_type="paragraph",
            content_text=str(directive.get("text") or ""),
            links_json=mandatory_links,
            fact_claims_json=[],
            missing_fact_placeholders_json=[],
            risk_flags_json=[
                {
                    "code": "author_mandatory_text",
                    "summary": "人工强制措辞，需逐条人工确认并通过事实核查后方可导出。",
                    "directive_id": directive.get("id"),
                }
            ],
            review_status="needs_confirm",
        )

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
        content_generator = "template"
        if section_pack.section_type in _LLM_SUBSTANTIVE_SECTION_TYPES:
            llm_text = _compose_section_with_llm(
                db,
                tenant_id=tenant_id,
                project=project,
                section_id=section_id,
                actor_user_id=actor_user_id,
                section_pack=section_pack,
                rule_draft=content_text,
            )
            if llm_text:
                content_text = llm_text
                content_generator = "llm"
        mandatory_texts = [
            str(directive.get("text") or "").strip()
            for directive in section_pack.context_json.get("author_directives") or []
            if directive.get("directive_type") == "mandatory_text"
            and str(directive.get("text") or "").strip()
        ]
        missing_mandatory_texts = [text for text in mandatory_texts if text not in content_text]
        if missing_mandatory_texts:
            content_text = "\n\n".join(
                [
                    content_text.strip(),
                    "补充承诺：",
                    *missing_mandatory_texts,
                ]
            ).strip()
        content_text = _sanitize_bid_draft_language(content_text)
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
                "source": "mvp1.3_context_pack_draft",
                "context_pack_id": str(context_pack.id),
                "section_context_pack_id": str(section_pack.id),
                "profile_id": context_pack.profile_id,
                "profile_version": context_pack.profile_version,
                "verified_form_facts": _jsonable(
                    _verified_form_facts(section_pack.context_json.get("project_facts") or {})
                ),
                "generated_at": datetime.now(UTC).isoformat(),
                "internal_draft": context_pack.readiness_status == "block",
                "content_generator": content_generator,
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
            reason="基于已确认 ContextPack 生成结构化商务/资格草稿",
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
    mandatory_text_pending = [
        block
        for block in blocks
        if (block.links_json or {}).get("source") == AUTHOR_MANDATORY_TEXT_SOURCE
        and block.review_status != "approved"
    ]
    if mandatory_text_pending:
        issues.append(
            {
                "code": "coverage.mandatory_text_needs_confirm",
                "severity": "warn",
                "summary": f"含 {len(mandatory_text_pending)} 处人工强制措辞，需逐条人工确认后方可导出。",
                "block_ids": [str(block.id) for block in mandatory_text_pending[:20]],
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
            "mandatory_text_pending_count": len(mandatory_text_pending),
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
    """Run an async ContextPack draft generation task for the MVP1.3 draft workflow.

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
