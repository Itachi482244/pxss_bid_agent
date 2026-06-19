from __future__ import annotations

from typing import Any

from app.services.agent.tools.base import PermissionResult, ToolResult, ToolUseContext
from app.services.material_retrieval import search_material_hits


ALLOWED_VERIFICATION_STATUSES = {"confirmed"}
ALLOWED_DATA_LEVELS = {"public", "internal"}
DEFAULT_EVIDENCE_SEARCH_LIMIT = 5
MAX_EVIDENCE_SEARCH_LIMIT = 5


def _string_set(value: Any, default: set[str]) -> set[str]:
    if value is None:
        return set(default)
    if isinstance(value, str):
        return {value}
    try:
        return {str(item) for item in value}
    except TypeError:
        return {str(value)}


def _limit(value: Any) -> int:
    try:
        parsed = int(value or DEFAULT_EVIDENCE_SEARCH_LIMIT)
    except (TypeError, ValueError):
        return DEFAULT_EVIDENCE_SEARCH_LIMIT
    return max(1, min(MAX_EVIDENCE_SEARCH_LIMIT, parsed))


class EvidenceSearchTool:
    name = "EvidenceSearchTool"
    description = "在已确认企业资料中检索候选响应证据。"
    side_effect_level = "read"
    writes_db = False
    requires_user_confirmation = False

    def is_read_only(self) -> bool:
        return True

    def is_destructive(self) -> bool:
        return False

    def check_permission(self, input: dict[str, Any], ctx: ToolUseContext) -> PermissionResult:
        query = str(input.get("query") or "").strip()
        if not query:
            return PermissionResult.deny("证据检索需要 query。")
        if ctx.project_id is None or ctx.section_id is None:
            return PermissionResult.deny("证据检索需要项目和标段上下文。")
        requested_statuses = _string_set(
            input.get("verification_statuses"),
            ALLOWED_VERIFICATION_STATUSES,
        )
        if not requested_statuses.issubset(ALLOWED_VERIFICATION_STATUSES):
            return PermissionResult.deny("Agent 证据检索只能读取已确认企业资料。")
        requested_levels = _string_set(input.get("allowed_data_levels"), ALLOWED_DATA_LEVELS)
        if not requested_levels.issubset(ALLOWED_DATA_LEVELS):
            return PermissionResult.deny("Agent 证据检索不能读取受限或机密资料。")
        return PermissionResult.allow("只读检索，仅限已确认且 public/internal 的企业资料。")

    def run(self, input: dict[str, Any], ctx: ToolUseContext) -> ToolResult:
        permission = self.check_permission(input, ctx)
        if permission.decision != "allow":
            return ToolResult(
                ok=False,
                error_code=f"PERMISSION_{permission.decision.upper()}",
                error_message=permission.reason,
            )
        hits = search_material_hits(
            ctx.db,
            tenant_id=ctx.tenant_id,
            query=str(input["query"]).strip(),
            verification_statuses=_string_set(
                input.get("verification_statuses"),
                ALLOWED_VERIFICATION_STATUSES,
            ),
            allowed_data_levels=_string_set(input.get("allowed_data_levels"), ALLOWED_DATA_LEVELS),
            limit=_limit(input.get("limit")),
        )
        data_hits: list[dict[str, Any]] = []
        for hit in hits:
            chunk = hit.chunk
            data_hits.append(
                {
                    "enterprise_material_id": str(hit.material.id),
                    "material_name": hit.material.name,
                    "material_type": hit.material.material_type,
                    "verification_status": hit.material.verification_status,
                    "data_level": hit.material.data_level,
                    "enterprise_material_chunk_id": str(chunk.id) if chunk is not None else None,
                    "chunk_index": chunk.chunk_index if chunk is not None else None,
                    "snippet": hit.snippet,
                    "confidence_score": round(float(hit.confidence_score), 4),
                    "base_score": round(float(hit.base_score), 4) if hit.base_score is not None else None,
                    "rerank_score": round(float(hit.rerank_score), 4) if hit.rerank_score is not None else None,
                    "recommend_reason": hit.recommend_reason,
                    "matched_terms": hit.matched_terms or [],
                }
            )
        return ToolResult(
            ok=True,
            data={
                "hits": data_hits,
                "hit_count": len(data_hits),
                "policy": {
                    "verification_statuses": sorted(ALLOWED_VERIFICATION_STATUSES),
                    "allowed_data_levels": sorted(ALLOWED_DATA_LEVELS),
                    "max_limit": MAX_EVIDENCE_SEARCH_LIMIT,
                },
            },
            preview=f"找到 {len(data_hits)} 条候选企业资料证据。",
        )
