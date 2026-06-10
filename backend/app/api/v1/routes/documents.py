from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_request_context
from app.api.v1.routes.projects import get_section_or_404
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    AsyncTask,
    AuditLog,
    Document,
    DocumentChunk,
    DocumentExtractionQualityReport,
    DocumentSemanticSection,
    DocumentVersion,
    FileAcquisitionTask,
    ParseTask,
)
from app.schemas.document import (
    DocumentChunkRead,
    DocumentExtractionQualityReportRead,
    DocumentManualRevisionRequest,
    DocumentManualRevisionResult,
    DocumentSemanticSectionRead,
    AsyncTaskRead,
    DocumentRead,
    DocumentVersionRead,
    FileAcquisitionRequest,
    FileAcquisitionTaskRead,
    ParseTaskRead,
    ParseTaskRequest,
)
from app.services.document_utils import (
    TENDER_DOCUMENT_FILE_MAX_BYTES,
    file_extension,
    infer_parser_type,
    readable_file_size,
    safe_filename,
)
from app.services.storage import put_object_bytes
from app.services.task_dispatch import TaskDispatchError, enqueue_celery_task
from app.services.url_safety import validate_public_file_url
from app.services.document_parse import execute_document_parse_task
from app.services.file_acquisition import execute_file_acquisition_task
from app.services.compliance_generation import (
    ensure_document_section_plan,
    execute_section_compliance_extract_task,
    latest_extraction_quality_report,
)

router = APIRouter()


def async_task_read(task: AsyncTask) -> AsyncTaskRead:
    return AsyncTaskRead.model_validate(task)


def document_read(document: Document, version: DocumentVersion | None = None) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        project_id=document.project_id,
        section_id=document.section_id,
        doc_type=document.doc_type,
        title=document.title,
        source_type=document.source_type,
        source_site=document.source_site,
        source_url=document.source_url,
        original_filename=document.original_filename,
        content_type=document.content_type,
        file_ext=document.file_ext,
        file_size=document.file_size,
        sha256=document.sha256,
        status=document.status,
        current_version_id=document.current_version_id,
        acquired_at=document.acquired_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
        current_version=DocumentVersionRead.model_validate(version) if version else None,
    )


def acquisition_read(task: AsyncTask, acquisition: FileAcquisitionTask) -> FileAcquisitionTaskRead:
    return FileAcquisitionTaskRead(
        id=acquisition.id,
        task=async_task_read(task),
        project_id=acquisition.project_id,
        section_id=acquisition.section_id,
        source_url=acquisition.source_url,
        normalized_url=acquisition.normalized_url,
        source_site=acquisition.source_site,
        fetch_method=acquisition.fetch_method,
        validation_status=acquisition.validation_status,
        blocked_reason=acquisition.blocked_reason,
        http_status=acquisition.http_status,
        content_type=acquisition.content_type,
        content_length=acquisition.content_length,
        target_document_id=acquisition.target_document_id,
        created_at=acquisition.created_at,
        updated_at=acquisition.updated_at,
    )


def parse_task_read(task: AsyncTask, parse_task: ParseTask) -> ParseTaskRead:
    return ParseTaskRead(
        id=parse_task.id,
        task=async_task_read(task),
        document_id=parse_task.document_id,
        document_version_id=parse_task.document_version_id,
        parser_type=parse_task.parser_type,
        parser_name=parse_task.parser_name,
        parser_version=parse_task.parser_version,
        options_json=parse_task.options_json,
        result_summary_json=parse_task.result_summary_json,
        created_at=parse_task.created_at,
        updated_at=parse_task.updated_at,
    )


