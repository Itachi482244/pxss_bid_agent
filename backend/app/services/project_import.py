from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    AsyncTask,
    AuditLog,
    BidSection,
    Document,
    DocumentChunk,
    DocumentVersion,
    ParseTask,
    Project,
    ProjectMember,
)
from app.parsers.html import html_bytes_to_text, parse_html_bytes
from app.parsers.pdf import parse_pdf_bytes
from app.parsers.word import parse_docx_bytes
from app.services.compliance_generation import execute_compliance_matrix_generation_task
from app.services.document_conversion import convert_legacy_doc_to_docx
from app.services.document_parse import execute_document_parse_task
from app.services.document_utils import file_extension, infer_parser_type, safe_filename
from app.services.file_acquisition import fetch_public_file
from app.services.storage import get_object_bytes, put_object_bytes


MAX_PREVIEW_CHARS = 4000
MAX_EXTRACT_CHARS = 160000
CHINA_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class ImportSource:
    draft_id: uuid.UUID
    source_type: str
    source_site: str | None
    source_url: str | None
    original_filename: str
    content_type: str | None
    file_ext: str | None
    file_size: int
    sha256: str
    staged_object_key: str
    acquired_at: datetime


@dataclass(frozen=True)
class ProjectFieldDraft:
    name: str
    purchaser: str | None
    agency: str | None
    budget_amount: Decimal | None
    region_code: str | None
    industry_code: str | None
    notice_url: str | None
    bid_deadline_at: datetime | None


@dataclass(frozen=True)
class SectionFieldDraft:
    code: str | None
    name: str
    budget_amount: Decimal | None
    bid_deadline_at: datetime | None


@dataclass(frozen=True)
class ImportDraft:
    source: ImportSource
    project: ProjectFieldDraft
    sections: list[SectionFieldDraft]
    confidence: dict[str, float]
    warnings: list[str]
    preview_text: str


@dataclass(frozen=True)
class ImportConfirmResult:
    project_id: uuid.UUID
    section_id: uuid.UUID
    document_id: uuid.UUID
    parse_task_id: uuid.UUID | None
    matrix_task_id: uuid.UUID | None


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.replace("\xa0", " ").split()).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _line_value(patterns: tuple[str, ...], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1 if match.lastindex else 0).strip()
            value = re.split(r"\s{2,}|(?:\n)", value)[0].strip()
            return value.rstrip("。；;").strip()
    return None


def _clean_name(value: str | None, fallback: str) -> str:
    if value:
        cleaned = re.sub(r"(招标公告|招标文件|资格预审公告)$", "", value).strip(" ：:")
        cleaned = re.sub(r"(工程总承包|施工总承包|设计施工总承包)$", "", cleaned).strip(" ：:")
        if cleaned:
            return cleaned[:300]
    return Path(fallback).stem[:300] or "未命名投标项目"


def _extract_project_name(text: str, fallback: str) -> str:
    explicit = _line_value(
        (
            r"(?:项目名称|招标项目名称|工程名称)\s*[:：]\s*([^\n]+)",
            r"^\s*([^\n]{6,120}?(?:项目|工程|采购)[^\n]{0,40}?)\s*(?:招标公告|招标文件)\s*$",
        ),
        text,
    )
    if explicit:
        return _clean_name(explicit, fallback)

    for line in text.splitlines()[:30]:
        if any(signal in line for signal in ("招标公告", "招标文件")) and any(
            key in line for key in ("项目", "工程")
        ):
            return _clean_name(line, fallback)
    return _clean_name(None, fallback)


def _parse_decimal_amount(value: str, unit: str | None) -> Decimal | None:
    try:
        amount = Decimal(value.replace(",", "").replace("，", ""))
    except InvalidOperation:
        return None
    if unit and "万" in unit:
        amount *= Decimal("10000")
    return amount.quantize(Decimal("0.01"))


def _extract_budget(text: str) -> Decimal | None:
    match = re.search(
        r"(?:最高投标限价|招标控制价|预算金额|项目总投资|投资额)[^0-9]{0,30}"
        r"([0-9][0-9,.，]*)\s*(万元|元)?",
        text,
    )
    if not match:
        return None
    return _parse_decimal_amount(match.group(1), match.group(2))


