from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_request_context
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models import AsyncTask, AuditLog, EnterpriseMaterial, EnterpriseMaterialChunk, EnterpriseProfile
from app.schemas.document import AsyncTaskRead
from app.schemas.enterprise import (
    EnterpriseMaterialHistoryExtractResult,
    EnterpriseMaterialIndexHealthRead,
    EnterpriseMaterialIndexRebuildResult,
    EnterpriseMaterialChunkRead,
    EnterpriseMaterialCreateRequest,
    EnterpriseMaterialRead,
    EnterpriseMaterialSearchResult,
    EnterpriseMaterialUpdateRequest,
    EnterpriseProfileRead,
    EnterpriseProfileUpsertRequest,
)
from app.services.document_utils import HISTORY_MATERIAL_FILE_MAX_BYTES, MAX_FILE_BYTES, readable_file_size, safe_filename
from app.services.history_material_extract import (
    HistoryMaterialExtractError,
    create_pending_materials_from_extraction,
    execute_history_material_extract_task,
    extract_history_material_drafts,
)
from app.services.material_identity import enterprise_material_identity_key
from app.services.material_retrieval import (
    get_material_index_health,
    rebuild_material_chunks,
    rebuild_tenant_material_index,
    search_material_hits,
)
from app.services.storage import put_object_bytes
from app.services.task_dispatch import TaskDispatchError, enqueue_celery_task

router = APIRouter()

MATERIAL_TYPES = {
    "license",
    "qualification",
    "personnel",
    "performance",
    "business_template",
    "commitment",
    "product_catalog",
    "test_report",
    "product_image",
    "technical_proposal",
    "other",
}
DATA_LEVELS = {"public", "internal", "restricted", "confidential"}
VERIFICATION_STATUSES = {
    "draft",
    "pending_confirm",
    "confirmed",
    "conflict",
    "expired",
    "missing_evidence",
}

def validate_material_values(
    *,
    material_type: str | None = None,
    data_level: str | None = None,
    verification_status: str | None = None,
) -> None:
    if material_type is not None and material_type not in MATERIAL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported material_type: {material_type}",
        )
    if data_level is not None and data_level not in DATA_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported data_level: {data_level}",
        )
    if verification_status is not None and verification_status not in VERIFICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported verification_status: {verification_status}",
        )


def add_enterprise_audit_log(
    db: Session,
    ctx: RequestContext,
    *,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    before_json: dict | None,
    after_json: dict | None,
    reason: str,
) -> None:
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
            severity="info",
        )
    )


def material_snapshot(material: EnterpriseMaterial) -> dict[str, object]:
    return {
        "id": str(material.id),
        "material_type": material.material_type,
        "name": material.name,
        "issuing_authority": material.issuing_authority,
        "certificate_no": material.certificate_no,
        "holder_name": material.holder_name,
        "project_name": material.project_name,
        "amount": material.amount,
        "valid_from": material.valid_from.isoformat() if material.valid_from else None,
        "valid_until": material.valid_until.isoformat() if material.valid_until else None,
        "data_level": material.data_level,
        "verification_status": material.verification_status,
        "structured_fields": material.structured_fields,
        "evidence_text": material.evidence_text,
        "file_name": material.file_name,
        "sha256": material.sha256,
    }


