from __future__ import annotations

from typing import Protocol


class EvidencePolicyItem(Protocol):
    item_type: str
    requirement_text: str
    response_suggestion: str | None
    status: str
    risk_level: str
    is_mandatory: bool
    explanation_json: dict | None


EVIDENCE_REQUIRED_SIGNALS = (
    "营业执照",
    "资质",
    "资格证",
    "许可证",
    "安全生产",
    "证书",
    "项目负责人",
    "设计负责人",
    "施工负责人",
    "人员",
    "业绩",
    "财务",
    "审计报告",
    "纳税",
    "社保",
    "信誉",
    "联合体协议",
    "授权委托",
)

COMMITMENT_ONLY_SIGNALS = (
    "限额设计",
    "最高投标限价",
    "合同上限价",
    "投标报价",
    "预算不超",
    "不超过",
    "质量标准",
    "综合评估法",
    "电子化招投标",
    "开标现场",
    "解密",
    "资格后审",
    "工期要求",
    "缺陷责任期",
)


def _compact_text(item: EvidencePolicyItem) -> str:
    return f"{item.requirement_text}\n{item.response_suggestion or ''}".replace(" ", "")


def has_manual_evidence_not_required(item: EvidencePolicyItem) -> bool:
    explanation = item.explanation_json or {}
    return bool(explanation.get("enterprise_evidence_not_required"))


def manual_evidence_not_required_reason(item: EvidencePolicyItem) -> str | None:
    explanation = item.explanation_json or {}
    reason = explanation.get("enterprise_evidence_not_required_reason")
    return reason if isinstance(reason, str) and reason.strip() else None


def auto_evidence_not_required_reason(item: EvidencePolicyItem) -> str | None:
    text = _compact_text(item)
    if any(signal in text for signal in EVIDENCE_REQUIRED_SIGNALS):
        return None
    if item.item_type in {"deadline", "reference_info", "format", "scoring", "technical_response", "other"}:
        return "该条款属于流程、评分、技术或参考信息，通常不依赖企业资料证据。"
    if item.item_type == "mandatory_response" and any(signal in text for signal in COMMITMENT_ONLY_SIGNALS):
        return "该条款属于商务响应/承诺事项，不依赖企业证照或资质资料。"
    return None


def enterprise_evidence_not_required(item: EvidencePolicyItem) -> bool:
    return has_manual_evidence_not_required(item) or auto_evidence_not_required_reason(item) is not None


def enterprise_evidence_not_required_reason(item: EvidencePolicyItem) -> str | None:
    return manual_evidence_not_required_reason(item) or auto_evidence_not_required_reason(item)


def requires_enterprise_evidence(item: EvidencePolicyItem) -> bool:
    if enterprise_evidence_not_required(item):
        return False
    text = _compact_text(item)
    if item.item_type == "qualification":
        return True
    if any(signal in text for signal in EVIDENCE_REQUIRED_SIGNALS):
        return True
    if item.status == "needs_material":
        return True
    return False
