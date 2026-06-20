from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Literal, Protocol

from app.services.agent.policy import ReviewTier, is_technical_item, matrix_confidence
from app.services.evidence_policy import requires_enterprise_evidence


EvidenceOutcome = Literal["bound_active", "pre_accept_candidate", "blocked"]

AUTO_PASS_CONFIDENCE = Decimal("0.8800")
STRONG_SIM = Decimal("0.8800")
VALID_SIM = Decimal("0.6500")
DELTA_SIM = Decimal("0.0800")


class ComplianceClassifierItem(Protocol):
    item_type: str
    requirement_text: str
    response_suggestion: str | None
    status: str
    risk_level: str
    is_mandatory: bool
    confidence_score: Decimal | None
    source_chunk_id: object | None
    explanation_json: dict | None


class MaterialCandidate(Protocol):
    material: object
    confidence_score: float


@dataclass(frozen=True)
class EvidenceClassification:
    outcome: EvidenceOutcome
    tier: ReviewTier
    reasons: list[str]
    selected_candidate: object | None = None
    top1: Decimal | None = None
    top2: Decimal | None = None


@dataclass(frozen=True)
class ItemClassification:
    tier: ReviewTier
    is_disqualifying: bool
    reasons: list[str]
    confidence: Decimal
    evidence_outcome: EvidenceOutcome


TIER_RANK: dict[ReviewTier, int] = {
    "silent": 0,
    "pre_accepted": 1,
    "blocking": 2,
}


def is_disqualifying_item(item: ComplianceClassifierItem) -> bool:
    if item.item_type in {"qualification", "deadline"}:
        return True
    if item.risk_level == "high":
        return True
    if item.is_mandatory and item.risk_level in {"medium", "high"}:
        return True
    return False


def _candidate_similarity(candidate: MaterialCandidate) -> Decimal:
    return Decimal(str(candidate.confidence_score)).quantize(Decimal("0.0001"))


def _candidate_material(candidate: MaterialCandidate) -> object:
    return candidate.material


def _material_is_bindable(material: object) -> bool:
    return (
        getattr(material, "verification_status", None) == "confirmed"
        and getattr(material, "data_level", None) in {"public", "internal"}
    )


def classify_evidence_candidates(
    item: ComplianceClassifierItem,
    *,
    has_active_binding: bool,
    candidates: Iterable[MaterialCandidate] = (),
) -> EvidenceClassification:
    if has_active_binding or not requires_enterprise_evidence(item):
        return EvidenceClassification(
            outcome="bound_active",
            tier="silent",
            reasons=["证据条件已闭合"],
        )

    bindable_candidates = [
        candidate
        for candidate in candidates
        if _material_is_bindable(_candidate_material(candidate))
    ]
    bindable_candidates.sort(key=_candidate_similarity, reverse=True)
    if not bindable_candidates:
        return EvidenceClassification(
            outcome="blocked",
            tier="blocking",
            reasons=["无通过硬门槛的证据候选"],
        )

    top1_candidate = bindable_candidates[0]
    top1 = _candidate_similarity(top1_candidate)
    top2 = _candidate_similarity(bindable_candidates[1]) if len(bindable_candidates) > 1 else Decimal("0.0000")

    if is_disqualifying_item(item):
        return EvidenceClassification(
            outcome="blocked",
            tier="blocking",
            reasons=["废标级证据只推荐候选，需人工采纳"],
            selected_candidate=top1_candidate,
            top1=top1,
            top2=top2,
        )
    if top1 < STRONG_SIM:
        return EvidenceClassification(
            outcome="blocked",
            tier="blocking",
            reasons=["最优证据候选匹配度不足"],
            selected_candidate=top1_candidate,
            top1=top1,
            top2=top2,
        )
    if top2 >= VALID_SIM and top1 - top2 < DELTA_SIM:
        return EvidenceClassification(
            outcome="blocked",
            tier="blocking",
            reasons=["存在近邻歧义证据候选"],
            selected_candidate=top1_candidate,
            top1=top1,
            top2=top2,
        )
    if top2 < VALID_SIM:
        return EvidenceClassification(
            outcome="bound_active",
            tier="silent",
            reasons=["唯一强匹配证据候选"],
            selected_candidate=top1_candidate,
            top1=top1,
            top2=top2,
        )
    return EvidenceClassification(
        outcome="pre_accept_candidate",
        tier="pre_accepted",
        reasons=["明显最优但非唯一证据候选"],
        selected_candidate=top1_candidate,
        top1=top1,
        top2=top2,
    )


