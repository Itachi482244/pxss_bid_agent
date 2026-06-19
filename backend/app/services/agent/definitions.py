from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Callable, Sequence

from app.services.agent.policy import AgentActionPolicy, DEFAULT_ACTION_POLICY

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import AgentReviewItem, BidSection, ComplianceItem, Project
    from app.services.agent.progress import ProgressReporter


StepRunner = Callable[["StepContext"], list["AgentReviewItem"]]


@dataclass(frozen=True)
class AssistStepDefinition:
    step: str
    when_to_use: str
    runner: StepRunner
    progress_start: int
    progress_end: int
    auto_pass_confidence: Decimal = Decimal("0.8800")
    enabled: bool = True


@dataclass(frozen=True)
class AssistPlan:
    steps: tuple[AssistStepDefinition, ...]

    def enabled_steps(self, requested_steps: Sequence[str] | None = None) -> list[AssistStepDefinition]:
        requested = set(requested_steps or [])
        return [
            step
            for step in self.steps
            if step.enabled and (not requested or step.step in requested)
        ]


@dataclass(frozen=True)
class StepContext:
    db: "Session"
    project: "Project"
    section: "BidSection"
    items: list["ComplianceItem"]
    evidence_counts: dict[uuid.UUID, int]
    run_key: str
    async_task_id: uuid.UUID | None
    actor_user_id: uuid.UUID
    policy: AgentActionPolicy
    reporter: "ProgressReporter"
    step_definition: AssistStepDefinition | None = None

    def for_step(self, step_definition: AssistStepDefinition) -> "StepContext":
        return replace(self, step_definition=step_definition)

    @property
    def auto_pass_confidence(self) -> Decimal:
        if self.step_definition is None:
            return Decimal("0.8800")
        return self.step_definition.auto_pass_confidence


def base_step_context(
    *,
    db: "Session",
    project: "Project",
    section: "BidSection",
    items: list["ComplianceItem"],
    evidence_counts: dict[uuid.UUID, int],
    run_key: str,
    async_task_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    reporter: "ProgressReporter",
    policy: AgentActionPolicy = DEFAULT_ACTION_POLICY,
) -> StepContext:
    return StepContext(
        db=db,
        project=project,
        section=section,
        items=items,
        evidence_counts=evidence_counts,
        run_key=run_key,
        async_task_id=async_task_id,
        actor_user_id=actor_user_id,
        policy=policy,
        reporter=reporter,
    )