def add_audit_log(
    db: Session,
    ctx: RequestContext,
    *,
    project_id: uuid.UUID,
    section_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    after_json: dict | None = None,
    reason: str | None = None,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action=action,
            object_type=object_type,
            object_id=object_id,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def get_document_or_404(
    db: Session,
    ctx: RequestContext,
    *,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.tenant_id == ctx.tenant_id,
            Document.project_id == project_id,
            Document.section_id == section_id,
            Document.id == document_id,
            Document.status != "deleted",
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def get_document_version_or_404(
    db: Session,
    ctx: RequestContext,
    *,
    document: Document,
    version_id: uuid.UUID,
) -> DocumentVersion:
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.tenant_id == ctx.tenant_id,
            DocumentVersion.document_id == document.id,
            DocumentVersion.id == version_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document version not found")
    return version


@router.get(
    "/{project_id}/sections/{section_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[DocumentRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    rows = db.execute(
        select(Document, DocumentVersion)
        .outerjoin(DocumentVersion, DocumentVersion.id == Document.current_version_id)
        .where(
            Document.tenant_id == ctx.tenant_id,
            Document.project_id == project_id,
            Document.section_id == section_id,
            Document.status != "deleted",
        )
        .order_by(Document.created_at.desc())
    ).all()
    return [document_read(document, version) for document, version in rows]


@router.post(
    "/{project_id}/sections/{section_id}/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()] = "tender",
    title: Annotated[str | None, Form()] = None,
) -> DocumentRead:
    get_section_or_404(db, ctx, project_id, section_id)

    payload = await file.read(TENDER_DOCUMENT_FILE_MAX_BYTES + 1)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(payload) > TENDER_DOCUMENT_FILE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large; max {readable_file_size(TENDER_DOCUMENT_FILE_MAX_BYTES)}",
        )

    filename = safe_filename(file.filename)
    ext = file_extension(filename)
    content_hash = hashlib.sha256(payload).hexdigest()
    now = datetime.now(UTC)
    document_id = uuid.uuid4()
    object_key = (
        f"tenant/{ctx.tenant_id}/project/{project_id}/section/{section_id}/"
        f"documents/{document_id}/v1/{filename}"
    )

    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=payload,
        content_type=file.content_type,
    )

    document = Document(
        id=document_id,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        doc_type=doc_type,
        title=title or Path(filename).stem or filename,
        source_type="upload",
        original_filename=filename,
        content_type=file.content_type,
        file_ext=ext,
        file_size=len(payload),
        sha256=content_hash,
        bucket=settings.minio_bucket,
        object_key=object_key,
        status="available",
        created_by=ctx.user_id,
        acquired_at=now,
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        tenant_id=ctx.tenant_id,
        document_id=document.id,
        version_no=1,
        version_label="v0.1",
        object_key=object_key,
        sha256=content_hash,
        parse_status="pending",
        created_by=ctx.user_id,
        change_reason="初始上传版本",
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id

    add_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="document.uploaded",
        object_type="document",
        object_id=document.id,
        after_json={
            "filename": filename,
            "sha256": content_hash,
            "file_size": len(payload),
            "object_key": object_key,
        },
        reason="用户上传文件",
    )
    db.commit()
    db.refresh(document)
    db.refresh(version)
    return document_read(document, version)


@router.post(
    "/{project_id}/sections/{section_id}/documents/public-url",
    response_model=FileAcquisitionTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_public_url_acquisition(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: FileAcquisitionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> FileAcquisitionTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)

    validation = validate_public_file_url(payload.source_url)
    idempotency_source = validation.normalized_url or payload.source_url.strip()
    idempotency_key = "file-acquisition:" + hashlib.sha256(
        f"{section_id}:{idempotency_source}".encode("utf-8")
    ).hexdigest()

    existing_task = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == ctx.tenant_id,
            AsyncTask.task_type == "file_acquisition",
            AsyncTask.idempotency_key == idempotency_key,
        )
    )
    if existing_task is not None:
        existing_acquisition = db.scalar(
            select(FileAcquisitionTask).where(FileAcquisitionTask.task_id == existing_task.id)
        )
        if existing_acquisition is not None:
            return acquisition_read(existing_task, existing_acquisition)

    is_allowed = validation.is_allowed
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="file_acquisition",
        status="pending" if is_allowed else "failed",
        idempotency_key=idempotency_key,
        progress=0 if is_allowed else 100,
        input_json={
            "source_url": payload.source_url,
            "normalized_url": validation.normalized_url,
            "source_site": payload.source_site,
            "title": payload.title,
            "doc_type": payload.doc_type,
        },
        error_code=None if is_allowed else "URL_BLOCKED",
        error_message=validation.blocked_reason,
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
        finished_at=None if is_allowed else datetime.now(UTC),
    )
    db.add(task)
    db.flush()

    acquisition = FileAcquisitionTask(
        tenant_id=ctx.tenant_id,
        task_id=task.id,
        project_id=project_id,
        section_id=section_id,
        source_url=payload.source_url,
        normalized_url=validation.normalized_url,
        source_site=payload.source_site,
        fetch_method="manual_public_url",
        validation_status="allowed" if is_allowed else "blocked",
        blocked_reason=validation.blocked_reason,
    )
    db.add(acquisition)
    db.flush()

    add_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="document.public_url_requested",
        object_type="file_acquisition_task",
        object_id=acquisition.id,
        after_json=task.input_json,
        reason="用户提交公开链接获取文件",
        severity="info",
    )
    if not is_allowed:
        add_audit_log(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
            action="document.public_url_blocked",
            object_type="file_acquisition_task",
            object_id=acquisition.id,
            after_json={"source_url": payload.source_url, "blocked_reason": validation.blocked_reason},
            reason="URL 安全校验未通过",
            severity="warning",
        )

    db.commit()
    db.refresh(task)
    db.refresh(acquisition)
    if is_allowed:
        if settings.run_tasks_inline:
            result = execute_file_acquisition_task(db, task.id)
            parse_task_id = result.get("parse_async_task_id")
            if parse_task_id:
                execute_document_parse_task(db, parse_task_id)
            db.refresh(task)
            db.refresh(acquisition)
        else:
            from app.worker import run_file_acquisition_task

            try:
                enqueue_celery_task(
                    db,
                    task,
                    lambda: run_file_acquisition_task.delay(str(task.id)),
                )
            except TaskDispatchError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"文件获取任务派发失败：{exc}",
                ) from exc
            db.refresh(task)
            db.refresh(acquisition)
    return acquisition_read(task, acquisition)