def get_material_or_404(
    db: Session,
    ctx: RequestContext,
    material_id: uuid.UUID,
) -> EnterpriseMaterial:
    material = db.scalar(
        select(EnterpriseMaterial).where(
            EnterpriseMaterial.tenant_id == ctx.tenant_id,
            EnterpriseMaterial.id == material_id,
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


@router.get("/profile", response_model=EnterpriseProfileRead | None)
def get_enterprise_profile(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.scalar(select(EnterpriseProfile).where(EnterpriseProfile.tenant_id == ctx.tenant_id))


@router.put("/profile", response_model=EnterpriseProfileRead)
def upsert_enterprise_profile(
    payload: EnterpriseProfileUpsertRequest,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
):
    profile = db.scalar(select(EnterpriseProfile).where(EnterpriseProfile.tenant_id == ctx.tenant_id))
    if profile is None:
        profile = EnterpriseProfile(
            tenant_id=ctx.tenant_id,
            created_by=ctx.user_id,
            updated_by=ctx.user_id,
            **payload.model_dump(),
        )
        db.add(profile)
        action = "enterprise.profile_created"
        before = None
    else:
        before = {
            "company_name": profile.company_name,
            "unified_social_credit_code": profile.unified_social_credit_code,
            "legal_representative": profile.legal_representative,
            "registered_address": profile.registered_address,
            "business_scope": profile.business_scope,
            "region_preferences": profile.region_preferences,
            "industry_preferences": profile.industry_preferences,
            "forbidden_rules": profile.forbidden_rules,
        }
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        profile.updated_by = ctx.user_id
        action = "enterprise.profile_updated"

    db.flush()
    after = {
        "company_name": profile.company_name,
        "unified_social_credit_code": profile.unified_social_credit_code,
        "legal_representative": profile.legal_representative,
        "registered_address": profile.registered_address,
        "business_scope": profile.business_scope,
        "region_preferences": profile.region_preferences,
        "industry_preferences": profile.industry_preferences,
        "forbidden_rules": profile.forbidden_rules,
    }
    add_enterprise_audit_log(
        db,
        ctx,
        action=action,
        object_type="enterprise_profile",
        object_id=profile.id,
        before_json=before,
        after_json=after,
        reason="维护企业画像",
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/materials", response_model=list[EnterpriseMaterialRead])
def list_enterprise_materials(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    material_type: Annotated[str | None, Query()] = None,
    data_level: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    validate_material_values(
        material_type=material_type,
        data_level=data_level,
        verification_status=verification_status,
    )
    query = select(EnterpriseMaterial).where(EnterpriseMaterial.tenant_id == ctx.tenant_id)
    if material_type:
        query = query.where(EnterpriseMaterial.material_type == material_type)
    if data_level:
        query = query.where(EnterpriseMaterial.data_level == data_level)
    if verification_status:
        query = query.where(EnterpriseMaterial.verification_status == verification_status)
    query = query.order_by(EnterpriseMaterial.updated_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query).all())


@router.get("/materials/index-health", response_model=EnterpriseMaterialIndexHealthRead)
def get_enterprise_material_index_health(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
) -> EnterpriseMaterialIndexHealthRead:
    return EnterpriseMaterialIndexHealthRead.model_validate(
        get_material_index_health(db, tenant_id=ctx.tenant_id).__dict__
    )


@router.post("/materials/index/rebuild", response_model=EnterpriseMaterialIndexRebuildResult)
def rebuild_enterprise_material_index(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
) -> EnterpriseMaterialIndexRebuildResult:
    before = get_material_index_health(db, tenant_id=ctx.tenant_id)
    result = rebuild_tenant_material_index(db, tenant_id=ctx.tenant_id)
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.material_index_rebuilt",
        object_type="enterprise_material_index",
        object_id=None,
        before_json=jsonable_encoder(before.__dict__),
        after_json={
            "rebuilt_material_count": result.rebuilt_material_count,
            "rebuilt_chunk_count": result.rebuilt_chunk_count,
            "removed_chunk_count": result.removed_chunk_count,
            "health": jsonable_encoder(result.health.__dict__),
        },
        reason="重建企业资料检索索引",
    )
    db.commit()
    return EnterpriseMaterialIndexRebuildResult.model_validate(
        {
            **result.__dict__,
            "health": result.health.__dict__,
        }
    )


@router.get("/materials/search", response_model=list[EnterpriseMaterialSearchResult])
def search_enterprise_materials(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    query: Annotated[str, Query(max_length=1000)] = "",
    material_type: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    data_level: Annotated[str | None, Query()] = None,
    include_restricted: bool = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    validate_material_values(
        material_type=material_type,
        data_level=data_level,
        verification_status=verification_status,
    )
    allowed_data_levels = {"public", "internal"}
    if include_restricted:
        allowed_data_levels.update({"restricted", "confidential"})
    if data_level:
        allowed_data_levels = {data_level} if data_level in allowed_data_levels else set()
    hits = search_material_hits(
        db,
        tenant_id=ctx.tenant_id,
        query=query,
        material_type=material_type,
        verification_status=verification_status,
        allowed_data_levels=allowed_data_levels,
        limit=min(200, max(limit, limit * 4)),
    )
    deduped_hits = []
    seen_material_keys: set[str] = set()
    for hit in hits:
        material_key = enterprise_material_identity_key(hit.material)
        if material_key in seen_material_keys:
            continue
        seen_material_keys.add(material_key)
        deduped_hits.append(hit)
        if len(deduped_hits) >= limit:
            break
    return [
        EnterpriseMaterialSearchResult(
            **EnterpriseMaterialRead.model_validate(hit.material).model_dump(),
            snippet=hit.snippet,
            confidence_score=hit.confidence_score,
            base_score=hit.base_score,
            rerank_score=hit.rerank_score,
            rerank_provider=hit.rerank_provider,
            rerank_model=hit.rerank_model,
            rerank_used=hit.rerank_used,
            rerank_fallback_used=hit.rerank_fallback_used,
            rerank_error=hit.rerank_error,
            chunk_id=hit.chunk.id if hit.chunk else None,
            data_level_allowed=hit.material.data_level in allowed_data_levels,
            recommend_reason=hit.recommend_reason,
            matched_terms=hit.matched_terms or [],
            material_status_hint=hit.material_status_hint,
        )
        for hit in deduped_hits
    ]


@router.get("/materials/{material_id}/chunks", response_model=list[EnterpriseMaterialChunkRead])
def list_enterprise_material_chunks(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[EnterpriseMaterialChunkRead]:
    material = get_material_or_404(db, ctx, material_id)
    chunks = db.scalars(
        select(EnterpriseMaterialChunk)
        .where(
            EnterpriseMaterialChunk.tenant_id == ctx.tenant_id,
            EnterpriseMaterialChunk.enterprise_material_id == material.id,
        )
        .order_by(EnterpriseMaterialChunk.chunk_index.asc())
    ).all()
    return [EnterpriseMaterialChunkRead.model_validate(chunk) for chunk in chunks]


@router.post("/materials/{material_id}/chunks/rebuild", response_model=list[EnterpriseMaterialChunkRead])
def rebuild_enterprise_material_chunks(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
) -> list[EnterpriseMaterialChunkRead]:
    material = get_material_or_404(db, ctx, material_id)
    chunks = rebuild_material_chunks(db, material)
    db.flush()
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.material_chunks_rebuilt",
        object_type="enterprise_material",
        object_id=material.id,
        before_json=None,
        after_json={"chunk_count": len(chunks)},
        reason="重建企业资料检索切片",
    )
    db.commit()
    return [EnterpriseMaterialChunkRead.model_validate(chunk) for chunk in chunks]


@router.post("/materials", response_model=EnterpriseMaterialRead, status_code=status.HTTP_201_CREATED)
def create_enterprise_material(
    payload: EnterpriseMaterialCreateRequest,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
):
    validate_material_values(
        material_type=payload.material_type,
        data_level=payload.data_level,
        verification_status=payload.verification_status,
    )
    material = EnterpriseMaterial(
        tenant_id=ctx.tenant_id,
        created_by=ctx.user_id,
        updated_by=ctx.user_id,
        **payload.model_dump(),
    )
    db.add(material)
    db.flush()
    if material.verification_status == "confirmed":
        rebuild_material_chunks(db, material)
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.material_created",
        object_type="enterprise_material",
        object_id=material.id,
        before_json=None,
        after_json=material_snapshot(material),
        reason="新增企业资料",
    )
    db.commit()
    db.refresh(material)
    return material


def _history_extract_object_key(ctx: RequestContext, filename: str, sha256: str) -> str:
    suffix = Path(filename).suffix.lower()
    return (
        f"tenants/{ctx.tenant_id}/enterprise-material-history/"
        f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{sha256[:12]}{suffix}"
    )


def _read_history_upload_file(file: UploadFile) -> bytes:
    data = file.file.read(HISTORY_MATERIAL_FILE_MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(data) > HISTORY_MATERIAL_FILE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large; max {readable_file_size(HISTORY_MATERIAL_FILE_MAX_BYTES)}",
        )
    return data


def _execute_history_extract_background(task_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        execute_history_material_extract_task(db, task_id)


@router.post(
    "/materials/history-extract-tasks",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_enterprise_materials_history_extract_task(
    background_tasks: BackgroundTasks,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    pdf_mode: str = Form("auto"),
    data_level: str = Form("internal"),
) -> AsyncTaskRead:
    validate_material_values(data_level=data_level)
    data = _read_history_upload_file(file)
    filename = safe_filename(file.filename)
    sha256 = hashlib.sha256(data).hexdigest()
    object_key = _history_extract_object_key(ctx, filename, sha256)
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=file.content_type,
    )
    idempotency_key = "history-material-extract:" + hashlib.sha256(
        f"{ctx.tenant_id}:{ctx.user_id}:{sha256}:{pdf_mode}:{data_level}:{uuid.uuid4().hex}".encode("utf-8")
    ).hexdigest()
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=None,
        section_id=None,
        task_type="history_material_extract",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "source_file_name": filename,
            "source_file_size": len(data),
            "source_sha256": sha256,
            "content_type": file.content_type,
            "bucket": settings.minio_bucket,
            "object_key": object_key,
            "pdf_mode": pdf_mode,
            "data_level": data_level,
        },
        retry_count=0,
        max_retries=1,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            project_id=None,
            section_id=None,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action="enterprise.materials_history_extract_requested",
            object_type="async_task",
            object_id=task.id,
            after_json=task.input_json,
            reason="用户上传历史投标文件并请求异步抽取企业资料",
            severity="info",
        )
    )
    db.commit()
    db.refresh(task)

    if settings.run_tasks_inline:
        background_tasks.add_task(_execute_history_extract_background, task.id)
    else:
        from app.worker import run_history_material_extract_task

        try:
            enqueue_celery_task(
                db,
                task,
                lambda: run_history_material_extract_task.delay(str(task.id)),
            )
        except TaskDispatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"历史资料抽取任务派发失败：{exc}",
            ) from exc
        db.refresh(task)
    return AsyncTaskRead.model_validate(task)