def _date_from_match(match: re.Match[str]) -> datetime:
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    hour = int(match.group(4) or 0)
    minute = int(match.group(5) or 0)
    prefix = match.group(0)
    if "下午" in prefix and hour < 12:
        hour += 12
    local_dt = datetime(year, month, day, hour, minute, tzinfo=CHINA_TZ)
    return local_dt.astimezone(UTC)


def _extract_deadline(text: str) -> datetime | None:
    candidates = []
    for keyword in ("投标截止时间", "递交截止时间", "开标时间", "截止时间"):
        index = text.find(keyword)
        if index >= 0:
            candidates.append(text[index : index + 120])
    candidates.append(text[:MAX_EXTRACT_CHARS])
    for candidate in candidates:
        match = re.search(
            r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*"
            r"(?:上午|下午)?\s*(\d{1,2})?\s*(?:时|:|：)?\s*(\d{1,2})?",
            candidate,
        )
        if match:
            return _date_from_match(match)
        match = re.search(
            r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*(\d{1,2})?[:：]?(\d{1,2})?",
            candidate,
        )
        if match:
            return _date_from_match(match)
    return None


def _infer_region_code(text: str) -> str | None:
    if "岳阳市君山区" in text or "君山区" in text:
        return "CN-430611"
    if "岳阳市" in text:
        return "CN-4306"
    if "湖南" in text:
        return "CN-43"
    return None


def _infer_industry_code(text: str) -> str | None:
    if "燃气" in text or "管网" in text:
        return "municipal-gas"
    if "弱电" in text or "安防" in text:
        return "weak-current"
    if "市政" in text:
        return "municipal"
    return None


def _extract_section_name(text: str, project_name: str) -> str:
    explicit = _line_value(
        (
            r"(?:标段名称|标段编号及名称)\s*[:：]\s*([^\n]+)",
            r"(?:本项目|该项目)分为\s*一个标段",
        ),
        text,
    )
    if explicit and "一个标段" not in explicit:
        return explicit[:300]
    return f"一标段：{project_name}"[:300]


def extract_project_draft(text: str, *, fallback_name: str, source_url: str | None) -> tuple[
    ProjectFieldDraft,
    list[SectionFieldDraft],
    dict[str, float],
    list[str],
]:
    text = _normalize_text(text)[:MAX_EXTRACT_CHARS]
    project_name = _extract_project_name(text, fallback_name)
    purchaser = _line_value(
        (
            r"(?:招标人|采购人|建设单位)\s*[:：]\s*([^\n]+)",
            r"(?:招 标 人|采 购 人)\s*[:：]\s*([^\n]+)",
        ),
        text,
    )
    agency = _line_value(
        (
            r"(?:招标代理机构|采购代理机构|代理机构)\s*[:：]\s*([^\n]+)",
            r"(?:招标代理|采购代理)\s*[:：]\s*([^\n]+)",
        ),
        text,
    )
    budget_amount = _extract_budget(text)
    deadline = _extract_deadline(text)
    region_code = _infer_region_code(text)
    industry_code = _infer_industry_code(text)
    section_name = _extract_section_name(text, project_name)

    confidence = {
        "name": 0.88 if project_name != Path(fallback_name).stem else 0.45,
        "purchaser": 0.82 if purchaser else 0.0,
        "agency": 0.78 if agency else 0.0,
        "budget_amount": 0.76 if budget_amount is not None else 0.0,
        "bid_deadline_at": 0.80 if deadline is not None else 0.0,
        "region_code": 0.62 if region_code else 0.0,
        "industry_code": 0.62 if industry_code else 0.0,
        "section_name": 0.70,
    }
    warnings: list[str] = []
    if not purchaser:
        warnings.append("未识别到招标人/采购人，请确认后再创建。")
    if budget_amount is None:
        warnings.append("未识别到预算或最高投标限价。")
    if deadline is None:
        warnings.append("未识别到投标截止时间。")

    project = ProjectFieldDraft(
        name=project_name,
        purchaser=purchaser,
        agency=agency,
        budget_amount=budget_amount,
        region_code=region_code,
        industry_code=industry_code,
        notice_url=source_url,
        bid_deadline_at=deadline,
    )
    sections = [
        SectionFieldDraft(
            code="section-001",
            name=section_name,
            budget_amount=budget_amount,
            bid_deadline_at=deadline,
        )
    ]
    return project, sections, confidence, warnings


