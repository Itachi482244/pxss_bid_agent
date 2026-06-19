from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from app.services.evidence_policy import requires_enterprise_evidence


Automation = Literal["auto", "human", "deny"]


class CompliancePolicyItem(Protocol):
    item_type: str
    requirement_text: str
    response_suggestion: str | None
    status: str
    risk_level: str
    is_mandatory: bool
    confidence_score: Decimal | None
    source_chunk_id: object | None
    explanation_json: dict | None


class QualificationEvaluationLike(Protocol):
    evaluation_status: str
    is_blocking: bool
    risk_level: str


@dataclass(frozen=True)
class ActionPolicy:
    action: str
    default_automation: Automation
    note: str = ""


ACTION_POLICIES: dict[str, ActionPolicy] = {
    "agent_matrix_low_risk_pass": ActionPolicy(
        "agent_matrix_low_risk_pass",
        "auto",
        "低风险、来源明确，仅记录 Agent 自动核验，不改变业务状态。",
    ),
    "qualification_evaluation_preserved": ActionPolicy(
        "qualification_evaluation_preserved",
        "auto",
        "已人工确认且结果未变化的资格评估项保持确认。",
    ),
    "qualification_decision_preserved": ActionPolicy(
        "qualification_decision_preserved",
        "auto",
        "已人工确认的 Go/No-Go 结论保持确认。",
    ),
    "confirm_matrix_item": ActionPolicy("confirm_matrix_item", "human"),
    "review_technical_response": ActionPolicy("review_technical_response", "human"),
    "accept_evidence_binding": ActionPolicy("accept_evidence_binding", "human"),
    "missing_evidence": ActionPolicy("missing_evidence", "human"),
    "review_qualification_evaluation": ActionPolicy("review_qualification_evaluation", "human"),
    "confirm_qualification_decision": ActionPolicy("confirm_qualification_decision", "human"),
    "review_draft_block": ActionPolicy("review_draft_block", "human"),
    "ack_llm_technical_advice": ActionPolicy(
        "ack_llm_technical_advice",
        "human",
        "只读 LLM 技术建议，采纳仅关闭建议，不确认技术响应。",
    ),
    "ack_llm_draft_advice": ActionPolicy(
        "ack_llm_draft_advice",
        "human",
        "只读 LLM 草稿建议，采纳仅关闭建议，不批准草稿 block。",
    ),
}


def policy_for(action: str) -> ActionPolicy:
    return ACTION_POLICIES.get(action, ActionPolicy(action, "deny", "未声明的 Agent 动作默认拒绝。"))


def is_technical_item(item: CompliancePolicyItem) -> bool:
    text = f"{item.requirement_text}\n{item.response_suggestion or ''}"
    return item.item_type in {"technical_response", "scoring"} or (
        item.item_type == "other"
        and any(signal in text for signal in ("技术", "设备", "参数", "验收", "净化", "洁净"))
    )


def matrix_confidence(item: CompliancePolicyItem, evidence_count: int) -> Decimal:
    if item.confidence_score is not None:
        return item.confidence_score.quantize(Decimal("0.0001"))
    score = Decimal("0.7200")
    if item.source_chunk_id is not None:
        score += Decimal("0.0800")
    if item.status == "confirmed":
        score += Decimal("0.1200")
    if evidence_count:
        score += Decimal("0.0400")
    if item.risk_level == "high":
        score -= Decimal("0.2200")
    elif item.risk_level == "medium":
        score -= Decimal("0.0700")
    if item.is_mandatory:
        score -= Decimal("0.1600")
    if item.item_type in {"qualification", "deadline", "technical_response", "scoring"}:
        score -= Decimal("0.1000")
    return max(Decimal("0.0000"), min(Decimal("1.0000"), score)).quantize(Decimal("0.0001"))


def matrix_escalation_reasons(item: CompliancePolicyItem, evidence_count: int) -> list[str]:
    reasons: list[str] = []
    explanation = item.explanation_json or {}
    if item.source_chunk_id is None:
        reasons.append("缺少原文来源，不能自动放行")
    if item.risk_level == "high":
        reasons.append("高风险条款必须人工核验")
    if item.is_mandatory:
        reasons.append("强制响应项必须人工确认")
    if item.item_type == "qualification":
        reasons.append("资格类条款会影响参标结论")
    if item.item_type == "deadline":
        reasons.append("截止时间/关键日期类条款必须人工确认")
    if is_technical_item(item):
        reasons.append("技术或评分项需要业务/技术人员复核")
    if item.status == "needs_material":
        reasons.append("当前标记为缺材料")
    if requires_enterprise_evidence(item) and evidence_count == 0:
        reasons.append("缺少企业资料证据")
    if explanation.get("needs_human_review"):
        reasons.append("抽取规则标记需要人工复核")
    return list(dict.fromkeys(reasons))


def severity_for_compliance_item(item: CompliancePolicyItem, reasons: list[str]) -> str:
    if item.risk_level == "high" and (item.is_mandatory or item.item_type == "qualification"):
        return "critical"
    if item.risk_level == "high" or item.is_mandatory or item.item_type in {"qualification", "deadline"}:
        return "high"
    if reasons or item.risk_level == "medium" or is_technical_item(item):
        return "medium"
    return "low"


def confirmation_requires_source_verified(item: CompliancePolicyItem) -> bool:
    return item.risk_level == "high" or item.is_mandatory or item.item_type == "qualification"


class AgentActionPolicy:
    """Context-aware action policy for Agent assist review items.

    The action name is only the first dimension.  Some decisions, such as source
    verification and qualification auto-pass, depend on the target object.
    """

    def policy_for(self, action: str) -> ActionPolicy:
        return policy_for(action)

    def automation_for(self, action: str, target: object | None = None) -> Automation:
        if action == "review_qualification_evaluation" and target is not None:
            return "human" if self.qualification_evaluation_requires_human(target) else "auto"
        return self.policy_for(action).default_automation

    def requires_human(self, action: str, target: object | None = None) -> bool:
        return self.automation_for(action, target) != "auto"

    def requires_source_verified(self, action: str, target: object | None = None) -> bool:
        if action not in {"confirm_matrix_item", "review_technical_response"}:
            return False
        if target is None:
            return False
        return confirmation_requires_source_verified(target)  # type: ignore[arg-type]

    def matrix_confidence(self, item: CompliancePolicyItem, evidence_count: int) -> Decimal:
        return matrix_confidence(item, evidence_count)

    def matrix_escalation_reasons(
        self,
        item: CompliancePolicyItem,
        evidence_count: int,
    ) -> list[str]:
        return matrix_escalation_reasons(item, evidence_count)

    def severity_for_compliance_item(
        self,
        item: CompliancePolicyItem,
        reasons: list[str],
    ) -> str:
        return severity_for_compliance_item(item, reasons)

    def qualification_evaluation_requires_human(self, evaluation: object) -> bool:
        target = evaluation  # keep attribute access local for Protocol friendliness
        return (
            getattr(target, "evaluation_status") != "satisfied"
            or bool(getattr(target, "is_blocking"))
            or getattr(target, "risk_level") in {"medium", "high"}
        )

    def qualification_evaluation_severity(self, evaluation: QualificationEvaluationLike) -> str:
        if evaluation.is_blocking or evaluation.evaluation_status == "not_satisfied":
            return "critical"
        if evaluation.risk_level == "high":
            return "high"
        if self.qualification_evaluation_requires_human(evaluation):
            return "medium"
        return "low"


DEFAULT_ACTION_POLICY = AgentActionPolicy()