@router.post(
    "/materials/history-extract",
    response_model=EnterpriseMaterialHistoryExtractResult,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
def extract_enterprise_materials_from_history_file(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    pdf_mode: str = Form("auto"),
    data_level: str = Form("internal"),
):
    validate_material_values(data_level=data_level)
    data = _read_history_upload_file(file)

    filename = safe_filename(file.filename)
    sha256 = hashlib.sha256(data).hexdigest()
    object_key = _history_extract_object_key(ctx, filename, sha256)
    try:
        extraction = extract_history_material_drafts(
            db,
            tenant_id=ctx.tenant_id,
            actor_user_id=ctx.user_id,
            data=data,
            filename=filename,
            content_type=file.content_type,
            pdf_mode=pdf_mode,
        )
    except HistoryMaterialExtractError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=file.content_type,
    )
    materials = create_pending_materials_from_extraction(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user_id,
        extraction=extraction,
        bucket=settings.minio_bucket,
        object_key=object_key,
        source_data=data,
        data_level=data_level,
    )
    db.flush()
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.materials_extracted_from_history",
        object_type="enterprise_material_history_file",
        object_id=None,
        before_json=None,
        after_json={
            "source_file_name": extraction.source_file_name,
            "source_sha256": extraction.source_sha256,
            "parser_summary": extraction.parser_summary,
            "extraction_method": extraction.extraction_method,
            "draft_count": len(materials),
            "text_block_count": len(extraction.text_blocks),
            "warnings": extraction.warnings,
        },
        reason="上传历史投标文件并抽取企业资料草稿",
    )
    db.commit()
    for material in materials:
        db.refresh(material)
    return EnterpriseMaterialHistoryExtractResult(
        materials=[EnterpriseMaterialRead.model_validate(material) for material in materials],
        source_file_name=extraction.source_file_name,
        source_file_size=extraction.source_file_size,
        source_sha256=extraction.source_sha256,
        parser_summary=extraction.parser_summary,
        extraction_method=extraction.extraction_method,
        warning_messages=extraction.warnings,
        draft_count=len(materials),
        text_block_count=len(extraction.text_blocks),
    )


