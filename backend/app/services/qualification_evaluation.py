from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    BidSection,
    ComplianceEvidenceBinding,
    ComplianceItem,
    EnterpriseMaterial,
    Project,
    QualificationDecision,
    QualificationEvaluation,
)


RULES_PATH = Path(__file__).resolve().parents[3] / "data" / "rules" / "qualification_rules.json"
DEFAULT_RULES: dict[str, Any] = {
    "version": "0.1",
    "qualification_grade_order": {
        "特级": 6,
        "一级": 5,
        "甲级": 5,
        "二级": 4,
        "乙级": 4,
        "三级": 3,
        "丙级": 3,
        "四级": 2,
        "丁级": 2,
    },
    "qualification_aliases": {},
    "manual_check_signals": ["联合体", "信用", "黑名单", "处罚", "失信", "财务", "社保", "纳税"],
}


@dataclass(frozen=True)
class EvaluationOutcome:
    requirement_type: str
    extracted_requirement: dict[str, Any]
    evaluation_status: str
    risk_level: str
    is_blocking: bool
    matched_material_id: uuid.UUID | None
    matched_material_name: str | None
    matched_rule_code: str
    rule_version: str
    reason: str
    evidence_text: str | None
    missing_materials: list[str] | None


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _uuid_text(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


def _evaluation_result_changed(
    evaluation: QualificationEvaluation,
    *,
    requirement_text: str,
    outcome: EvaluationOutcome,
) -> bool:
    return any(
        (
            evaluation.requirement_text != requirement_text,
            evaluation.requirement_type != outcome.requirement_type,
            _canonical_json(evaluation.extracted_requirement) != _canonical_json(outcome.extracted_requirement),
            evaluation.evaluation_status != outcome.evaluation_status,
            evaluation.risk_level != outcome.risk_level,
            evaluation.is_blocking != outcome.is_blocking,
            _uuid_text(evaluation.matched_material_id) != _uuid_text(outcome.matched_material_id),
            evaluation.matched_material_name != outcome.matched_material_name,
            evaluation.matched_rule_code != outcome.matched_rule_code,
            evaluation.rule_version != outcome.rule_version,
            evaluation.reason != outcome.reason,
            evaluation.evidence_text != outcome.evidence_text,
            _canonical_json(evaluation.missing_materials) != _canonical_json(outcome.missing_materials),
        )
    )


def load_qualification_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return DEFAULT_RULES
    with RULES_PATH.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    return {**DEFAULT_RULES, **loaded}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def _material_text(material: EnterpriseMaterial) -> str:
    fields = material.structured_fields or {}
    return " ".join(
        str(part or "")
        for part in (
            material.name,
            material.issuing_authority,
            material.certificate_no,
            material.holder_name,
            material.project_name,
            material.amount,
            material.evidence_text,
            json.dumps(fields, ensure_ascii=False) if fields else "",
        )
    )


def _material_evidence(material: EnterpriseMaterial) -> str:
    parts = [
        f"资料：{material.name}",
        f"编号：{material.certificate_no}" if material.certificate_no else None,
        f"有效期至：{material.valid_until.isoformat()}" if material.valid_until else None,
        material.evidence_text,
        f"原始文件：{material.file_name}" if material.file_name else None,
    ]
    return "；".join(part for part in parts if part)


def _grade_from_text(text: str, grade_order: dict[str, int]) -> str | None:
    candidates = sorted(grade_order, key=len, reverse=True)
    for grade in candidates:
        if grade in text:
            return grade
    return None


def _category_from_text(text: str, aliases: dict[str, list[str]]) -> str | None:
    normalized = _normalize_text(text)
    for category, values in aliases.items():
        for alias in [category, *values]:
            if _normalize_text(alias) in normalized:
                return category
    return None


def _is_valid_on_deadline(material: EnterpriseMaterial, deadline: date | None) -> bool | None:
    if material.valid_until is None or deadline is None:
        return None
    return material.valid_until >= deadline


def _deadline_for(project: Project, section: BidSection) -> date | None:
    value = section.bid_deadline_at or project.bid_deadline_at
    return value.date() if value else None


def _status_for_material(material: EnterpriseMaterial, *, otherwise: str = "satisfied") -> str:
    if material.verification_status == "confirmed":
        return otherwise
    if material.verification_status == "expired":
        return "not_satisfied"
    if material.verification_status == "missing_evidence":
        return "needs_material"
    return "pending_confirm"


def _risk_for_status(status: str, mandatory: bool) -> str:
    if status == "not_satisfied":
        return "high" if mandatory else "medium"
    if status == "needs_material":
        return "high" if mandatory else "medium"
    if status == "pending_confirm":
        return "medium" if mandatory else "low"
    return "low"


def _missing_outcome(
    *,
    requirement_type: str,
    rule_code: str,
    rule_version: str,
    missing: str,
    mandatory: bool,
    extracted: dict[str, Any],
) -> EvaluationOutcome:
    return EvaluationOutcome(
        requirement_type=requirement_type,
        extracted_requirement=extracted,
        evaluation_status="needs_material",
        risk_level="high" if mandatory else "medium",
        is_blocking=mandatory,
        matched_material_id=None,
        matched_material_name=None,
        matched_rule_code=rule_code,
        rule_version=rule_version,
        reason=f"企业资料库未找到可用于响应的{missing}。",
        evidence_text=None,
        missing_materials=[missing],
    )


def _find_material(
    materials: list[EnterpriseMaterial],
    *,
    material_type: str,
    signals: list[str],
) -> EnterpriseMaterial | None:
    normalized_signals = [_normalize_text(signal) for signal in signals if signal]
    for material in materials:
        if material.material_type != material_type:
            continue
        text = _normalize_text(_material_text(material))
        if not normalized_signals or any(signal in text for signal in normalized_signals):
            return material
    return None


def _evaluate_license(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    deadline: date | None,
    rule_version: str,
) -> EvaluationOutcome:
    material = _find_material(materials, material_type="license", signals=["营业执照"])
    if material is None:
        material = _find_material(materials, material_type="qualification", signals=["营业执照"])
    if material is None:
        return _missing_outcome(
            requirement_type="business_license",
            rule_code="license.exists",
            rule_version=rule_version,
            missing="营业执照",
            mandatory=item.is_mandatory,
            extracted={"keyword": "营业执照"},
        )
    valid = _is_valid_on_deadline(material, deadline)
    if valid is False:
        status = "not_satisfied"
        reason = "营业执照存在，但有效期未覆盖投标截止时间。"
        rule_code = "certificate.valid_on_deadline"
    else:
        status = _status_for_material(material)
        reason = "已找到营业执照材料；仍需人工确认原件一致性。" if status == "pending_confirm" else "已找到已确认的营业执照材料。"
        rule_code = "license.exists"
    return EvaluationOutcome(
        requirement_type="business_license",
        extracted_requirement={"keyword": "营业执照"},
        evaluation_status=status,
        risk_level=_risk_for_status(status, item.is_mandatory),
        is_blocking=status in {"not_satisfied", "needs_material"} and item.is_mandatory,
        matched_material_id=material.id,
        matched_material_name=material.name,
        matched_rule_code=rule_code,
        rule_version=rule_version,
        reason=reason,
        evidence_text=_material_evidence(material),
        missing_materials=None,
    )


def _evaluate_safety_license(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    deadline: date | None,
    rule_version: str,
) -> EvaluationOutcome:
    material = _find_material(materials, material_type="qualification", signals=["安全生产许可证"])
    if material is None:
        material = _find_material(materials, material_type="license", signals=["安全生产许可证"])
    if material is None:
        return _missing_outcome(
            requirement_type="safety_production_license",
            rule_code="safety_license.exists",
            rule_version=rule_version,
            missing="安全生产许可证",
            mandatory=item.is_mandatory,
            extracted={"keyword": "安全生产许可证"},
        )
    valid = _is_valid_on_deadline(material, deadline)
    status = "not_satisfied" if valid is False else _status_for_material(material)
    reason = (
        "安全生产许可证有效期未覆盖投标截止时间。"
        if status == "not_satisfied"
        else "已找到安全生产许可证材料。"
    )
    return EvaluationOutcome(
        requirement_type="safety_production_license",
        extracted_requirement={"keyword": "安全生产许可证"},
        evaluation_status=status,
        risk_level=_risk_for_status(status, item.is_mandatory),
        is_blocking=status in {"not_satisfied", "needs_material"} and item.is_mandatory,
        matched_material_id=material.id,
        matched_material_name=material.name,
        matched_rule_code="safety_license.exists",
        rule_version=rule_version,
        reason=reason,
        evidence_text=_material_evidence(material),
        missing_materials=None,
    )


def _evaluate_qualification(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    deadline: date | None,
    rules: dict[str, Any],
) -> EvaluationOutcome:
    text = f"{item.requirement_text} {item.normalized_requirement or ''}"
    grade_order: dict[str, int] = rules["qualification_grade_order"]
    aliases: dict[str, list[str]] = rules["qualification_aliases"]
    required_category = _category_from_text(text, aliases)
    required_grade = _grade_from_text(text, grade_order)
    extracted = {
        "qualification_category": required_category,
        "min_grade": required_grade,
        "must_be_valid_on": "bid_deadline",
    }
    candidates = [material for material in materials if material.material_type == "qualification"]
    if required_category:
        candidates = [
            material
            for material in candidates
            if _category_from_text(_material_text(material), {required_category: aliases.get(required_category, [])})
            == required_category
        ]
    if not candidates:
        return _missing_outcome(
            requirement_type="enterprise_qualification",
            rule_code="qualification.exists",
            rule_version=rules["version"],
            missing=required_category or "企业资质证书",
            mandatory=item.is_mandatory,
            extracted=extracted,
        )

    best = candidates[0]
    best_grade = _grade_from_text(_material_text(best), grade_order)
    if required_grade and best_grade:
        if grade_order.get(best_grade, 0) < grade_order.get(required_grade, 0):
            return EvaluationOutcome(
                requirement_type="enterprise_qualification",
                extracted_requirement=extracted | {"matched_grade": best_grade},
                evaluation_status="not_satisfied",
                risk_level="high" if item.is_mandatory else "medium",
                is_blocking=item.is_mandatory,
                matched_material_id=best.id,
                matched_material_name=best.name,
                matched_rule_code="qualification.grade_at_least",
                rule_version=rules["version"],
                reason=f"企业资质等级为{best_grade}，低于招标要求{required_grade}。",
                evidence_text=_material_evidence(best),
                missing_materials=None,
            )
    valid = _is_valid_on_deadline(best, deadline)
    status = "not_satisfied" if valid is False else _status_for_material(best)
    if status == "not_satisfied":
        reason = "企业资质证书有效期未覆盖投标截止时间。"
    elif status == "pending_confirm":
        reason = "已找到可能匹配的企业资质，但资料尚未人工确认。"
    else:
        reason = "企业资质材料匹配资格要求。"
        if required_grade and best_grade:
            reason = f"企业具备{best_grade}资质，满足招标要求{required_grade}及以上。"
    return EvaluationOutcome(
        requirement_type="enterprise_qualification",
        extracted_requirement=extracted | {"matched_grade": best_grade},
        evaluation_status=status,
        risk_level=_risk_for_status(status, item.is_mandatory),
        is_blocking=status in {"not_satisfied", "needs_material"} and item.is_mandatory,
        matched_material_id=best.id,
        matched_material_name=best.name,
        matched_rule_code="qualification.grade_at_least" if required_grade else "qualification.exists",
        rule_version=rules["version"],
        reason=reason,
        evidence_text=_material_evidence(best),
        missing_materials=None,
    )


def _evaluate_personnel(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    rule_version: str,
) -> EvaluationOutcome:
    text = item.requirement_text
    signals = ["项目负责人", "建造师", "注册", "安全B证", "B证", "职称"]
    material = _find_material(materials, material_type="personnel", signals=[s for s in signals if s in text])
    if material is None:
        return _missing_outcome(
            requirement_type="personnel_certificate",
            rule_code="personnel.certificate_exists",
            rule_version=rule_version,
            missing="人员证书或项目负责人材料",
            mandatory=item.is_mandatory,
            extracted={"signals": [s for s in signals if s in text]},
        )
    status = _status_for_material(material)
    return EvaluationOutcome(
        requirement_type="personnel_certificate",
        extracted_requirement={"signals": [s for s in signals if s in text]},
        evaluation_status=status,
        risk_level=_risk_for_status(status, item.is_mandatory),
        is_blocking=status in {"not_satisfied", "needs_material"} and item.is_mandatory,
        matched_material_id=material.id,
        matched_material_name=material.name,
        matched_rule_code="personnel.certificate_exists",
        rule_version=rule_version,
        reason="已找到人员相关材料。" if status == "satisfied" else "已找到人员材料，但仍需人工确认。",
        evidence_text=_material_evidence(material),
        missing_materials=None,
    )


def _evaluate_performance(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    rule_version: str,
) -> EvaluationOutcome:
    text = item.requirement_text
    if "不要求" in text:
        return EvaluationOutcome(
            requirement_type="performance",
            extracted_requirement={"requirement": "not_required"},
            evaluation_status="not_applicable",
            risk_level="low",
            is_blocking=False,
            matched_material_id=None,
            matched_material_name=None,
            matched_rule_code="performance.not_required",
            rule_version=rule_version,
            reason="招标文件明确类似业绩不要求，本项不构成参标阻断。",
            evidence_text=item.evidence_text or item.requirement_text,
            missing_materials=None,
        )
    material = _find_material(materials, material_type="performance", signals=["业绩", "类似"])
    if material is None:
        return _missing_outcome(
            requirement_type="performance",
            rule_code="performance.exists",
            rule_version=rule_version,
            missing="类似业绩证明材料",
            mandatory=item.is_mandatory,
            extracted={"requirement": "required"},
        )
    status = _status_for_material(material)
    return EvaluationOutcome(
        requirement_type="performance",
        extracted_requirement={"requirement": "required"},
        evaluation_status=status,
        risk_level=_risk_for_status(status, item.is_mandatory),
        is_blocking=status in {"not_satisfied", "needs_material"} and item.is_mandatory,
        matched_material_id=material.id,
        matched_material_name=material.name,
        matched_rule_code="performance.exists",
        rule_version=rule_version,
        reason="已找到类似业绩材料。" if status == "satisfied" else "已找到类似业绩材料，但仍需人工确认。",
        evidence_text=_material_evidence(material),
        missing_materials=None,
    )


def evaluate_qualification_item(
    item: ComplianceItem,
    materials: list[EnterpriseMaterial],
    deadline: date | None,
    rules: dict[str, Any],
) -> EvaluationOutcome:
    text = f"{item.requirement_text} {item.normalized_requirement or ''}"
    if any(signal in text for signal in rules["manual_check_signals"]):
        return EvaluationOutcome(
            requirement_type="manual_check",
            extracted_requirement={"signals": [s for s in rules["manual_check_signals"] if s in text]},
            evaluation_status="pending_confirm",
            risk_level="medium" if item.is_mandatory else "low",
            is_blocking=False,
            matched_material_id=None,
            matched_material_name=None,
            matched_rule_code="manual.check_required",
            rule_version=rules["version"],
            reason="该资格项涉及联合体、信用、财务或社保等人工判断事项，需业务负责人或合规人员确认。",
            evidence_text=item.evidence_text or item.requirement_text,
            missing_materials=None,
        )
    if "营业执照" in text:
        return _evaluate_license(item, materials, deadline, rules["version"])
    if "安全生产许可证" in text:
        return _evaluate_safety_license(item, materials, deadline, rules["version"])
    if "业绩" in text or "类似工程" in text:
        return _evaluate_performance(item, materials, rules["version"])
    if any(signal in text for signal in ("项目负责人", "建造师", "注册", "职称", "安全B证", "B证")):
        return _evaluate_personnel(item, materials, rules["version"])
    if "资质" in text:
        return _evaluate_qualification(item, materials, deadline, rules)
    return EvaluationOutcome(
        requirement_type="manual_check",
        extracted_requirement={},
        evaluation_status="pending_confirm",
        risk_level="medium" if item.is_mandatory else "low",
        is_blocking=False,
        matched_material_id=None,
        matched_material_name=None,
        matched_rule_code="manual.check_required",
        rule_version=rules["version"],
        reason="当前资格项尚未命中可自动判断规则，需要人工确认。",
        evidence_text=item.evidence_text or item.requirement_text,
        missing_materials=None,
    )


def _manual_bound_evidence_outcome(
    item: ComplianceItem,
    outcome: EvaluationOutcome,
    binding: ComplianceEvidenceBinding | None,
) -> EvaluationOutcome:
    if binding is None or outcome.evaluation_status != "needs_material":
        return outcome
    snapshot = binding.material_snapshot or {}
    material_name = str(snapshot.get("name") or binding.evidence_text or "已绑定企业资料")
    extracted = {
        **outcome.extracted_requirement,
        "manual_bound_evidence": True,
        "manual_binding_id": str(binding.id),
    }
    return EvaluationOutcome(
        requirement_type=outcome.requirement_type,
        extracted_requirement=extracted,
        evaluation_status="pending_confirm",
        risk_level="medium" if item.is_mandatory else "low",
        is_blocking=False,
        matched_material_id=binding.enterprise_material_id,
        matched_material_name=material_name,
        matched_rule_code=f"{outcome.matched_rule_code}.manual_binding",
        rule_version=outcome.rule_version,
        reason="已人工绑定企业资料证据，但自动规则尚不能判定完全满足资格要求，需人工确认适配性。",
        evidence_text=binding.evidence_text,
        missing_materials=None,
    )


def evaluation_snapshot(evaluation: QualificationEvaluation) -> dict[str, Any]:
    return {
        "id": str(evaluation.id),
        "compliance_item_id": str(evaluation.compliance_item_id),
        "requirement_type": evaluation.requirement_type,
        "evaluation_status": evaluation.evaluation_status,
        "risk_level": evaluation.risk_level,
        "is_blocking": evaluation.is_blocking,
        "matched_material_id": str(evaluation.matched_material_id)
        if evaluation.matched_material_id
        else None,
        "matched_material_name": evaluation.matched_material_name,
        "matched_rule_code": evaluation.matched_rule_code,
        "reason": evaluation.reason,
        "missing_materials": evaluation.missing_materials,
    }


def run_qualification_evaluation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> list[QualificationEvaluation]:
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    if project is None or section is None:
        return []
    rules = load_qualification_rules()
    materials = list(
        db.scalars(
            select(EnterpriseMaterial)
            .where(EnterpriseMaterial.tenant_id == tenant_id)
            .order_by(EnterpriseMaterial.verification_status.asc(), EnterpriseMaterial.updated_at.desc())
        ).all()
    )
    items = list(
        db.scalars(
            select(ComplianceItem)
            .where(
                ComplianceItem.tenant_id == tenant_id,
                ComplianceItem.project_id == project_id,
                ComplianceItem.section_id == section_id,
                ComplianceItem.item_type == "qualification",
                ComplianceItem.deleted_at.is_(None),
            )
            .order_by(ComplianceItem.created_at.asc())
        ).all()
    )
    deadline = _deadline_for(project, section)
    active_bindings = list(
        db.scalars(
            select(ComplianceEvidenceBinding)
            .where(
                ComplianceEvidenceBinding.tenant_id == tenant_id,
                ComplianceEvidenceBinding.project_id == project_id,
                ComplianceEvidenceBinding.section_id == section_id,
                ComplianceEvidenceBinding.status == "active",
            )
            .order_by(ComplianceEvidenceBinding.created_at.desc())
        ).all()
    )
    latest_binding_by_item: dict[uuid.UUID, ComplianceEvidenceBinding] = {}
    for binding in active_bindings:
        latest_binding_by_item.setdefault(binding.compliance_item_id, binding)
    results: list[QualificationEvaluation] = []
    counts = {"satisfied": 0, "not_satisfied": 0, "needs_material": 0, "pending_confirm": 0, "not_applicable": 0}
    for item in items:
        outcome = evaluate_qualification_item(item, materials, deadline, rules)
        outcome = _manual_bound_evidence_outcome(item, outcome, latest_binding_by_item.get(item.id))
        evaluation = db.scalar(
            select(QualificationEvaluation).where(
                QualificationEvaluation.tenant_id == tenant_id,
                QualificationEvaluation.project_id == project_id,
                QualificationEvaluation.section_id == section_id,
                QualificationEvaluation.compliance_item_id == item.id,
            )
        )
        if evaluation is None:
            evaluation = QualificationEvaluation(
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                compliance_item_id=item.id,
                created_by=actor_user_id,
                updated_by=actor_user_id,
                requirement_text=item.requirement_text,
                requirement_type=outcome.requirement_type,
                extracted_requirement=outcome.extracted_requirement,
                evaluation_status=outcome.evaluation_status,
                risk_level=outcome.risk_level,
                is_blocking=outcome.is_blocking,
                matched_material_id=outcome.matched_material_id,
                matched_material_name=outcome.matched_material_name,
                matched_rule_code=outcome.matched_rule_code,
                rule_version=outcome.rule_version,
                reason=outcome.reason,
                evidence_text=outcome.evidence_text,
                missing_materials=outcome.missing_materials,
            )
            db.add(evaluation)
        else:
            confirmation_stale = evaluation.confirmed_by is not None and _evaluation_result_changed(
                evaluation,
                requirement_text=item.requirement_text,
                outcome=outcome,
            )
            evaluation.updated_by = actor_user_id
            evaluation.requirement_text = item.requirement_text
            evaluation.requirement_type = outcome.requirement_type
            evaluation.extracted_requirement = outcome.extracted_requirement
            evaluation.evaluation_status = outcome.evaluation_status
            evaluation.risk_level = outcome.risk_level
            evaluation.is_blocking = outcome.is_blocking
            evaluation.matched_material_id = outcome.matched_material_id
            evaluation.matched_material_name = outcome.matched_material_name
            evaluation.matched_rule_code = outcome.matched_rule_code
            evaluation.rule_version = outcome.rule_version
            evaluation.reason = outcome.reason
            evaluation.evidence_text = outcome.evidence_text
            evaluation.missing_materials = outcome.missing_materials
            if confirmation_stale:
                evaluation.confirmed_by = None
                evaluation.confirmed_at = None
                evaluation.confirm_reason = None
        counts[outcome.evaluation_status] += 1
        results.append(evaluation)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="qualification.evaluation_run",
            object_type="qualification_evaluation",
            object_id=None,
            after_json={"count": len(results), "status_counts": counts, "rule_version": rules["version"]},
            reason="运行参标资格预评估",
            severity="info",
        )
    )
    return results


def refresh_qualification_after_evidence_change(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_type: str = "user",
) -> dict[str, int]:
    evaluations = run_qualification_evaluation(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=actor_user_id,
    )
    active_decisions = list(
        db.scalars(
            select(QualificationDecision).where(
                QualificationDecision.tenant_id == tenant_id,
                QualificationDecision.project_id == project_id,
                QualificationDecision.section_id == section_id,
                QualificationDecision.status != "superseded",
            )
        ).all()
    )
    for decision in active_decisions:
        decision.status = "superseded"
    if active_decisions:
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                action="qualification.decision_invalidated",
                object_type="qualification_decision",
                object_id=None,
                before_json={"decision_ids": [str(item.id) for item in active_decisions]},
                after_json={"reason": "enterprise_evidence_changed"},
                reason="企业资料证据发生变化，原参标建议已失效",
                severity="warning",
            )
        )
    return {
        "evaluation_count": len(evaluations),
        "invalidated_decision_count": len(active_decisions),
    }
