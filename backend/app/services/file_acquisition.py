from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import observed_task
from app.models import AsyncTask, AuditLog, Document, DocumentVersion, FileAcquisitionTask, ParseTask
from app.services.document_utils import (
    MAX_FILE_BYTES,
    file_extension,
    infer_parser_type,
    safe_filename,
)
from app.services.storage import put_object_bytes
from app.services.url_safety import validate_public_file_url


@dataclass(frozen=True)
class DownloadedFile:
    final_url: str
    filename: str
    content_type: str | None
    content_length: int
    http_status: int
    redirect_chain: list[str]
    data: bytes


class FileAcquisitionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "FILE_ACQUISITION_FAILED",
        http_status: int | None = None,
        redirect_chain: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.redirect_chain = redirect_chain or []


def _filename_from_response(url: str, headers: httpx.Headers) -> str:
    disposition = headers.get("content-disposition")
    if disposition:
        message = Message()
        message["content-disposition"] = disposition
        filename = message.get_filename()
        if filename:
            return safe_filename(filename)

    path_name = Path(urlparse(url).path).name
    return safe_filename(path_name or "downloaded-document.bin")


def fetch_public_file(url: str, *, max_redirects: int = 5) -> DownloadedFile:
    validation = validate_public_file_url(url)
    if not validation.is_allowed or validation.normalized_url is None:
        raise FileAcquisitionError(
            validation.blocked_reason or "URL 安全校验未通过",
            code="URL_BLOCKED",
        )

    current_url = validation.normalized_url
    redirect_chain: list[str] = []
    try:
        with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0), follow_redirects=False) as client:
            for _ in range(max_redirects + 1):
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FileAcquisitionError(
                                "重定向响应缺少 Location",
                                code="INVALID_REDIRECT",
                                http_status=response.status_code,
                                redirect_chain=redirect_chain,
                            )
                        next_url = urljoin(current_url, location)
                        next_validation = validate_public_file_url(next_url)
                        if not next_validation.is_allowed or next_validation.normalized_url is None:
                            raise FileAcquisitionError(
                                next_validation.blocked_reason or "重定向 URL 安全校验未通过",
                                code="URL_BLOCKED",
                                http_status=response.status_code,
                                redirect_chain=[*redirect_chain, next_url],
                            )
                        redirect_chain.append(next_validation.normalized_url)
                        current_url = next_validation.normalized_url
                        continue

                    if response.status_code >= 400:
                        raise FileAcquisitionError(
                            f"远端文件下载失败，HTTP {response.status_code}",
                            code="HTTP_ERROR",
                            http_status=response.status_code,
                            redirect_chain=redirect_chain,
                        )

                    content_length_header = response.headers.get("content-length")
                    if content_length_header:
                        try:
                            declared_size = int(content_length_header)
                        except ValueError as exc:
                            raise FileAcquisitionError(
                                "远端文件 Content-Length 非法",
                                code="INVALID_CONTENT_LENGTH",
                                http_status=response.status_code,
                                redirect_chain=redirect_chain,
                            ) from exc
                        if declared_size > MAX_FILE_BYTES:
                            raise FileAcquisitionError(
                                "远端文件超过大小限制",
                                code="FILE_TOO_LARGE",
                                http_status=response.status_code,
                                redirect_chain=redirect_chain,
                            )

                    chunks: list[bytes] = []
                    total_size = 0
                    for chunk in response.iter_bytes():
                        total_size += len(chunk)
                        if total_size > MAX_FILE_BYTES:
                            raise FileAcquisitionError(
                                "远端文件超过大小限制",
                                code="FILE_TOO_LARGE",
                                http_status=response.status_code,
                                redirect_chain=redirect_chain,
                            )
                        chunks.append(chunk)

                    return DownloadedFile(
                        final_url=current_url,
                        filename=_filename_from_response(current_url, response.headers),
                        content_type=response.headers.get("content-type"),
                        content_length=total_size,
                        http_status=response.status_code,
                        redirect_chain=redirect_chain,
                        data=b"".join(chunks),
                    )

            raise FileAcquisitionError(
                "重定向次数超过限制",
                code="TOO_MANY_REDIRECTS",
                redirect_chain=redirect_chain,
            )
    except httpx.HTTPError as exc:
        raise FileAcquisitionError(
            "远端文件连接失败",
            code="NETWORK_ERROR",
            redirect_chain=redirect_chain,
        ) from exc


def _coerce_task_id(task_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    try:
        return uuid.UUID(str(task_id))
    except ValueError as exc:
        raise FileAcquisitionError("任务ID格式错误", code="INVALID_TASK_ID") from exc


def _add_worker_audit(
    db: Session,
    task: AsyncTask,
    acquisition: FileAcquisitionTask,
    *,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
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
            object_type=object_type,
            object_id=object_id,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def _create_parse_task_if_missing(
    db: Session,
    *,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
) -> ParseTask:
    parser_type = infer_parser_type(document.file_ext, document.content_type)
    idempotency_key = f"document-parse:{document.id}:{version.id}:{parser_type}"
    existing_task = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == task.tenant_id,
            AsyncTask.task_type == "document_parse",
            AsyncTask.idempotency_key == idempotency_key,
        )
    )
    if existing_task is not None:
        existing_parse_task = db.scalar(select(ParseTask).where(ParseTask.task_id == existing_task.id))
        if existing_parse_task is not None:
            return existing_parse_task

    parse_async_task = AsyncTask(
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        section_id=task.section_id,
        task_type="document_parse",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "parser_type": parser_type,
            "parser_name": "mvp-parser",
            "trigger": "file_acquisition",
        },
        retry_count=0,
        max_retries=3,
        created_by=task.created_by,
    )
    db.add(parse_async_task)
    db.flush()

    parse_task = ParseTask(
        tenant_id=task.tenant_id,
        task_id=parse_async_task.id,
        document_id=document.id,
        document_version_id=version.id,
        parser_type=parser_type,
        parser_name="mvp-parser",
        parser_version="0.1.0",
        options_json={"trigger": "file_acquisition"},
    )
    db.add(parse_task)
    db.flush()
    document.status = "parsing"
    version.parse_status = "parsing"
    return parse_task


