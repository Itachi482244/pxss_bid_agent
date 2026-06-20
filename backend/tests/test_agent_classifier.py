from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.agent.classifier import (
    apply_llm_tier_advice,
    classify_compliance_item,
    classify_evidence_candidates,
)


@dataclass
class FakeItem:
    item_type: str = "other"
    requirement_text: str = "提供服务承诺"
    response_suggestion: str | None = None
    status: str = "pending_confirm"
    risk_level: str = "low"
    is_mandatory: bool = False
    confidence_score: Decimal | None = Decimal("0.9500")
    source_chunk_id: object | None = object()
    explanation_json: dict | None = None


@dataclass
class FakeMaterial:
    verification_status: str = "confirmed"
    data_level: str = "internal"


@dataclass
class FakeHit:
    confidence_score: float
    material: FakeMaterial


def test_medium_risk_is_not_silent_even_with_closed_evidence() -> None:
    item = FakeItem(risk_level="medium")
    evidence = classify_evidence_candidates(item, has_active_binding=True)

    classification = classify_compliance_item(item, evidence=evidence)

    assert classification.tier == "blocking"
    assert "未满足静默或预采纳准入条件" in classification.reasons


def test_unique_strong_candidate_is_silent_for_low_risk_requirement() -> None:
    item = FakeItem(requirement_text="企业资质证书")

    evidence = classify_evidence_candidates(
        item,
        has_active_binding=False,
        candidates=[FakeHit(0.93, FakeMaterial())],
    )
    classification = classify_compliance_item(item, evidence=evidence)

    assert evidence.outcome == "bound_active"
    assert evidence.tier == "silent"
    assert classification.tier == "silent"


def test_near_neighbor_candidate_is_blocking() -> None:
    item = FakeItem(requirement_text="企业资质证书")

    evidence = classify_evidence_candidates(
        item,
        has_active_binding=False,
        candidates=[FakeHit(0.93, FakeMaterial()), FakeHit(0.90, FakeMaterial())],
    )

    assert evidence.outcome == "blocked"
    assert evidence.tier == "blocking"
    assert "存在近邻歧义证据候选" in evidence.reasons


def test_obvious_best_non_unique_candidate_is_preaccepted() -> None:
    item = FakeItem(requirement_text="企业资质证书")

    evidence = classify_evidence_candidates(
        item,
        has_active_binding=False,
        candidates=[FakeHit(0.94, FakeMaterial()), FakeHit(0.72, FakeMaterial())],
    )

    assert evidence.outcome == "pre_accept_candidate"
    assert evidence.tier == "pre_accepted"


def test_disqualifying_requirement_never_silently_binds_candidate() -> None:
    item = FakeItem(item_type="qualification", requirement_text="投标人须具备施工资质")

    evidence = classify_evidence_candidates(
        item,
        has_active_binding=False,
        candidates=[FakeHit(0.98, FakeMaterial())],
    )
    classification = classify_compliance_item(item, evidence=evidence)

    assert evidence.tier == "blocking"
    assert classification.tier == "blocking"
    assert classification.is_disqualifying is True


def test_llm_advice_can_only_raise_tier() -> None:
    low_risk_item = FakeItem(requirement_text="提供服务承诺")
    evidence = classify_evidence_candidates(low_risk_item, has_active_binding=True)
    silent_classification = classify_compliance_item(low_risk_item, evidence=evidence)

    raised = apply_llm_tier_advice(
        silent_classification,
        suggested_tier="blocking",
        reasons=["LLM 识别到可能涉及响应承诺边界"],
    )

    assert raised.tier == "blocking"
    assert "LLM 识别到可能涉及响应承诺边界" in raised.reasons
    assert raised.evidence_outcome == silent_classification.evidence_outcome

    medium_item = FakeItem(risk_level="medium")
    blocking_classification = classify_compliance_item(
        medium_item,
        evidence=classify_evidence_candidates(medium_item, has_active_binding=True),
    )
    lowered = apply_llm_tier_advice(
        blocking_classification,
        suggested_tier="silent",
        reasons=["LLM 认为可以放行"],
    )

    assert lowered is blocking_classification
    assert lowered.tier == "blocking"
