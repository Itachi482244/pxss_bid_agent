from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models import AgentReviewItem
from app.services.agent.tools.base import PermissionResult, ToolResult, ToolUseContext


class ComplianceConfirmTool:
    name = "ComplianceConfirmTool"
    description = "用户采纳后确认合规条款；普通 Agent runner 不得自动调用。"
    side_effect_level = "user_confirmed_write"
    writes_db = True
    requires_user_confirmation = True

    def is_read_only(self) -> bool:
        return False

    def is_destructive(self) -> bool:
        return True

    def check_permission(self, input: dict[str, Any], ctx: ToolUseContext) -> PermissionResult:
        if not ctx.allow_user_confirmation_actions:
            return PermissionResult.ask("确认合规条款必须来自用户采纳/确认路径。")
        if ctx.project_id is None or ctx.section_id is None:
            return PermissionResult.deny("确认合规条款需要项目和标段上下文。")
        if not input.get("review_item_id"):
            return PermissionResult.deny("确认合规条款需要 review_item_id。")
        if not str(input.get("reason") or "").strip():
            return PermissionResult.deny("确认合规条款需要 reason。")
        return PermissionResult.allow("用户确认上下文允许执行。")

    def run(self, input: dict[str, Any], ctx: ToolUseContext) -> ToolResult:
        permission = self.check_permission(input, ctx)
        if permission.decision != "allow":
            return ToolResult(
                ok=False,
                error_code=f"PERMISSION_{permission.decision.upper()}",
                error_message=permission.reason,
            )

        try:
            review_item_id = uuid.UUID(str(input["review_item_id"]))
        except ValueError:
            return ToolResult(
                ok=False,
                error_code="REVIEW_ITEM_ID_INVALID",
                error_message="review_item_id 不是合法 UUID。",
            )
        review_item = ctx.db.scalar(
            select(AgentReviewItem).where(
                AgentReviewItem.tenant_id == ctx.tenant_id,
                AgentReviewItem.project_id == ctx.project_id,
                AgentReviewItem.section_id == ctx.section_id,
                AgentReviewItem.id == review_item_id,
                AgentReviewItem.status == "open",
            )
        )
        if review_item is None:
            return ToolResult(
                ok=False,
                error_code="REVIEW_ITEM_NOT_FOUND",
                error_message="待确认条款对应的 Agent 待办不存在或已处理。",
            )
        if review_item.action not in {"confirm_matrix_item", "review_technical_response"}:
            return ToolResult(
                ok=False,
                error_code="REVIEW_ITEM_ACTION_UNSUPPORTED",
                error_message="该 Agent 待办不是合规条款确认动作。",
            )

        from app.services.agent_assist import AgentAssistError, accept_agent_review_item

        try:
            accepted = accept_agent_review_item(
                ctx.db,
                tenant_id=ctx.tenant_id,
                project_id=ctx.project_id,
                section_id=ctx.section_id,
                review_item_id=review_item.id,
                actor_user_id=ctx.actor_user_id,
                reason=str(input["reason"]).strip(),
                source_verified=bool(input.get("source_verified")),
            )
        except AgentAssistError as exc:
            return ToolResult(
                ok=False,
                error_code=exc.code,
                error_message=str(exc),
            )
        return ToolResult(
            ok=True,
            data={
                "review_item_id": str(accepted.id),
                "status": accepted.status,
                "compliance_item_id": str(accepted.compliance_item_id)
                if accepted.compliance_item_id
                else None,
            },
            preview="用户确认上下文已完成合规条款确认。",
        )
