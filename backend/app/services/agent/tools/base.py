from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from sqlalchemy.orm import Session


PermissionDecision = Literal["allow", "deny", "ask"]
SideEffectLevel = Literal["read", "write_suggestion_state", "user_confirmed_write", "destructive"]


@dataclass(frozen=True)
class PermissionResult:
    decision: PermissionDecision
    reason: str = ""

    @classmethod
    def allow(cls, reason: str = "") -> "PermissionResult":
        return cls("allow", reason)

    @classmethod
    def deny(cls, reason: str) -> "PermissionResult":
        return cls("deny", reason)

    @classmethod
    def ask(cls, reason: str) -> "PermissionResult":
        return cls("ask", reason)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    preview: str = ""
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ToolUseContext:
    db: Session
    tenant_id: uuid.UUID
    project_id: uuid.UUID | None
    section_id: uuid.UUID | None
    actor_user_id: uuid.UUID
    run_key: str | None = None
    allow_user_confirmation_actions: bool = False


@runtime_checkable
class ToolSpec(Protocol):
    name: str
    description: str
    side_effect_level: SideEffectLevel
    writes_db: bool
    requires_user_confirmation: bool

    def is_read_only(self) -> bool: ...

    def is_destructive(self) -> bool: ...

    def check_permission(self, input: dict[str, Any], ctx: ToolUseContext) -> PermissionResult: ...

    def run(self, input: dict[str, Any], ctx: ToolUseContext) -> ToolResult: ...

