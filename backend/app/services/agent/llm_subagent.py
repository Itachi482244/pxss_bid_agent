from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models import AgentReviewItem
from app.services.agent.progress import budget_display_payload
from app.services.llm_gateway import LLMResult, chat_completion


ReadonlySubagentMode = Literal["technical_response_advice", "l4_style_advice"]
LLM_TECHNICAL_ADVICE_ACTION = "ack_llm_technical_advice"
LLM_DRAFT_ADVICE_ACTION = "ack_llm_draft_advice"
LLM_SUBAGENT_PROMPT_VERSION = "agent_readonly_subagent.v1"
LLM_SUBAGENT_DISALLOWED_TOOLS = (
    "ComplianceConfirmTool",
    "accept_evidence_binding",
    "confirm_qualification_decision",
    "review_qualification_evaluation.accept",
    "export_tender_format_docx",
    "write_business_draft",
)


@dataclass(frozen=True)
class ReadonlyLLMSubagentRequest:
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    actor_user_id: uuid.UUID
    mode: ReadonlySubagentMode
    target_type: Literal["compliance_item", "draft_block"]
    target_id: uuid.UUID
    title: str
    context: dict[str, Any]
    source_refs: dict[str, Any] | None = None
    max_tokens: int = 900


@dataclass(frozen=True)
class ReadonlyLLMSubagentResult:
    mode: ReadonlySubagentMode
    target_type: str
    target_id: uuid.UUID
    summary: str
    recommendations: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    model_invocation_log_id: uuid.UUID | None = None

    @property
    def severity(self) -> str:
        flags = {flag.lower() for flag in self.risk_flags}
        if any(flag in flags for flag in {"blocking", "high", "critical", "废标", "阻断"}):
            return "high"
        if flags:
            return "medium"
        return "medium"


def _json_from_model_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM 子 Agent 必须返回 JSON object。")
    return payload


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _subagent_messages(request: ReadonlyLLMSubagentRequest) -> list[dict[str, str]]:
    mode_label = "技术响应/偏离初判" if request.mode == "technical_response_advice" else "L4 表达润色建议"
    return [
        {
            "role": "system",
            "content": (
                "你是投标 Agent 的只读子 Agent，只能阅读上下文并输出建议 JSON。"
                "禁止写正式稿、禁止导出、禁止绑定证据、禁止确认资格或合规条款、禁止修改数据库。"
                "如果证据不足，必须明确说缺少什么，不能编造证据、页码、指标或工程量。"
                "只返回 JSON object，字段为 summary、recommendations、risk_flags。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "mode": request.mode,
                    "mode_label": mode_label,
                    "target_type": request.target_type,
                    "target_id": str(request.target_id),
                    "title": request.title,
                    "context": request.context,
                    "source_refs": request.source_refs or {},
                    "disallowed_tools": list(LLM_SUBAGENT_DISALLOWED_TOOLS),
                },
                ensure_ascii=False,
                default=str,
            ),
        },
    ]


def run_readonly_llm_subagent(
    db: Session,
    request: ReadonlyLLMSubagentRequest,
) -> ReadonlyLLMSubagentResult:
    """Run the read-only LLM seam through the shared chat gateway.

    This function intentionally accepts no base_url/api_key/provider arguments.
    ``chat_completion`` resolves the same tenant/env chat model config used by
    the main Agent flow.
    """

    result: LLMResult = chat_completion(
        db,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        section_id=request.section_id,
        actor_user_id=request.actor_user_id,
        actor_type="worker",
        task_type="agent_readonly_subagent",
        prompt_version=LLM_SUBAGENT_PROMPT_VERSION,
        messages=_subagent_messages(request),
        complexity="simple",
        temperature=0.0,
        response_format={"type": "json_object"},
        max_tokens=request.max_tokens,
        evidence_refs={
            "read_only": True,
            "target_type": request.target_type,
            "target_id": str(request.target_id),
            "source_refs": request.source_refs or {},
            "disallowed_tools": list(LLM_SUBAGENT_DISALLOWED_TOOLS),
            "config_source": "shared_chat_model_config",
        },
    )
    payload = _json_from_model_text(result.content)
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        summary = "LLM 子 Agent 已返回建议，但未提供摘要。"
    return ReadonlyLLMSubagentResult(
        mode=request.mode,
        target_type=request.target_type,
        target_id=request.target_id,
        summary=summary,
        recommendations=_list_of_strings(payload.get("recommendations")),
        risk_flags=_list_of_strings(payload.get("risk_flags")),
        raw_payload=payload,
        model_invocation_log_id=result.log_id,
    )


def _short_text(text: str | None, limit: int = 90) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def build_llm_advice_review_item(
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    run_key: str,
    async_task_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    result: ReadonlyLLMSubagentResult,
    title: str,
    detail: str | None = None,
    source_ref_json: dict[str, Any] | None = None,
    compliance_item_id: uuid.UUID | None = None,
    draft_block_id: uuid.UUID | None = None,
) -> AgentReviewItem:
    if result.target_type == "compliance_item":
        action = LLM_TECHNICAL_ADVICE_ACTION
        step = "qualification_technical"
        object_type = "compliance_item"
        compliance_item_id = compliance_item_id or result.target_id
        object_id = compliance_item_id
    elif result.target_type == "draft_block":
        action = LLM_DRAFT_ADVICE_ACTION
        step = "qualification_technical"
        object_type = "draft_block"
        draft_block_id = draft_block_id or result.target_id
        object_id = draft_block_id
    else:
        raise ValueError(f"不支持的 LLM 子 Agent 目标类型：{result.target_type}")

    recommendation_json = budget_display_payload(
        {
            "generated_by": "readonly_llm_subagent",
            "mode": result.mode,
            "summary": result.summary,
            "recommendations": result.recommendations,
            "risk_flags": result.risk_flags,
            "raw_payload": result.raw_payload,
            "model_invocation_log_id": str(result.model_invocation_log_id)
            if result.model_invocation_log_id
            else None,
            "read_only": True,
            "disallowed_tools": list(LLM_SUBAGENT_DISALLOWED_TOOLS),
            "business_effect": "只读建议；用户采纳仅关闭建议，不确认条款、不绑定证据、不批准草稿。",
        }
    )
    return AgentReviewItem(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        async_task_id=async_task_id,
        run_key=run_key,
        step=step,
        action=action,
        status="open",
        severity=result.severity,
        title=f"LLM 建议：{_short_text(title)}",
        detail=detail or result.summary,
        object_type=object_type,
        object_id=object_id,
        compliance_item_id=compliance_item_id,
        draft_block_id=draft_block_id,
        confidence_score=None,
        requires_human=True,
        escalation_reasons=["LLM 子 Agent 只产建议，必须人工拍板"],
        recommendation_json=recommendation_json,
        source_ref_json=source_ref_json,
        triggered_by=actor_user_id,
    )
