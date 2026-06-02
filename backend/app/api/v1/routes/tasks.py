from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_request_context
from app.db.session import get_db
from app.models import AsyncTask, ProjectMember
from app.schemas.document import AsyncTaskRead

router = APIRouter()

ACTIVE_TASK_STATUSES = ("pending", "running", "retrying")


def _visible_project_ids(ctx: RequestContext):
    return select(ProjectMember.project_id).where(
        ProjectMember.tenant_id == ctx.tenant_id,
        ProjectMember.user_id == ctx.user_id,
        ProjectMember.status == "active",
    )


@router.get("", response_model=list[AsyncTaskRead])
def list_async_tasks(
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    project_id: uuid.UUID | None = Query(default=None),
    section_id: uuid.UUID | None = Query(default=None),
    task_type: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[AsyncTaskRead]:
    visible_project_ids = db.scalars(_visible_project_ids(ctx)).all()
    statement = select(AsyncTask).where(AsyncTask.tenant_id == ctx.tenant_id)
    if project_id is not None:
        if project_id not in visible_project_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        statement = statement.where(AsyncTask.project_id == project_id)
    else:
        statement = statement.where(
            (AsyncTask.project_id.in_(visible_project_ids)) | (AsyncTask.created_by == ctx.user_id)
        )
    if section_id is not None:
        statement = statement.where(AsyncTask.section_id == section_id)
    if task_type:
        statement = statement.where(AsyncTask.task_type == task_type)
    if active is True:
        statement = statement.where(AsyncTask.status.in_(ACTIVE_TASK_STATUSES))
    elif active is False:
        statement = statement.where(AsyncTask.status.not_in(ACTIVE_TASK_STATUSES))
    tasks = db.scalars(statement.order_by(AsyncTask.updated_at.desc()).limit(limit)).all()
    return [AsyncTaskRead.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=AsyncTaskRead)
def get_async_task(
    task_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AsyncTaskRead:
    task = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == ctx.tenant_id,
            AsyncTask.id == task_id,
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.project_id is None:
        if task.created_by != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    elif task.project_id not in db.scalars(_visible_project_ids(ctx)).all():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return AsyncTaskRead.model_validate(task)