def _text_from_source(data: bytes, *, filename: str, content_type: str | None) -> str:
    ext = file_extension(filename)
    if ext == "doc":
        data = convert_legacy_doc_to_docx(data, filename=filename)
        return "\n".join(chunk.content_text for chunk in parse_docx_bytes(data))
    if ext == "docx":
        return "\n".join(chunk.content_text for chunk in parse_docx_bytes(data))
    if ext == "pdf":
        return "\n".join(chunk.content_text for chunk in parse_pdf_bytes(data))
    if ext in {"html", "htm"} or (content_type and "html" in content_type):
        return html_bytes_to_text(data, content_type)
    return data.decode("utf-8", errors="replace")


def _stage_source(
    *,
    ctx: RequestContext,
    draft_id: uuid.UUID,
    filename: str,
    data: bytes,
    content_type: str | None,
) -> tuple[str, str]:
    content_hash = hashlib.sha256(data).hexdigest()
    object_key = f"tenant/{ctx.tenant_id}/project-imports/{draft_id}/{filename}"
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=content_type,
    )
    return object_key, content_hash


def build_upload_import_draft(
    *,
    ctx: RequestContext,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> ImportDraft:
    draft_id = uuid.uuid4()
    safe_name = safe_filename(filename)
    staged_object_key, content_hash = _stage_source(
        ctx=ctx,
        draft_id=draft_id,
        filename=safe_name,
        data=data,
        content_type=content_type,
    )
    text = _text_from_source(data, filename=safe_name, content_type=content_type)
    project, sections, confidence, warnings = extract_project_draft(
        text,
        fallback_name=safe_name,
        source_url=None,
    )
    source = ImportSource(
        draft_id=draft_id,
        source_type="manual_import",
        source_site=None,
        source_url=None,
        original_filename=safe_name,
        content_type=content_type,
        file_ext=file_extension(safe_name),
        file_size=len(data),
        sha256=content_hash,
        staged_object_key=staged_object_key,
        acquired_at=datetime.now(UTC),
    )
    return ImportDraft(
        source=source,
        project=project,
        sections=sections,
        confidence=confidence,
        warnings=warnings,
        preview_text=_normalize_text(text)[:MAX_PREVIEW_CHARS],
    )


def build_url_import_draft(
    *,
    ctx: RequestContext,
    source_url: str,
    source_site: str | None,
    title: str | None,
) -> ImportDraft:
    downloaded = fetch_public_file(source_url)
    draft_id = uuid.uuid4()
    filename = safe_filename(downloaded.filename)
    if "." not in filename and downloaded.content_type and "html" in downloaded.content_type:
        filename = f"{filename}.html"
    staged_object_key, content_hash = _stage_source(
        ctx=ctx,
        draft_id=draft_id,
        filename=filename,
        data=downloaded.data,
        content_type=downloaded.content_type,
    )
    text = _text_from_source(data=downloaded.data, filename=filename, content_type=downloaded.content_type)
    fallback_name = title or filename
    project, sections, confidence, warnings = extract_project_draft(
        text,
        fallback_name=fallback_name,
        source_url=downloaded.final_url,
    )
    hostname = urlparse(downloaded.final_url).hostname
    source = ImportSource(
        draft_id=draft_id,
        source_type="public_url",
        source_site=source_site or hostname,
        source_url=downloaded.final_url,
        original_filename=filename,
        content_type=downloaded.content_type,
        file_ext=file_extension(filename),
        file_size=downloaded.content_length,
        sha256=content_hash,
        staged_object_key=staged_object_key,
        acquired_at=datetime.now(UTC),
    )
    return ImportDraft(
        source=source,
        project=project,
        sections=sections,
        confidence=confidence,
        warnings=warnings,
        preview_text=_normalize_text(text)[:MAX_PREVIEW_CHARS],
    )


def _add_audit(
    db: Session,
    *,
    ctx: RequestContext,
    project_id: uuid.UUID,
    section_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    after_json: dict | None,
    reason: str,
    actor_type: str = "user",
) -> None:
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            actor_type=actor_type,
            action=action,
            object_type=object_type,
            object_id=object_id,
            after_json=after_json,
            reason=reason,
        )
    )