@router.patch("/materials/{material_id}", response_model=EnterpriseMaterialRead)
def update_enterprise_material(
    material_id: uuid.UUID,
    payload: EnterpriseMaterialUpdateRequest,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
):
    material = get_material_or_404(db, ctx, material_id)
    validate_material_values(
        material_type=payload.material_type,
        data_level=payload.data_level,
        verification_status=payload.verification_status,
    )
    before = material_snapshot(material)
    update_data = payload.model_dump(exclude_unset=True)
    reason = update_data.pop("reason")
    for field, value in update_data.items():
        setattr(material, field, value)
    material.updated_by = ctx.user_id
    db.flush()
    should_rebuild_chunks = (
        material.verification_status == "confirmed"
        and {"name", "structured_fields", "evidence_text", "data_level", "verification_status"} & set(update_data)
    )
    if should_rebuild_chunks:
        rebuild_material_chunks(db, material)
    elif "verification_status" in update_data and material.verification_status != "confirmed":
        db.execute(
            delete(EnterpriseMaterialChunk).where(
                EnterpriseMaterialChunk.tenant_id == ctx.tenant_id,
                EnterpriseMaterialChunk.enterprise_material_id == material.id,
            )
        )
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.material_updated",
        object_type="enterprise_material",
        object_id=material.id,
        before_json=before,
        after_json=material_snapshot(material),
        reason=reason,
    )
    db.commit()
    db.refresh(material)
    return material


@router.post("/materials/{material_id}/file", response_model=EnterpriseMaterialRead)
async def upload_enterprise_material_file(
    material_id: uuid.UUID,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    reason: str = Form("上传企业资料原始文件"),
):
    material = get_material_or_404(db, ctx, material_id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    before = material_snapshot(material)
    sha256 = hashlib.sha256(data).hexdigest()
    suffix = Path(file.filename or "material.bin").suffix.lower()
    object_key = (
        f"tenants/{ctx.tenant_id}/enterprise-materials/{material.id}/"
        f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{sha256[:12]}{suffix}"
    )
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=file.content_type,
    )
    material.file_name = file.filename or "material.bin"
    material.content_type = file.content_type
    material.file_size = len(data)
    material.sha256 = sha256
    material.bucket = settings.minio_bucket
    material.object_key = object_key
    material.updated_by = ctx.user_id
    if material.verification_status == "draft":
        material.verification_status = "pending_confirm"

    db.flush()
    add_enterprise_audit_log(
        db,
        ctx,
        action="enterprise.material_file_uploaded",
        object_type="enterprise_material",
        object_id=material.id,
        before_json=before,
        after_json=material_snapshot(material),
        reason=reason,
    )
    db.commit()
    db.refresh(material)
    return material