@observed_task("file_acquisition")
def execute_file_acquisition_task(db: Session, task_id: uuid.UUID | str) -> dict[str, str]:
    task_uuid = _coerce_task_id(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "file_acquisition":
        raise FileAcquisitionError("文件获取任务不存在", code="TASK_NOT_FOUND")

    acquisition = db.scalar(select(FileAcquisitionTask).where(FileAcquisitionTask.task_id == task.id))
    if acquisition is None:
        raise FileAcquisitionError("文件获取任务详情不存在", code="TASK_DETAIL_NOT_FOUND")

    if acquisition.target_document_id is not None and task.status == "succeeded":
        return {"status": "already_succeeded", "document_id": str(acquisition.target_document_id)}

    if acquisition.validation_status == "blocked":
        return {"status": "blocked", "task_id": str(task.id)}

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = 20
    db.commit()

    try:
        downloaded = fetch_public_file(acquisition.normalized_url or acquisition.source_url)
        filename = safe_filename(downloaded.filename)
        ext = file_extension(filename)
        content_hash = hashlib.sha256(downloaded.data).hexdigest()
        document_id = uuid.uuid4()
        object_key = (
            f"tenant/{task.tenant_id}/project/{task.project_id}/section/{task.section_id}/"
            f"documents/{document_id}/v1/{filename}"
        )

        put_object_bytes(
            bucket=settings.minio_bucket,
            object_key=object_key,
            data=downloaded.data,
            content_type=downloaded.content_type,
        )

        task.progress = 70
        document = Document(
            id=document_id,
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            doc_type=(task.input_json or {}).get("doc_type", "tender"),
            title=(task.input_json or {}).get("title") or Path(filename).stem or filename,
            source_type="public_url",
            source_site=acquisition.source_site,
            source_url=acquisition.source_url,
            original_filename=filename,
            content_type=downloaded.content_type,
            file_ext=ext,
            file_size=downloaded.content_length,
            sha256=content_hash,
            bucket=settings.minio_bucket,
            object_key=object_key,
            status="available",
            created_by=task.created_by,
            acquired_at=datetime.now(UTC),
        )
        db.add(document)
        db.flush()

        version = DocumentVersion(
            tenant_id=task.tenant_id,
            document_id=document.id,
            version_no=1,
            version_label="v0.1",
            object_key=object_key,
            sha256=content_hash,
            parse_status="pending",
            created_by=task.created_by,
            change_reason="公开链接获取初始版本",
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id

        acquisition.target_document_id = document.id
        acquisition.http_status = downloaded.http_status
        acquisition.content_type = downloaded.content_type
        acquisition.content_length = downloaded.content_length
        acquisition.redirect_chain_json = {"items": downloaded.redirect_chain}

        parse_task = _create_parse_task_if_missing(db, task=task, document=document, version=version)

        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "parse_task_id": str(parse_task.id),
            "parse_async_task_id": str(parse_task.task_id),
            "sha256": content_hash,
            "file_size": downloaded.content_length,
            "final_url": downloaded.final_url,
        }
        task.finished_at = datetime.now(UTC)

        _add_worker_audit(
            db,
            task,
            acquisition,
            action="document.public_url_downloaded",
            object_type="document",
            object_id=document.id,
            after_json=task.output_json,
            reason="Worker 下载公开附件并创建文件记录",
        )
        _add_worker_audit(
            db,
            task,
            acquisition,
            action="document.parse_started",
            object_type="parse_task",
            object_id=parse_task.id,
            after_json={"document_id": str(document.id), "document_version_id": str(version.id)},
            reason="公开附件获取完成后自动创建解析任务",
        )
        db.commit()
        return {
            "status": "succeeded",
            "document_id": str(document.id),
            "parse_async_task_id": str(parse_task.task_id),
        }

    except FileAcquisitionError as exc:
        task.status = "failed"
        task.progress = 100
        task.error_code = exc.code
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        acquisition.blocked_reason = str(exc)
        acquisition.http_status = exc.http_status
        acquisition.redirect_chain_json = {"items": exc.redirect_chain}
        _add_worker_audit(
            db,
            task,
            acquisition,
            action="document.public_url_download_failed",
            object_type="file_acquisition_task",
            object_id=acquisition.id,
            after_json={"error_code": exc.code, "error_message": str(exc)},
            reason="Worker 获取公开附件失败",
            severity="warning",
        )
        db.commit()
        return {"status": "failed", "error_code": exc.code}