def _clean_optional_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _create_document_from_staged_source(
    db: Session,
    *,
    ctx: RequestContext,
    project: Project,
    section: BidSection,
    source: dict,
) -> tuple[Document, DocumentVersion, bytes]:
    object_key = str(source["staged_object_key"])
    prefix = f"tenant/{ctx.tenant_id}/project-imports/{source['draft_id']}/"
    if not object_key.startswith(prefix):
        raise ValueError("导入草稿来源不属于当前租户")
    data = get_object_bytes(bucket=settings.minio_bucket, object_key=object_key)
    content_hash = hashlib.sha256(data).hexdigest()
    if content_hash != source["sha256"]:
        raise ValueError("导入草稿文件哈希不一致，请重新导入")

    filename = safe_filename(str(source["original_filename"]))
    final_object_key = (
        f"tenant/{ctx.tenant_id}/project/{project.id}/section/{section.id}/"
        f"documents/{uuid.uuid4()}/v1/{filename}"
    )
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=final_object_key,
        data=data,
        content_type=source.get("content_type"),
    )
    document = Document(
        tenant_id=ctx.tenant_id,
        project_id=project.id,
        section_id=section.id,
        doc_type="tender",
        title=Path(filename).stem or filename,
        source_type=source["source_type"],
        source_site=source.get("source_site"),
        source_url=source.get("source_url"),
        original_filename=filename,
        content_type=source.get("content_type"),
        file_ext=source.get("file_ext"),
        file_size=len(data),
        sha256=content_hash,
        bucket=settings.minio_bucket,
        object_key=final_object_key,
        status="available",
        created_by=ctx.user_id,
        acquired_at=datetime.now(UTC),
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        tenant_id=ctx.tenant_id,
        document_id=document.id,
        version_no=1,
        version_label="v0.1",
        object_key=final_object_key,
        sha256=content_hash,
        parse_status="pending",
        created_by=ctx.user_id,
        change_reason="项目导入来源初始版本",
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id
    return document, version, data


def _create_parse_task(
    db: Session,
    *,
    ctx: RequestContext,
    project: Project,
    section: BidSection,
    document: Document,
    version: DocumentVersion,
) -> AsyncTask:
    parser_type = infer_parser_type(document.file_ext, document.content_type)
    idempotency_key = f"document-parse:{document.id}:{version.id}:{parser_type}"
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project.id,
        section_id=section.id,
        task_type="document_parse",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "parser_type": parser_type,
            "parser_name": "mvp-parser",
            "trigger": "project_import",
        },
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    db.add(
        ParseTask(
            tenant_id=ctx.tenant_id,
            task_id=task.id,
            document_id=document.id,
            document_version_id=version.id,
            parser_type=parser_type,
            parser_name="mvp-parser",
            parser_version="0.1.0",
            options_json={"trigger": "project_import"},
        )
    )
    document.status = "parsing"
    version.parse_status = "parsing"
    return task


def _parse_html_document(
    db: Session,
    *,
    ctx: RequestContext,
    project: Project,
    section: BidSection,
    document: Document,
    version: DocumentVersion,
    data: bytes,
) -> None:
    chunks = parse_html_bytes(data, document.content_type)
    for chunk in chunks:
        db.add(
            DocumentChunk(
                tenant_id=ctx.tenant_id,
                document_id=document.id,
                document_version_id=version.id,
                section_id=section.id,
                chunk_index=chunk.chunk_index,
                heading_path=chunk.heading_path,
                content_text=chunk.content_text,
                content_hash=hashlib.sha256(chunk.content_text.encode("utf-8")).hexdigest(),
                table_json=chunk.table_json,
            )
        )
    document.status = "available"
    version.parse_status = "succeeded"
    version.parser_name = "html-import-parser"
    version.parser_version = "0.1.0"
    _add_audit(
        db,
        ctx=ctx,
        project_id=project.id,
        section_id=section.id,
        action="document.parse_succeeded",
        object_type="document",
        object_id=document.id,
        after_json={"document_version_id": str(version.id), "chunk_count": len(chunks)},
        reason="导入网页公告后自动解析为文本分块",
        actor_type="worker",
    )


