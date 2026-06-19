from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.agent.llm_subagent import (
    LLM_DRAFT_ADVICE_ACTION,
    LLM_SUBAGENT_DISALLOWED_TOOLS,
    LLM_TECHNICAL_ADVICE_ACTION,
    ReadonlyLLMSubagentRequest,
    ReadonlyLLMSubagentResult,
    build_llm_advice_review_item,
    run_readonly_llm_subagent,
)
from app.services.agent.tools import (
    ComplianceConfirmTool,
    EvidenceSearchTool,
    QualificationEvaluateTool,
    ToolSpec,
    ToolUseContext,
)
from app.services.llm_gateway import LLMResult


def _tool_ctx(*, allow_user_confirmation_actions: bool = False) -> ToolUseContext:
    return ToolUseContext(
        db=SimpleNamespace(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        section_id=uuid4(),
        actor_user_id=uuid4(),
        run_key=f"tool-test:{uuid4().hex[:8]}",
        allow_user_confirmation_actions=allow_user_confirmation_actions,
    )


def test_agent_tool_specs_declare_permissions_and_side_effects() -> None:
    evidence_tool = EvidenceSearchTool()
    qualification_tool = QualificationEvaluateTool()
    confirm_tool = ComplianceConfirmTool()

    assert isinstance(evidence_tool, ToolSpec)
    assert evidence_tool.is_read_only()
    assert evidence_tool.writes_db is False
    assert evidence_tool.side_effect_level == "read"

    assert isinstance(qualification_tool, ToolSpec)
    assert not qualification_tool.is_read_only()
    assert qualification_tool.writes_db is True
    assert qualification_tool.side_effect_level == "write_suggestion_state"
    assert not qualification_tool.is_destructive()

    assert isinstance(confirm_tool, ToolSpec)
    assert confirm_tool.writes_db is True
    assert confirm_tool.requires_user_confirmation is True
    assert confirm_tool.side_effect_level == "user_confirmed_write"
    assert confirm_tool.is_destructive()


def test_evidence_search_tool_wraps_material_search(monkeypatch: pytest.MonkeyPatch) -> None:
    material = SimpleNamespace(
        id=uuid4(),
        name="测试营业执照",
        material_type="license",
        verification_status="confirmed",
        data_level="internal",
    )
    chunk = SimpleNamespace(id=uuid4(), chunk_index=2)
    hit = SimpleNamespace(
        material=material,
        chunk=chunk,
        snippet="营业执照摘要",
        confidence_score=Decimal("0.8700"),
        base_score=Decimal("0.8000"),
        rerank_score=None,
        recommend_reason="命中营业执照",
        matched_terms=["营业执照"],
    )
    calls: list[dict[str, object]] = []

    def fake_search_material_hits(db, **kwargs):  # noqa: ANN001
        calls.append(kwargs)
        return [hit]

    monkeypatch.setattr(
        "app.services.agent.tools.evidence_search.search_material_hits",
        fake_search_material_hits,
    )

    result = EvidenceSearchTool().run({"query": "营业执照", "limit": 99}, _tool_ctx())

    assert result.ok is True
    assert result.data["hit_count"] == 1
    assert result.data["hits"][0]["material_name"] == "测试营业执照"
    assert calls[0]["verification_statuses"] == {"confirmed"}
    assert calls[0]["allowed_data_levels"] == {"public", "internal"}
    assert calls[0]["limit"] == 5


def test_evidence_search_tool_rejects_privileged_filters() -> None:
    result = EvidenceSearchTool().run(
        {
            "query": "营业执照",
            "verification_statuses": ["confirmed", "expired"],
            "allowed_data_levels": ["public", "confidential"],
        },
        _tool_ctx(),
    )

    assert result.ok is False
    assert result.error_code == "PERMISSION_DENY"
    assert "已确认企业资料" in (result.error_message or "")


def test_qualification_evaluate_tool_writes_suggestion_state(monkeypatch: pytest.MonkeyPatch) -> None:
    evaluation = SimpleNamespace(
        evaluation_status="not_satisfied",
        is_blocking=True,
    )

    def fake_run_qualification_evaluation(db, **kwargs):  # noqa: ANN001
        return [evaluation]

    def fake_evaluation_snapshot(item):  # noqa: ANN001
        return {"evaluation_status": item.evaluation_status, "is_blocking": item.is_blocking}

    monkeypatch.setattr(
        "app.services.agent.tools.qualification_evaluate.run_qualification_evaluation",
        fake_run_qualification_evaluation,
    )
    monkeypatch.setattr(
        "app.services.agent.tools.qualification_evaluate.evaluation_snapshot",
        fake_evaluation_snapshot,
    )

    result = QualificationEvaluateTool().run({}, _tool_ctx())

    assert result.ok is True
    assert result.data["evaluation_count"] == 1
    assert result.data["blocking_count"] == 1
    assert "资格预评估" in result.preview


def test_compliance_confirm_tool_requires_user_confirmation_context() -> None:
    tool = ComplianceConfirmTool()

    blocked = tool.run({"review_item_id": str(uuid4()), "reason": "测试确认"}, _tool_ctx())
    allowed_permission = tool.check_permission(
        {"review_item_id": str(uuid4()), "reason": "测试确认"},
        _tool_ctx(allow_user_confirmation_actions=True),
    )

    assert blocked.ok is False
    assert blocked.error_code == "PERMISSION_ASK"
    assert "用户采纳" in (blocked.error_message or "")
    assert allowed_permission.decision == "allow"


def test_compliance_confirm_tool_rejects_invalid_review_item_id() -> None:
    result = ComplianceConfirmTool().run(
        {"review_item_id": "not-a-uuid", "reason": "测试确认"},
        _tool_ctx(allow_user_confirmation_actions=True),
    )

    assert result.ok is False
    assert result.error_code == "REVIEW_ITEM_ID_INVALID"


def test_compliance_confirm_tool_routes_through_agent_accept(monkeypatch: pytest.MonkeyPatch) -> None:
    review_item_id = uuid4()
    compliance_item_id = uuid4()
    review_item = SimpleNamespace(
        id=review_item_id,
        action="confirm_matrix_item",
        compliance_item_id=compliance_item_id,
    )

    class FakeDb:
        def scalar(self, _stmt):  # noqa: ANN001
            return review_item

    ctx = ToolUseContext(
        db=FakeDb(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        section_id=uuid4(),
        actor_user_id=uuid4(),
        allow_user_confirmation_actions=True,
    )
    calls: list[dict[str, object]] = []

    def fake_accept_agent_review_item(_db, **kwargs):  # noqa: ANN001, ANN003
        calls.append(kwargs)
        return SimpleNamespace(id=review_item_id, status="accepted", compliance_item_id=compliance_item_id)

    monkeypatch.setattr(
        "app.services.agent_assist.accept_agent_review_item",
        fake_accept_agent_review_item,
    )

    result = ComplianceConfirmTool().run(
        {"review_item_id": str(review_item_id), "reason": "测试确认", "source_verified": True},
        ctx,
    )

    assert result.ok is True
    assert result.data["status"] == "accepted"
    assert calls
    assert calls[0]["project_id"] == ctx.project_id
    assert calls[0]["section_id"] == ctx.section_id
    assert calls[0]["source_verified"] is True


def test_readonly_llm_subagent_uses_shared_chat_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    log_id = uuid4()

    def fake_chat_completion(db, **kwargs):  # noqa: ANN001
        calls.append(kwargs)
        return LLMResult(
            content=json.dumps(
                {
                    "summary": "技术响应需要人工复核偏离表。",
                    "recommendations": ["核对设备参数", "补充检测报告引用"],
                    "risk_flags": ["high"],
                },
                ensure_ascii=False,
            ),
            provider="openai_compatible",
            model_name="shared-main-agent-model",
            complexity="simple",
            prompt_version=str(kwargs["prompt_version"]),
            log_id=log_id,
            usage={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
        )

    monkeypatch.setattr("app.services.agent.llm_subagent.chat_completion", fake_chat_completion)

    request = ReadonlyLLMSubagentRequest(
        tenant_id=uuid4(),
        project_id=uuid4(),
        section_id=uuid4(),
        actor_user_id=uuid4(),
        mode="technical_response_advice",
        target_type="compliance_item",
        target_id=uuid4(),
        title="净化设备技术参数响应",
        context={"requirement_text": "须响应净化设备参数。"},
        source_refs={"source_page_no": 3},
    )
    result = run_readonly_llm_subagent(SimpleNamespace(), request)

    assert result.summary == "技术响应需要人工复核偏离表。"
    assert result.model_invocation_log_id == log_id
    assert calls
    call = calls[0]
    assert call["task_type"] == "agent_readonly_subagent"
    assert call["actor_type"] == "worker"
    assert call["response_format"] == {"type": "json_object"}
    assert "base_url" not in call
    assert "api_key" not in call
    assert call["evidence_refs"]["config_source"] == "shared_chat_model_config"  # type: ignore[index]
    assert set(LLM_SUBAGENT_DISALLOWED_TOOLS) <= set(call["evidence_refs"]["disallowed_tools"])  # type: ignore[index]
    assert "禁止写正式稿" in call["messages"][0]["content"]  # type: ignore[index]


def test_llm_subagent_review_item_is_human_gated_without_business_side_effect_action() -> None:
    result = ReadonlyLLMSubagentResult(
        mode="technical_response_advice",
        target_type="compliance_item",
        target_id=uuid4(),
        summary="建议人工核对技术偏离。",
        recommendations=["确认是否允许正偏离"],
        risk_flags=["high"],
        raw_payload={"summary": "建议人工核对技术偏离。"},
        model_invocation_log_id=uuid4(),
    )

    item = build_llm_advice_review_item(
        tenant_id=uuid4(),
        project_id=uuid4(),
        section_id=uuid4(),
        run_key=f"llm-subagent:{uuid4().hex[:8]}",
        async_task_id=None,
        actor_user_id=uuid4(),
        result=result,
        title="技术条款",
        source_ref_json={"source_page_no": 5},
    )

    assert item.step == "qualification_technical"
    assert item.action == LLM_TECHNICAL_ADVICE_ACTION
    assert item.status == "open"
    assert item.requires_human is True
    assert item.severity == "high"
    assert item.recommendation_json["read_only"] is True
    assert "ComplianceConfirmTool" in item.recommendation_json["disallowed_tools"]
    assert "不确认条款" in item.recommendation_json["business_effect"]

    draft_result = ReadonlyLLMSubagentResult(
        mode="l4_style_advice",
        target_type="draft_block",
        target_id=uuid4(),
        summary="建议润色表达。",
    )
    draft_item = build_llm_advice_review_item(
        tenant_id=uuid4(),
        project_id=uuid4(),
        section_id=uuid4(),
        run_key=f"llm-subagent:{uuid4().hex[:8]}",
        async_task_id=None,
        actor_user_id=uuid4(),
        result=draft_result,
        title="草稿 block",
    )
    assert draft_item.action == LLM_DRAFT_ADVICE_ACTION
