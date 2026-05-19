from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Tenant, User


@dataclass(frozen=True)
class RequestContext:
    tenant_id: uuid.UUID
    tenant_code: str
    user_id: uuid.UUID
    user_external_id: str


def get_request_context(
    db: Annotated[Session, Depends(get_db)],
    x_tenant_code: Annotated[str | None, Header(alias="X-Tenant-Code")] = None,
    x_user_external_id: Annotated[str | None, Header(alias="X-User-External-Id")] = None,
) -> RequestContext:
    tenant_code = x_tenant_code or "demo"
    user_external_id = x_user_external_id or "demo-admin"

    tenant = db.scalar(
        select(Tenant).where(
            Tenant.code == tenant_code,
            Tenant.status == "active",
        )
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active tenant not found: {tenant_code}",
        )

    user = db.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.external_id == user_external_id,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active user not found in tenant {tenant_code}: {user_external_id}",
        )

    return RequestContext(
        tenant_id=tenant.id,
        tenant_code=tenant.code,
        user_id=user.id,
        user_external_id=user.external_id or user_external_id,
    )
