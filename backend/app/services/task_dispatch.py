"""Unified async task dispatch helpers.

All API routes that enqueue an :class:`AsyncTask` to Celery should go through
:func:`enqueue_celery_task` instead of calling ``.delay()`` directly with a
silent ``except Exception: pass``. When the broker is unreachable or dispatch
otherwise fails, the task is marked ``failed`` with an audit trail and a
:class:`TaskDispatchError` is raised so the route can surface a clear error to
the caller, rather than leaving the task stuck in ``pending`` forever.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import AsyncTask, AuditLog

TASK_DISPATCH_FAILED_CODE = "TASK_DISPATCH_FAILED"


class TaskDispatchError(Exception):
    """Raised when an async task cannot be handed off to the Celery broker."""

    def __init__(self, message: str, *, code: str = TASK_DISPATCH_FAILED_CODE) -> None:
        super().__init__(message)
        self.code = code


def mark_task_dispatch_failed(db: Session, task: AsyncTask, exc: Exception) -> None:
    """Mark a task as failed because it could not be dispatched, and audit it."""
    task.status = "failed"
    task.error_code = TASK_DISPATCH_FAILED_CODE
    task.error_message = f"任务派发到异步队列失败：{exc}"[:1000]
    task.finished_at = datetime.now(UTC)
    db.add(
        AuditLog(
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            actor_user_id=task.created_by,
            actor_type="system",
            action="task.dispatch_failed",
            object_type="async_task",
            object_id=task.id,
            after_json={
                "task_type": task.task_type,
                "error_code": TASK_DISPATCH_FAILED_CODE,
                "error_message": str(exc)[:1000],
            },
            reason="任务无法派发到异步队列，broker 不可用或配置异常",
            severity="critical",
        )
    )
    db.commit()


def enqueue_celery_task(db: Session, task: AsyncTask, invoker: Callable[[], object]) -> None:
    """Enqueue a task via ``invoker`` (which performs the ``.delay(...)`` call).

    On any failure the task is marked failed, audited, and ``TaskDispatchError``
    is raised so the caller can translate it into a user-facing error.
    """
    try:
        invoker()
    except Exception as exc:  # broker/connection/serialization errors
        mark_task_dispatch_failed(db, task, exc)
        raise TaskDispatchError(str(exc)) from exc
