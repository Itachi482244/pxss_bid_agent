from __future__ import annotations

from typing import Any

from app.services.agent.tools.base import PermissionResult, ToolResult, ToolUseContext
from app.services.qualification_evaluation import evaluation_snapshot, run_qualification_evaluation


class QualificationEvaluateTool:
    name = "QualificationEvaluateTool"
    description = "运行资格条款预评估，产出或更新 QualificationEvaluation 建议状态。"
    side_effect_level = "write_suggestion_state"
    writes_db = True
    requires_user_confirmation = False

    def is_read_only(self) -> bool:
        return False

    def is_destructive(self) -> bool:
        return False

    def check_permission(self, input: dict[str, Any], ctx: ToolUseContext) -> PermissionResult:
        if ctx.project_id is None or ctx.section_id is None:
            return PermissionResult.deny("资格评估需要项目和标段上下文。")
        return PermissionResult.allow("仅写入资格预评估建议状态。")

    def run(self, input: dict[str, Any], ctx: ToolUseContext) -> ToolResult:
        permission = self.check_permission(input, ctx)
        if permission.decision != "allow":
            return ToolResult(
                ok=False,
                error_code=f"PERMISSION_{permission.decision.upper()}",
                error_message=permission.reason,
            )
        evaluations = run_qualification_evaluation(
            ctx.db,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            section_id=ctx.section_id,
            actor_user_id=ctx.actor_user_id,
        )
        snapshots = [evaluation_snapshot(item) for item in evaluations]
        blocking_count = sum(
            1
            for item in evaluations
            if item.is_blocking or item.evaluation_status == "not_satisfied"
        )
        return ToolResult(
            ok=True,
            data={"evaluations": snapshots, "evaluation_count": len(snapshots), "blocking_count": blocking_count},
            preview=f"完成 {len(snapshots)} 条资格预评估，阻断项 {blocking_count} 条。",
        )

