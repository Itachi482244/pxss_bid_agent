from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AsyncTask, AuditLog, Document, DocumentChunk, DocumentVersion, ParseTask
from app.parsers.pdf import parse_pdf_bytes
from app.parsers.word import parse_docx_bytes
from app.services.storage import get_object_bytes


class DocumentParseError(Exception):
    def __init__(self, message: str, *, code: str = "DOCUMENT_PARSE_FAILED") -> None:
        super().__init__(message)
        self.code = code


def _coerce_task_id(task_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    try:
        return uuid.UUID(str(task_id))
    except ValueError as exc:
        raise DocumentParseError("任务ID格式错误", code="INVALID_TASK_ID") from exc


def _add_parse_audit(
    db: Session,
    task: AsyncTask,
    parse_task: ParseTask,
    *,
    action: str,
    after_json: dict | None = None,
    reason: str | None = None,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            actor_user_id=task.created_by,
            actor_type="worker",
            action=action,
            object_type="parse_task",
            object_id=parse_task.id,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def _parse_document_bytes(parse_task: ParseTask, document: Document, data: bytes):
    if parse_task.parser_type == "pdf_text":
        if document.file_ext != "pdf":
            raise DocumentParseError("PDF 文本解析器仅支持 .pdf 文件", code="PDF_FILE_REQUIRED")
        return parse_pdf_bytes(data)
    if parse_task.parser_type != "word":
        raise DocumentParseError(
            f"暂不支持解析类型：{parse_task.parser_type}",
            code="UNSUPPORTED_PARSER_TYPE",
        )
    if document.file_ext == "doc":
        raise DocumentParseError("暂不支持旧版 .doc 文件，请先转换为 .docx", code="LEGACY_DOC_UNSUPPORTED")
    if document.file_ext != "docx":
        raise DocumentParseError("Word 解析器仅支持 .docx 文件", code="WORD_FILE_REQUIRED")
    return parse_docx_bytes(data)


def _load_parse_context(
    db: Session,
    task_id: uuid.UUID | str,
) -> tuple[AsyncTask, ParseTask, Document, DocumentVersion]:
    task_uuid = _coerce_task_id(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "document_parse":
        raise DocumentParseError("文档解析任务不存在", code="TASK_NOT_FOUND")

    parse_task = db.scalar(select(ParseTask).where(ParseTask.task_id == task.id))
    if parse_task is None:
        raise DocumentParseError("文档解析任务详情不存在", code="TASK_DETAIL_NOT_FOUND")

    document = db.get(Document, parse_task.document_id)
    version = db.get(DocumentVersion, parse_task.document_version_id)
    if document is None or version is None:
        raise DocumentParseError("待解析文档或版本不存在", code="DOCUMENT_NOT_FOUND")
    if document.tenant_id != task.tenant_id or version.tenant_id != task.tenant_id:
        raise DocumentParseError("任务与文档租户不一致", code="TENANT_MISMATCH")
    return task, parse_task, document, version


def execute_document_parse_task(db: Session, task_id: uuid.UUID | str) -> dict[str, str | int]:
    task, parse_task, document, version = _load_parse_context(db, task_id)

    if task.status == "succeeded" and version.parse_status in {"succeeded", "frozen"}:
        chunk_count = db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.tenant_id == task.tenant_id,
                DocumentChunk.document_version_id == version.id,
            )
        )
        return {
            "status": "already_succeeded",
            "document_id": str(document.id),
            "chunk_count": chunk_count or 0,
        }

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = 20
    document.status = "parsing"
    version.parse_status = "parsing"
    db.commit()

    try:
        data = get_object_bytes(bucket=document.bucket, object_key=version.object_key)
        parsed_chunks = _parse_document_bytes(parse_task, document, data)

        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.tenant_id == task.tenant_id,
                DocumentChunk.document_version_id == version.id,
            )
        )
        for chunk in parsed_chunks:
            db.add(
                DocumentChunk(
                    tenant_id=task.tenant_id,
                    document_id=document.id,
                    document_version_id=version.id,
                    section_id=document.section_id,
                    chunk_index=chunk.chunk_index,
                    page_no=getattr(chunk, "page_no", None),
                    heading_path=chunk.heading_path,
                    content_text=chunk.content_text,
                    content_hash=hashlib.sha256(chunk.content_text.encode("utf-8")).hexdigest(),
                    bbox_json=getattr(chunk, "bbox_json", None),
                    table_json=chunk.table_json,
                )
            )

        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "chunk_count": len(parsed_chunks),
        }
        task.finished_at = datetime.now(UTC)
        parse_task.result_summary_json = {
            "chunk_count": len(parsed_chunks),
            "parser_type": parse_task.parser_type,
        }
        document.status = "available"
        version.parse_status = "succeeded"
        version.parser_name = parse_task.parser_name
        version.parser_version = parse_task.parser_version

        _add_parse_audit(
            db,
            task,
            parse_task,
            action="document.parse_succeeded",
            after_json=task.output_json,
            reason="Worker 完成 Word 文档解析并写入分块",
        )
        db.commit()
        return {
            "status": "succeeded",
            "document_id": str(document.id),
            "chunk_count": len(parsed_chunks),
        }
    except Exception as exc:
        error_code = exc.code if isinstance(exc, DocumentParseError) else "DOCUMENT_PARSE_FAILED"
        task.status = "failed"
        task.progress = 100
        task.error_code = error_code
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        document.status = "parse_failed"
        version.parse_status = "failed"
        _add_parse_audit(
            db,
            task,
            parse_task,
            action="document.parse_failed",
            after_json={"error_code": error_code, "error_message": str(exc)},
            reason="Worker 解析文档失败",
            severity="warning",
        )
        db.commit()
        return {"status": "failed", "error_code": error_code}
