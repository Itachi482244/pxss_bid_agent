from __future__ import annotations

import uuid
from collections import Counter

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentReviewItem, BidSection, Project, QualificationDecision
from app.schemas.project import AgentReviewItemRead, FinalReviewZoneRead, SectionFinalReviewRead
from app.services.agent.readiness import compute_section_readiness


def _fallback_tier(item: AgentReviewItem) -> str:
    if item.tier:
        return item.tier
    if item.status == "auto_passed" or not item.requires_human:
        return "silent"
    return "blocking"


def _effective_scope_key(item: AgentReviewItem) -> tuple[str, ...]:
    if item.compliance_item_id:
        return ("compliance_item", item.step, str(item.compliance_item_id))
    if item.qualification_evaluation_id:
        return ("qualification_evaluation", item.step, str(item.qualification_evaluation_id))
    if item.qualification_decision_id:
        return ("qualification_decision", item.step, str(item.qualification_decision_id))
    if item.draft_block_id:
        return ("draft_block", item.step, str(item.draft_block_id))
    if item.object_id:
        return ("object", item.step, item.object_type, str(item.object_id))
    return ("review_item", item.step, str(item.id))


def _created_desc_value(value: datetime | None) -> float:
    if value is None:
        return 0
    return -value.timestamp()


def _zone(
    *,
    tier: str,
    title: str,
    description: str,
    items: list[AgentReviewItem],
    items_limit: int = 500,
) -> FinalReviewZoneRead:
    counts = Counter(item.status for item in items)
    return FinalReviewZoneRead(
        tier=tier,
        title=title,
        description=description,
        total_count=len(items),
        open_count=counts["open"],
        accepted_count=counts["accepted"],
        dismissed_count=counts["dismissed"],
        auto_passed_count=counts["auto_passed"],
        items=[AgentReviewItemRead.model_validate(item) for item in items[:items_limit]],
    )


def effective_review_items(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    include_decided: bool = True,
    limit: int | None = 500,
) -> list[AgentReviewItem]:
    latest_items = list(
        db.scalars(
            select(AgentReviewItem)
            .where(
                AgentReviewItem.tenant_id == tenant_id,
                AgentReviewItem.project_id == project_id,
                AgentReviewItem.section_id == section_id,
                AgentReviewItem.status != "superseded",
            )
            .order_by(AgentReviewItem.step.asc(), AgentReviewItem.created_at.desc())
        ).all()
    )
    superseded_decision_ids = set(
        db.scalars(
            select(QualificationDecision.id).where(
                QualificationDecision.tenant_id == tenant_id,
                QualificationDecision.project_id == project_id,
                QualificationDecision.section_id == section_id,
                QualificationDecision.status == "superseded",
            )
        ).all()
    )
    if superseded_decision_ids:
        latest_items = [
            item
            for item in latest_items
            if item.qualification_decision_id not in superseded_decision_ids
        ]
    latest_run_by_scope: dict[tuple[str, ...], str] = {}
    for item in latest_items:
        latest_run_by_scope.setdefault(_effective_scope_key(item), item.run_key)
    if not latest_run_by_scope:
        return []

    effective_items = [
        item
        for item in latest_items
        if latest_run_by_scope[_effective_scope_key(item)] == item.run_key
    ]
    if not include_decided:
        effective_items = [
            item for item in effective_items if item.status in {"open", "auto_passed"}
        ]
    tier_rank = {"blocking": 0, "pre_accepted": 1, "silent": 2}
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    effective_items.sort(
        key=lambda item: (
            tier_rank.get(_fallback_tier(item), 3),
            severity_rank.get(item.severity, 4),
            _created_desc_value(item.created_at),
        )
    )
    if limit is None:
        return effective_items
    return effective_items[:limit]


latest_review_items = effective_review_items


def build_section_final_review(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    section: BidSection,
) -> SectionFinalReviewRead:
    readiness = compute_section_readiness(
        db,
        tenant_id=tenant_id,
        project=project,
        section=section,
    )
    items = effective_review_items(
        db,
        tenant_id=tenant_id,
        project_id=project.id,
        section_id=section.id,
        limit=None,
    )
    red_items = [item for item in items if _fallback_tier(item) == "blocking"]
    yellow_items = [item for item in items if _fallback_tier(item) == "pre_accepted"]
    white_items = [item for item in items if _fallback_tier(item) == "silent"]

    red = _zone(
        tier="blocking",
        title="红牌区",
        description="必须清零后才能确认锁定。",
        items=red_items,
    )
    yellow = _zone(
        tier="pre_accepted",
        title="预采纳区",
        description="默认随确认锁定生效，可展开撤销或单条处理。",
        items=yellow_items,
    )
    white = _zone(
        tier="silent",
        title="已自动完成",
        description="低风险自动核验和即时绑定，只读留痕。",
        items=white_items,
    )
    suggested_actions = [
        item.title for item in red_items if item.status == "open"
    ][:5] or readiness.preflight.suggested_actions
    return SectionFinalReviewRead(
        project_id=project.id,
        section_id=section.id,
        assist_stage=section.assist_stage,
        can_confirm=red.open_count == 0 and readiness.can_confirm,
        can_generate=readiness.can_generate,
        readiness=readiness.preflight,
        red=red,
        yellow=yellow,
        white=white,
        suggested_actions=suggested_actions,
    )
