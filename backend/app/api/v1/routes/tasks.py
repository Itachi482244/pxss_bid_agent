from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_request_context
from app.db.session import get_db
from app.models import AsyncTask, ProjectMember
from app.schemas.document import AsyncTaskRead

router = APIRouter()


def _visible_project_ids(ctx: RequestContext):
    return select(ProjectMember.project_id).where(
        ProjectMember.tenant_id == ctx.tenant_id,
        ProjectMember.user_id == ctx.user_id,
        ProjectMember.status == "active",
    )


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