def classify_compliance_item(
    item: ComplianceClassifierItem,
    *,
    evidence: EvidenceClassification,
    auto_pass_confidence: Decimal = AUTO_PASS_CONFIDENCE,
) -> ItemClassification:
    confidence = matrix_confidence(item, 1 if evidence.outcome == "bound_active" else 0)
    is_disqualifying = is_disqualifying_item(item)
    reasons: list[str] = []
    explanation = item.explanation_json or {}

    if is_disqualifying:
        reasons.append("废标级或实质性条款必须人工可见")
    if item.risk_level == "high":
        reasons.append("高风险条款必须人工核验")
    if item.is_mandatory:
        reasons.append("强制响应项必须人工确认")
    if item.item_type in {"qualification", "deadline"}:
        reasons.append("资格/关键日期类条款必须人工确认")
    if is_technical_item(item) and item.status != "confirmed":
        reasons.append("技术或评分项需要业务/技术人员复核")
    if item.source_chunk_id is None:
        reasons.append("缺少原文来源")
    if requires_enterprise_evidence(item) and evidence.outcome == "blocked":
        reasons.extend(evidence.reasons)
    if explanation.get("needs_human_review"):
        reasons.append("抽取规则标记需要人工复核")

    if reasons:
        return ItemClassification(
            tier="blocking",
            is_disqualifying=is_disqualifying,
            reasons=list(dict.fromkeys(reasons)),
            confidence=confidence,
            evidence_outcome=evidence.outcome,
        )

    silent_ready = (
        item.risk_level == "low"
        and not item.is_mandatory
        and not is_technical_item(item)
        and item.item_type not in {"qualification", "deadline"}
        and item.source_chunk_id is not None
        and evidence.outcome == "bound_active"
        and not explanation.get("needs_human_review")
        and confidence >= auto_pass_confidence
    )
    if silent_ready:
        return ItemClassification(
            tier="silent",
            is_disqualifying=False,
            reasons=["低风险、来源明确、证据闭合且置信度达标"],
            confidence=confidence,
            evidence_outcome=evidence.outcome,
        )

    if item.risk_level == "low" and item.source_chunk_id is not None and evidence.outcome in {
        "bound_active",
        "pre_accept_candidate",
    }:
        return ItemClassification(
            tier="pre_accepted",
            is_disqualifying=False,
            reasons=evidence.reasons or ["低风险项存在轻微瑕疵，放入预采纳区"],
            confidence=confidence,
            evidence_outcome=evidence.outcome,
        )

    return ItemClassification(
        tier="blocking",
        is_disqualifying=is_disqualifying,
        reasons=["未满足静默或预采纳准入条件"],
        confidence=confidence,
        evidence_outcome=evidence.outcome,
    )


def apply_llm_tier_advice(
    base: ItemClassification,
    *,
    suggested_tier: ReviewTier | None,
    reasons: list[str] | None = None,
) -> ItemClassification:
    if suggested_tier is None:
        return base
    if TIER_RANK[suggested_tier] <= TIER_RANK[base.tier]:
        return base
    advice_reasons = [reason for reason in reasons or [] if reason]
    return ItemClassification(
        tier=suggested_tier,
        is_disqualifying=base.is_disqualifying,
        reasons=list(
            dict.fromkeys(
                [
                    *base.reasons,
                    *(advice_reasons or ["LLM 风险复核建议上调人工可见级别"]),
                ]
            )
        ),
        confidence=base.confidence,
        evidence_outcome=base.evidence_outcome,
    )