@router.post(
    "/{project_id}/sections/{section_id}/documents/{document_id}/parse-tasks",
    response_model=ParseTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_parse_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: ParseTaskRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ParseTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    if document.current_version_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document has no current version",
        )

    current_version = db.get(DocumentVersion, document.current_version_id)
    target_version_id = document.current_version_id
    if current_version is not None and current_version.parser_name == "manual-editor":
        next_version_no = (
            db.scalar(
                select(func.max(DocumentVersion.version_no)).where(
                    DocumentVersion.tenant_id == ctx.tenant_id,
                    DocumentVersion.document_id == document.id,
                )
            )
            or 0
        ) + 1
        reparse_version = DocumentVersion(
            tenant_id=ctx.tenant_id,
            document_id=document.id,
            version_no=next_version_no,
            version_label=f"v0.{next_version_no}",
            object_key=document.object_key,
            sha256=document.sha256,
            parse_status="pending",
            created_by=ctx.user_id,
            change_reason="重新解析原始文件",
        )
        db.add(reparse_version)
        db.flush()
        document.current_version_id = reparse_version.id
        target_version_id = reparse_version.id

    parser_type = payload.parser_type or infer_parser_type(document.file_ext, document.content_type)
    idempotency_key = f"document-parse:{document.id}:{target_version_id}:{parser_type}"

    existing_task = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == ctx.tenant_id,
            AsyncTask.task_type == "document_parse",
            AsyncTask.idempotency_key == idempotency_key,
        )
    )
    if existing_task is not None:
        existing_parse_task = db.scalar(
            select(ParseTask).where(ParseTask.task_id == existing_task.id)
        )
        if existing_parse_task is not None:
            return parse_task_read(existing_task, existing_parse_task)

    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="document_parse",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "document_id": str(document.id),
            "document_version_id": str(target_version_id),
            "parser_type": parser_type,
            "parser_name": payload.parser_name,
        },
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()

    parse_task = ParseTask(
        tenant_id=ctx.tenant_id,
        task_id=task.id,
        document_id=document.id,
        document_version_id=target_version_id,
        parser_type=parser_type,
        parser_name=payload.parser_name,
        parser_version=payload.parser_version,
        options_json=payload.options_json,
    )
    db.add(parse_task)

    document.status = "parsing"
    target_version = db.get(DocumentVersion, target_version_id)
    if target_version is not None:
        target_version.parse_status = "parsing"

    add_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="document.parse_started",
        object_type="parse_task",
        object_id=parse_task.id,
        after_json=task.input_json,
        reason="用户创建文档解析任务",
    )
    db.commit()
    db.refresh(task)
    db.refresh(parse_task)
    if settings.run_tasks_inline:
        execute_document_parse_task(db, task.id)
        db.refresh(task)
        db.refresh(parse_task)
    else:
        from app.worker import run_document_parse_task

        try:
            enqueue_celery_task(
                db,
                task,
                lambda: run_document_parse_task.delay(str(task.id)),
            )
        except TaskDispatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"文档解析任务派发失败：{exc}",
            ) from exc
        db.refresh(task)
        db.refresh(parse_task)
    return parse_task_read(task, parse_task)