def _create_matrix_task(
    db: Session,
    *,
    ctx: RequestContext,
    project: Project,
    section: BidSection,
    document: Document,
    version: DocumentVersion,
) -> AsyncTask:
    idempotency_key = "matrix-generate:" + hashlib.sha256(
        f"project-import:{section.id}:{document.id}:{version.id}".encode("utf-8")
    ).hexdigest()
    existing = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == ctx.tenant_id,
            AsyncTask.task_type == "matrix_generate",
            AsyncTask.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project.id,
        section_id=section.id,
        task_type="matrix_generate",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "section_id": str(section.id),
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "force": True,
            "trigger": "project_import",
        },
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    _add_audit(
        db,
        ctx=ctx,
        project_id=project.id,
        section_id=section.id,
        action="compliance.matrix_generate_requested",
        object_type="async_task",
        object_id=task.id,
        after_json=task.input_json,
        reason="项目导入后自动生成合规矩阵候选项",
    )
    return task


def confirm_import_draft(
    db: Session,
    *,
    ctx: RequestContext,
    project_payload: dict,
    sections_payload: list[dict],
    source_payload: dict,
    auto_parse: bool,
    auto_generate_matrix: bool,
    async_processing: bool = True,
) -> ImportConfirmResult:
    section_payload = sections_payload[0] if sections_payload else {}
    project = Project(
        tenant_id=ctx.tenant_id,
        name=project_payload["name"].strip(),
        purchaser=_clean_optional_string(project_payload.get("purchaser")),
        agency=_clean_optional_string(project_payload.get("agency")),
        budget_amount=project_payload.get("budget_amount"),
        region_code=_clean_optional_string(project_payload.get("region_code")),
        industry_code=_clean_optional_string(project_payload.get("industry_code")),
        notice_url=_clean_optional_string(project_payload.get("notice_url"))
        or _clean_optional_string(source_payload.get("source_url")),
        status="parsing" if auto_parse else "pending_files",
        bid_deadline_at=project_payload.get("bid_deadline_at"),
        created_by=ctx.user_id,
    )
    db.add(project)
    db.flush()
    db.add(
        ProjectMember(
            tenant_id=ctx.tenant_id,
            project_id=project.id,
            user_id=ctx.user_id,
            role_code="owner",
            status="active",
            created_by=ctx.user_id,
        )
    )
    section = BidSection(
        tenant_id=ctx.tenant_id,
        project_id=project.id,
        code=section_payload.get("code") or "section-001",
        name=(section_payload.get("name") or f"一标段：{project.name}").strip(),
        budget_amount=section_payload.get("budget_amount") or project.budget_amount,
        status="parsing" if auto_parse else "pending_files",
        bid_deadline_at=section_payload.get("bid_deadline_at") or project.bid_deadline_at,
        created_by=ctx.user_id,
    )
    db.add(section)
    db.flush()
    document, version, data = _create_document_from_staged_source(
        db,
        ctx=ctx,
        project=project,
        section=section,
        source=source_payload,
    )
    _add_audit(
        db,
        ctx=ctx,
        project_id=project.id,
        section_id=section.id,
        action="project.import_confirmed",
        object_type="project",
        object_id=project.id,
        after_json={
            "name": project.name,
            "section_name": section.name,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "document_id": str(document.id),
        },
        reason="用户确认导入草稿并创建项目",
    )

    parse_task_id: uuid.UUID | None = None
    matrix_task_id: uuid.UUID | None = None
    is_html = document.file_ext in {"html", "htm"} or (
        document.content_type is not None and "html" in document.content_type
    )

    if auto_parse:
        if is_html:
            _parse_html_document(
                db,
                ctx=ctx,
                project=project,
                section=section,
                document=document,
                version=version,
                data=data,
            )
            db.commit()
        else:
            parse_task = _create_parse_task(
                db,
                ctx=ctx,
                project=project,
                section=section,
                document=document,
                version=version,
            )
            parse_task_id = parse_task.id
            if async_processing and auto_generate_matrix:
                matrix_task = _create_matrix_task(
                    db,
                    ctx=ctx,
                    project=project,
                    section=section,
                    document=document,
                    version=version,
                )
                matrix_task_id = matrix_task.id
            db.commit()
            if async_processing:
                return ImportConfirmResult(
                    project_id=project.id,
                    section_id=section.id,
                    document_id=document.id,
                    parse_task_id=parse_task_id,
                    matrix_task_id=matrix_task_id,
                )
            db.commit()
            execute_document_parse_task(db, parse_task.id)
            db.refresh(version)

        if version.parse_status == "succeeded":
            project.status = "pending_confirm"
            section.status = "pending_confirm"
            if auto_generate_matrix:
                matrix_task = _create_matrix_task(
                    db,
                    ctx=ctx,
                    project=project,
                    section=section,
                    document=document,
                    version=version,
                )
                matrix_task_id = matrix_task.id
                db.commit()
                execute_compliance_matrix_generation_task(db, matrix_task.id)
                db.refresh(project)
                db.refresh(section)
        else:
            project.status = "pending_files"
            section.status = "pending_files"

    db.commit()
    return ImportConfirmResult(
        project_id=project.id,
        section_id=section.id,
        document_id=document.id,
        parse_task_id=parse_task_id,
        matrix_task_id=matrix_task_id,
    )