@router.get(
    "/{project_id}/sections/{section_id}/documents/{document_id}/versions/{version_id}/chunks",
    response_model=list[DocumentChunkRead],
)
def list_document_version_chunks(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[DocumentChunkRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    get_document_version_or_404(db, ctx, document=document, version_id=version_id)
    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.tenant_id == ctx.tenant_id,
            DocumentChunk.document_id == document.id,
            DocumentChunk.document_version_id == version_id,
        )
        .order_by(DocumentChunk.chunk_index.asc())
    ).all()
    return [DocumentChunkRead.model_validate(chunk) for chunk in chunks]


@router.get(
    "/{project_id}/sections/{section_id}/documents/{document_id}/versions/{version_id}/semantic-sections",
    response_model=list[DocumentSemanticSectionRead],
)
def list_document_semantic_sections(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[DocumentSemanticSectionRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    get_document_version_or_404(db, ctx, document=document, version_id=version_id)
    sections = db.scalars(
        select(DocumentSemanticSection)
        .where(
            DocumentSemanticSection.tenant_id == ctx.tenant_id,
            DocumentSemanticSection.document_id == document.id,
            DocumentSemanticSection.document_version_id == version_id,
        )
        .order_by(DocumentSemanticSection.section_index)
    ).all()
    return [DocumentSemanticSectionRead.model_validate(section) for section in sections]


@router.post(
    "/{project_id}/sections/{section_id}/documents/{document_id}/versions/{version_id}/semantic-sections/replan",
    response_model=list[DocumentSemanticSectionRead],
    status_code=status.HTTP_202_ACCEPTED,
)
def replan_document_semantic_sections(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[DocumentSemanticSectionRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    version = get_document_version_or_404(db, ctx, document=document, version_id=version_id)
    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.tenant_id == ctx.tenant_id,
            DocumentChunk.document_id == document.id,
            DocumentChunk.document_version_id == version.id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document version has no chunks")

    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="document_section_plan",
        status="running",
        idempotency_key=f"document-section-plan:{version.id}:{uuid.uuid4().hex}",
        progress=20,
        input_json={"document_id": str(document.id), "document_version_id": str(version.id), "force": True},
        retry_count=0,
        max_retries=0,
        created_by=ctx.user_id,
        started_at=datetime.now(UTC),
    )
    db.add(task)
    db.flush()
    try:
        sections = ensure_document_section_plan(db, task, document, version, list(chunks), force=True)
        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "section_count": len(sections),
        }
        task.finished_at = datetime.now(UTC)
        add_audit_log(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
            action="document.semantic_sections_replanned",
            object_type="document_version",
            object_id=version.id,
            after_json=task.output_json,
            reason="用户重新规划招标文件章节",
        )
        db.commit()
        return [DocumentSemanticSectionRead.model_validate(section) for section in sections]
    except Exception as exc:
        error_code = getattr(exc, "code", "DOCUMENT_SECTION_PLAN_FAILED")
        task.status = "failed"
        task.progress = 100
        task.error_code = error_code
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        db.add(
            DocumentExtractionQualityReport(
                tenant_id=ctx.tenant_id,
                task_id=task.id,
                document_id=document.id,
                document_version_id=version.id,
                section_id=section_id,
                status="blocked",
                issues_json=[
                    {
                        "severity": "high",
                        "code": error_code,
                        "message": str(exc),
                    }
                ],
                summary_json={
                    "document_id": str(document.id),
                    "document_version_id": str(version.id),
                },
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{project_id}/sections/{section_id}/document-semantic-sections/{semantic_section_id}/extract-compliance",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def extract_document_semantic_section_compliance(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    semantic_section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AsyncTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    semantic_section = db.scalar(
        select(DocumentSemanticSection).where(
            DocumentSemanticSection.tenant_id == ctx.tenant_id,
            DocumentSemanticSection.section_id == section_id,
            DocumentSemanticSection.id == semantic_section_id,
        )
    )
    if semantic_section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semantic section not found")

    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="section_compliance_extract",
        status="pending",
        idempotency_key=f"section-compliance-extract:{semantic_section_id}:{uuid.uuid4().hex}",
        progress=0,
        input_json={"semantic_section_id": str(semantic_section_id), "force": True},
        retry_count=0,
        max_retries=0,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    add_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="document.semantic_section_extract_requested",
        object_type="document_semantic_section",
        object_id=semantic_section_id,
        after_json=task.input_json,
        reason="用户请求重抽当前语义段",
    )
    db.commit()
    execute_section_compliance_extract_task(db, task.id)
    db.refresh(task)
    return async_task_read(task)


@router.get(
    "/{project_id}/sections/{section_id}/documents/{document_id}/versions/{version_id}/extraction-quality-report",
    response_model=DocumentExtractionQualityReportRead | None,
)
def get_document_extraction_quality_report(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DocumentExtractionQualityReportRead | None:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    get_document_version_or_404(db, ctx, document=document, version_id=version_id)
    report = latest_extraction_quality_report(
        db,
        tenant_id=ctx.tenant_id,
        document_version_id=version_id,
    )
    return DocumentExtractionQualityReportRead.model_validate(report) if report else None


@router.post(
    "/{project_id}/sections/{section_id}/documents/{document_id}/versions/{version_id}/manual-revisions",
    response_model=DocumentManualRevisionResult,
    status_code=status.HTTP_201_CREATED,
)
def publish_document_manual_revision(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: DocumentManualRevisionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DocumentManualRevisionResult:
    get_section_or_404(db, ctx, project_id, section_id)
    document = get_document_or_404(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        document_id=document_id,
    )
    source_version = get_document_version_or_404(db, ctx, document=document, version_id=version_id)
    chunk_indexes = [chunk.chunk_index for chunk in payload.chunks]
    if len(set(chunk_indexes)) != len(chunk_indexes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk indexes must be unique")

    next_version_no = (
        db.scalar(
            select(func.max(DocumentVersion.version_no)).where(
                DocumentVersion.tenant_id == ctx.tenant_id,
                DocumentVersion.document_id == document.id,
            )
        )
        or 0
    ) + 1
    combined_text = "\n".join(
        f"{chunk.chunk_index}:{chunk.heading_path or ''}:{chunk.page_no or ''}:{chunk.content_text}"
        for chunk in sorted(payload.chunks, key=lambda item: item.chunk_index)
    )
    revision_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()
    new_version = DocumentVersion(
        tenant_id=ctx.tenant_id,
        document_id=document.id,
        version_no=next_version_no,
        version_label=f"v0.{next_version_no}",
        object_key=source_version.object_key,
        sha256=revision_hash,
        parse_status="succeeded",
        parser_name="manual-editor",
        parser_version="1.0",
        created_by=ctx.user_id,
        change_reason=payload.reason.strip(),
    )
    db.add(new_version)
    db.flush()

    created_chunks: list[DocumentChunk] = []
    for index, chunk in enumerate(sorted(payload.chunks, key=lambda item: item.chunk_index), start=1):
        content_text = chunk.content_text.strip()
        saved = DocumentChunk(
            tenant_id=ctx.tenant_id,
            document_id=document.id,
            document_version_id=new_version.id,
            section_id=document.section_id,
            chunk_index=index,
            page_no=chunk.page_no,
            heading_path=chunk.heading_path.strip() if chunk.heading_path else None,
            content_text=content_text,
            content_hash=hashlib.sha256(content_text.encode("utf-8")).hexdigest(),
            bbox_json=chunk.bbox_json,
            table_json=chunk.table_json,
        )
        db.add(saved)
        created_chunks.append(saved)

    document.current_version_id = new_version.id
    document.status = "available"
    add_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="document.manual_revision_published",
        object_type="document_version",
        object_id=new_version.id,
        after_json={
            "document_id": str(document.id),
            "source_version_id": str(source_version.id),
            "new_version_id": str(new_version.id),
            "new_version_label": new_version.version_label,
            "chunk_count": len(created_chunks),
            "content_sha256": revision_hash,
        },
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(document)
    db.refresh(source_version)
    db.refresh(new_version)
    for chunk in created_chunks:
        db.refresh(chunk)
    return DocumentManualRevisionResult(
        document=document_read(document, new_version),
        source_version=DocumentVersionRead.model_validate(source_version),
        new_version=DocumentVersionRead.model_validate(new_version),
        chunks=[DocumentChunkRead.model_validate(chunk) for chunk in created_chunks],
    )