def execute_import_processing_background(
    *,
    parse_task_id: uuid.UUID | None,
    matrix_task_id: uuid.UUID | None,
) -> None:
    if parse_task_id is None:
        return
    with SessionLocal() as db:
        parse_result = execute_document_parse_task(db, parse_task_id)
        task = db.get(AsyncTask, parse_task_id)
        if task is None or task.project_id is None or task.section_id is None:
            return
        project = db.get(Project, task.project_id)
        section = db.get(BidSection, task.section_id)
        if project is None or section is None:
            return

        if parse_result.get("status") in {"succeeded", "already_succeeded"}:
            project.status = "pending_confirm"
            section.status = "pending_confirm"
            db.commit()
            if matrix_task_id is not None:
                execute_compliance_matrix_generation_task(db, matrix_task_id)
        else:
            project.status = "pending_files"
            section.status = "pending_files"
            if matrix_task_id is not None:
                _fail_matrix_task_due_to_parse_failure(
                    db,
                    matrix_task_id=matrix_task_id,
                    parse_task=task,
                )
            db.commit()


def _fail_matrix_task_due_to_parse_failure(
    db: Session,
    *,
    matrix_task_id: uuid.UUID,
    parse_task: AsyncTask,
) -> None:
    matrix_task = db.get(AsyncTask, matrix_task_id)
    if matrix_task is None or matrix_task.status in {"succeeded", "failed", "canceled"}:
        return

    reason = parse_task.error_message or parse_task.error_code or "未知解析错误"
    now = datetime.now(UTC)
    matrix_task.status = "failed"
    matrix_task.progress = 100
    matrix_task.error_code = "TENDER_PARSE_FAILED"
    matrix_task.error_message = f"招标文件解析失败，矩阵生成未执行：{reason}"
    matrix_task.finished_at = now
    matrix_task.output_json = {
        **(matrix_task.output_json or {}),
        "blocked_by_task_id": str(parse_task.id),
        "blocked_by_error_code": parse_task.error_code,
    }
    db.add(
        AuditLog(
            tenant_id=matrix_task.tenant_id,
            project_id=matrix_task.project_id,
            section_id=matrix_task.section_id,
            actor_user_id=matrix_task.created_by,
            actor_type="worker",
            action="compliance.matrix_generate_failed",
            object_type="async_task",
            object_id=matrix_task.id,
            after_json={
                "error_code": matrix_task.error_code,
                "error_message": matrix_task.error_message,
                "blocked_by_task_id": str(parse_task.id),
            },
            reason="招标文件解析失败，矩阵生成未执行",
            severity="warning",
        )
    )
