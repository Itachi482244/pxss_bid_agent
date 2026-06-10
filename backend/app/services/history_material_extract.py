from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.observability import observed_task
from app.models import AsyncTask, AuditLog, EnterpriseMaterial, SourcePageImage
from app.parsers.pdf import PdfTextEmptyError, parse_pdf_bytes
from app.parsers.word import parse_docx_bytes
from app.schemas.enterprise import EnterpriseMaterialRead
from app.services.document_utils import file_extension, safe_filename
from app.services.llm_gateway import LLMGatewayError, chat_completion
from app.services.material_identity import material_identity_key_from_values
from app.services.ocr import OcrError, get_ocr_client
from app.services.source_page_images import get_or_create_pdf_page_image_asset, page_image_payload
from app.services.storage import get_object_bytes

HISTORY_MATERIAL_EXTRACT_PROMPT_VERSION = "history-material-extract-v1"
MAX_LLM_INPUT_CHARS = 18000
PDF_OCR_FORK_JOIN_MAX_WORKERS = 4
MAX_MATERIAL_NAME_CHARS = 80
SUPPORTED_HISTORY_EXTENSIONS = {
    "pdf",
    "docx",
    "jpg",
    "jpeg",
    "png",
    "bmp",
    "tif",
    "tiff",
}
ALLOWED_MATERIAL_TYPES = {
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
MATERIAL_TYPE_LABELS = {
    "license": "营业执照",
    "qualification": "企业资质证书",
    "personnel": "人员资格证书",
    "performance": "历史项目业绩",
    "business_template": "商务模板",
    "commitment": "承诺材料",
    "product_catalog": "产品资料",
    "test_report": "检测报告",
    "product_image": "产品图片",
    "technical_proposal": "历史技术方案",
    "other": "其他资料",
}
SOURCE_IMAGE_MATERIAL_TYPES = {"license", "qualification", "personnel", "test_report", "product_image"}
SOURCE_IMAGE_KEYWORDS = (
    "营业执照",
    "统一社会信用代码",
    "资质证书",
    "资格证书",
    "许可证",
    "安全生产许可证",
    "注册证书",
    "职称证书",
    "检测报告",
    "检验报告",
    "认证证书",
    "授权委托书",
    "法定代表人授权",
)
PERFORMANCE_SIGNAL_KEYWORDS = ("业绩", "合同", "中标", "竣工", "验收", "项目名称", "工程名称", "合同金额", "中标金额")


class HistoryMaterialExtractError(Exception):
    def __init__(self, message: str, *, code: str = "HISTORY_MATERIAL_EXTRACT_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceTextBlock:
    block_index: int
    content_text: str
    parser: str
    page_no: int | None = None
    heading_path: str | None = None
    table_json: dict[str, Any] | None = None
    ocr_confidence: float | None = None


@dataclass(frozen=True)
class ExtractedMaterialDraft:
    material_type: str
    name: str
    evidence_text: str
    confidence: float
    source_block_indexes: list[int]
    issuing_authority: str | None = None
    certificate_no: str | None = None
    holder_name: str | None = None
    project_name: str | None = None
    amount: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    structured_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HistoryMaterialExtraction:
    source_file_name: str
    source_content_type: str | None
    source_file_size: int
    source_sha256: str
    parser_summary: dict[str, Any]
    text_blocks: list[SourceTextBlock]
    drafts: list[ExtractedMaterialDraft]
    extraction_method: str
    warnings: list[str]


def _clean_text(text: str) -> str:
    lines = [" ".join(line.replace("\xa0", " ").split()).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _clip(text: str, limit: int = 900) -> str:
    text = _clean_text(text)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _compact_single_line(text: str, *, limit: int = MAX_MATERIAL_NAME_CHARS) -> str:
    value = re.sub(r"\s+", " ", _clean_text(text)).strip(" ，,。；;：:")
    return value if len(value) <= limit else f"{value[:limit].rstrip()}..."


def _first_match(pattern: str, text: str, *, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return _clean_text(match.group(1))


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    text = text.replace("/", "-").replace(".", "-")
    match = re.search(r"(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})", text)
    if not match:
        return None
    year, month, day = (int(item) for item in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _looks_like_evidence_blob(value: str) -> bool:
    text = _clean_text(value)
    if len(text) > MAX_MATERIAL_NAME_CHARS:
        return True
    if "\n" in value:
        return True
    punctuation_count = sum(text.count(item) for item in ("，", "。", "；", "：", "、", "（", "）", "(", ")"))
    return punctuation_count >= 4


def _infer_project_name(evidence_text: str) -> str | None:
    return (
        _first_match(r"(?:项目名称|工程名称)[：:\s]*([^\n，。；;]{4,120})", evidence_text)
        or _first_match(r"((?:[\u4e00-\u9fffA-Za-z0-9（）()\-]{4,80})(?:项目|工程))", evidence_text)
    )


def _should_drop_draft(
    *,
    material_type: str,
    evidence_text: str,
) -> bool:
    if material_type != "performance":
        return False
    return not any(keyword in evidence_text for keyword in PERFORMANCE_SIGNAL_KEYWORDS)


def _sanitize_material_name(
    raw_name: str,
    *,
    material_type: str,
    evidence_text: str,
    issuing_authority: str | None,
    certificate_no: str | None,
    holder_name: str | None,
    project_name: str | None,
    structured_fields: dict[str, Any],
) -> str:
    name = _clean_text(raw_name)
    if name and not _looks_like_evidence_blob(name):
        return _compact_single_line(name)

    if material_type == "performance" and project_name:
        return _compact_single_line(f"{project_name}业绩")
    if material_type == "personnel" and holder_name:
        return _compact_single_line(f"{holder_name}资格证书")
    if material_type in {"license", "qualification", "test_report"}:
        category = str(
            structured_fields.get("qualification_category")
            or structured_fields.get("certificate_name")
            or structured_fields.get("report_name")
            or ""
        ).strip()
        grade = str(structured_fields.get("grade") or "").strip()
        if category:
            return _compact_single_line(" ".join(part for part in (category, grade) if part))
        if certificate_no:
            return _compact_single_line(f"{MATERIAL_TYPE_LABELS.get(material_type, '证书')} {certificate_no}")
    if issuing_authority and material_type in {"license", "qualification", "test_report"}:
        return _compact_single_line(f"{issuing_authority}{MATERIAL_TYPE_LABELS.get(material_type, '材料')}")
    return MATERIAL_TYPE_LABELS.get(material_type, "其他资料")


def _source_locations(blocks: list[SourceTextBlock], block_indexes: list[int]) -> list[dict[str, Any]]:
    by_index = {block.block_index: block for block in blocks}
    locations: list[dict[str, Any]] = []
    for block_index in block_indexes:
        block = by_index.get(block_index)
        if block is None:
            continue
        payload: dict[str, Any] = {
            "block_index": block.block_index,
            "page_no": block.page_no,
            "heading_path": block.heading_path,
            "parser": block.parser,
            "snippet": _clip(block.content_text, 320),
        }
        if block.ocr_confidence is not None:
            payload["ocr_confidence"] = block.ocr_confidence
        locations.append(payload)
    return locations


def _source_blocks(blocks: list[SourceTextBlock], block_indexes: list[int]) -> list[SourceTextBlock]:
    by_index = {block.block_index: block for block in blocks}
    source_blocks: list[SourceTextBlock] = []
    for block_index in block_indexes:
        block = by_index.get(block_index)
        if block is not None:
            source_blocks.append(block)
    return source_blocks


def _draft_needs_source_image(draft: ExtractedMaterialDraft, blocks: list[SourceTextBlock]) -> bool:
    if any(block.parser in {"pdf_ocr", "image_ocr"} for block in blocks):
        return True
    if draft.material_type in SOURCE_IMAGE_MATERIAL_TYPES:
        return True
    text = "\n".join([draft.name, draft.evidence_text, *[block.content_text for block in blocks]])
    return any(keyword in text for keyword in SOURCE_IMAGE_KEYWORDS)


def _persist_pdf_page_assets_for_blocks(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    blocks: list[SourceTextBlock],
    drafts: list[ExtractedMaterialDraft],
    source_kind: str,
    source_id: uuid.UUID | None,
    bucket: str,
    object_key: str,
    source_data: bytes | None,
    source_file_name: str,
    source_sha256: str,
) -> dict[int, SourcePageImage]:
    if source_data is None or file_extension(source_file_name) != "pdf":
        return {}
    page_numbers: set[int] = set()
    for draft in drafts:
        source_blocks = _source_blocks(blocks, draft.source_block_indexes)
        if not _draft_needs_source_image(draft, source_blocks):
            continue
        page_numbers.update(
            block.page_no
            for block in source_blocks
            if block.page_no is not None and block.parser == "pdf_ocr"
        )
    assets: dict[int, SourcePageImage] = {}
    for page_no in sorted(page_numbers):
        assets[page_no] = get_or_create_pdf_page_image_asset(
            db,
            tenant_id=tenant_id,
            source_kind=source_kind,
            source_id=source_id,
            source_bucket=bucket,
            source_object_key=object_key,
            source_sha256=source_sha256,
            source_file_name=source_file_name,
            pdf_data=source_data,
            page_no=page_no,
            image_bucket=bucket,
        )
    return assets


def _source_images_for_draft(
    draft: ExtractedMaterialDraft,
    *,
    blocks: list[SourceTextBlock],
    page_assets: dict[int, SourcePageImage],
    bucket: str,
    object_key: str,
    source_data: bytes | None,
    source_file_name: str,
    source_content_type: str | None,
    source_sha256: str,
) -> list[dict[str, Any]]:
    source_blocks = _source_blocks(blocks, draft.source_block_indexes)
    if not _draft_needs_source_image(draft, source_blocks):
        return []

    ext = file_extension(source_file_name)
    images: list[dict[str, Any]] = []
    if ext == "pdf":
        seen_pages: set[int] = set()
        for block in source_blocks:
            if block.page_no is None or block.page_no in seen_pages:
                continue
            seen_pages.add(block.page_no)
            asset = page_assets.get(block.page_no)
            if asset is not None:
                images.append(page_image_payload(asset, block_index=block.block_index, parser=block.parser))
    elif ext in {"jpg", "jpeg", "png", "bmp", "tif", "tiff"}:
        images.append(
            {
                "bucket": bucket,
                "object_key": object_key,
                "content_type": source_content_type,
                "file_size": len(source_data) if source_data is not None else None,
                "sha256": source_sha256,
                "page_no": None,
                "block_index": source_blocks[0].block_index if source_blocks else 1,
                "parser": source_blocks[0].parser if source_blocks else "image_ocr",
                "source": "original_image",
            }
        )
    return images


def _make_structured_fields(
    draft: ExtractedMaterialDraft,
    *,
    blocks: list[SourceTextBlock],
    source_file_name: str,
    source_sha256: str,
    extraction_method: str,
    source_images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fields = dict(draft.structured_fields or {})
    fields.update(
        {
            "source": "history_file_extract",
            "source_file_name": source_file_name,
            "source_sha256": source_sha256,
            "source_locations": _source_locations(blocks, draft.source_block_indexes),
            "extraction_method": extraction_method,
            "extraction_confidence": round(float(draft.confidence), 4),
            "needs_human_confirm": True,
            "trust_boundary": "pending_confirm_until_human_review",
        }
    )
    if source_images:
        fields["source_images"] = source_images
        fields["primary_source_image"] = source_images[0]
    return fields


def _dedupe_drafts(drafts: list[ExtractedMaterialDraft]) -> list[ExtractedMaterialDraft]:
    deduped: list[ExtractedMaterialDraft] = []
    seen: set[str] = set()
    for draft in drafts:
        key = material_identity_key_from_values(
            material_type=draft.material_type,
            name=draft.name,
            issuing_authority=draft.issuing_authority,
            certificate_no=draft.certificate_no,
            holder_name=draft.holder_name,
            project_name=draft.project_name,
            amount=draft.amount,
            structured_fields=draft.structured_fields,
            evidence_text=draft.evidence_text,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(draft)
    return deduped


def _ocr_image_block(
    *,
    image_bytes: bytes,
    block_index: int,
    page_no: int | None,
    parser: str,
) -> SourceTextBlock:
    try:
        result = get_ocr_client().recognize_image(image_bytes)
    except OcrError as exc:
        raise HistoryMaterialExtractError(str(exc), code=exc.code) from exc
    table_text = "\n".join(table.to_text() for table in result.tables if table.to_text()).strip()
    text = "\n".join(part for part in (result.text, table_text) if part).strip()
    if not text:
        raise HistoryMaterialExtractError("OCR 未识别到可用文字", code="OCR_TEXT_EMPTY")
    return SourceTextBlock(
        block_index=block_index,
        page_no=page_no,
        parser=parser,
        heading_path=f"PDF 第 {page_no} 页" if page_no is not None else "图片 OCR",
        content_text=text,
        table_json={"tables": [table.rows for table in result.tables]} if result.tables else None,
        ocr_confidence=result.confidence,
    )


OcrProgressCallback = Callable[[int, int], None]


def _parse_pdf_ocr_blocks(
    data: bytes,
    *,
    progress_callback: OcrProgressCallback | None = None,
) -> list[SourceTextBlock]:
    blocks_by_page: dict[int, SourceTextBlock] = {}
    with fitz.open(stream=data, filetype="pdf") as document:
        page_count = len(document)
        if page_count == 0:
            return []
        max_workers = max(1, min(PDF_OCR_FORK_JOIN_MAX_WORKERS, page_count))
        next_page_no = 1
        completed = 0

        def submit_page(executor: ThreadPoolExecutor, page_no: int):
            page = document.load_page(page_no - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_bytes = pixmap.tobytes("png")
            return executor.submit(
                _ocr_image_block,
                image_bytes=image_bytes,
                block_index=page_no,
                page_no=page_no,
                parser="pdf_ocr",
            )

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="history-pdf-ocr") as executor:
            pending = {}
            while next_page_no <= page_count and len(pending) < max_workers:
                future = submit_page(executor, next_page_no)
                pending[future] = next_page_no
                next_page_no += 1

            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    page_no = pending.pop(future)
                    blocks_by_page[page_no] = future.result()
                    completed += 1
                    if progress_callback is not None:
                        progress_callback(completed, page_count)
                    if next_page_no <= page_count:
                        next_future = submit_page(executor, next_page_no)
                        pending[next_future] = next_page_no
                        next_page_no += 1

    return [blocks_by_page[page_no] for page_no in sorted(blocks_by_page)]


def parse_history_file_to_blocks(
    *,
    data: bytes,
    filename: str,
    content_type: str | None,
    pdf_mode: str = "auto",
    ocr_progress_callback: OcrProgressCallback | None = None,
) -> tuple[list[SourceTextBlock], dict[str, Any], list[str]]:
    safe_name = safe_filename(filename)
    ext = file_extension(safe_name)
    warnings: list[str] = []
    if ext not in SUPPORTED_HISTORY_EXTENSIONS:
        raise HistoryMaterialExtractError(f"暂不支持的历史资料格式：{ext or 'unknown'}", code="UNSUPPORTED_HISTORY_FILE_TYPE")

    if ext == "docx":
        chunks = parse_docx_bytes(data)
        blocks = [
            SourceTextBlock(
                block_index=index,
                parser="word",
                heading_path=chunk.heading_path,
                content_text=chunk.content_text,
                table_json=chunk.table_json,
            )
            for index, chunk in enumerate(chunks, start=1)
            if chunk.content_text.strip()
        ]
        return blocks, {"parser": "word", "mode": "docx", "block_count": len(blocks)}, warnings

    if ext == "pdf":
        if pdf_mode not in {"auto", "ocr"}:
            raise HistoryMaterialExtractError("pdf_mode 仅支持 auto 或 ocr", code="INVALID_PDF_MODE")
        if pdf_mode == "ocr":
            blocks = _parse_pdf_ocr_blocks(data, progress_callback=ocr_progress_callback)
            return blocks, {
                "parser": "pdf_ocr",
                "mode": "ocr",
                "block_count": len(blocks),
                "ocr_fork_join_max_workers": PDF_OCR_FORK_JOIN_MAX_WORKERS,
            }, warnings
        try:
            chunks = parse_pdf_bytes(data)
            blocks = [
                SourceTextBlock(
                    block_index=index,
                    parser="pdf_text",
                    page_no=chunk.page_no,
                    heading_path=chunk.heading_path,
                    content_text=chunk.content_text,
                    table_json=chunk.table_json,
                )
                for index, chunk in enumerate(chunks, start=1)
                if chunk.content_text.strip()
            ]
            return blocks, {"parser": "pdf_text", "mode": "auto", "block_count": len(blocks)}, warnings
        except PdfTextEmptyError:
            warnings.append("PDF 未提取到文本，已自动切换为逐页 OCR。")
            blocks = _parse_pdf_ocr_blocks(data, progress_callback=ocr_progress_callback)
            return blocks, {
                "parser": "pdf_ocr",
                "mode": "auto_fallback_ocr",
                "block_count": len(blocks),
                "ocr_fork_join_max_workers": PDF_OCR_FORK_JOIN_MAX_WORKERS,
            }, warnings

    if content_type and content_type.startswith("image/") or ext in {"jpg", "jpeg", "png", "bmp", "tif", "tiff"}:
        block = _ocr_image_block(image_bytes=data, block_index=1, page_no=None, parser="image_ocr")
        return [block], {"parser": "image_ocr", "mode": "image", "block_count": 1}, warnings

    raise HistoryMaterialExtractError("暂不支持该文件类型", code="UNSUPPORTED_HISTORY_FILE_TYPE")


def _blocks_for_llm(blocks: list[SourceTextBlock]) -> str:
    parts: list[str] = []
    total = 0
    for block in blocks:
        header = f"[block={block.block_index}"
        if block.page_no is not None:
            header += f", page={block.page_no}"
        if block.heading_path:
            header += f", heading={block.heading_path}"
        header += f", parser={block.parser}]"
        text = f"{header}\n{_clip(block.content_text, 1800)}"
        if total + len(text) > MAX_LLM_INPUT_CHARS:
            break
        parts.append(text)
        total += len(text)
    return "\n\n".join(parts)


def _json_from_llm_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    return value if isinstance(value, dict) else {"materials": value}


def _draft_from_mapping(raw: dict[str, Any]) -> ExtractedMaterialDraft | None:
    material_type = str(raw.get("material_type") or "other").strip()
    if material_type not in ALLOWED_MATERIAL_TYPES:
        material_type = "other"
    evidence_text = _clean_text(str(raw.get("evidence_text") or raw.get("source_snippet") or ""))
    if not evidence_text:
        return None
    raw_name = _clean_text(str(raw.get("name") or raw.get("title") or ""))
    block_indexes = raw.get("source_block_indexes") or raw.get("source_blocks") or []
    if not isinstance(block_indexes, list):
        block_indexes = [block_indexes]
    normalized_blocks: list[int] = []
    for value in block_indexes:
        try:
            normalized_blocks.append(int(value))
        except (TypeError, ValueError):
            continue
    confidence = raw.get("confidence", 0.65)
    try:
        confidence_float = min(1.0, max(0.0, float(confidence)))
    except (TypeError, ValueError):
        confidence_float = 0.65
    structured = raw.get("structured_fields")
    structured_fields = structured if isinstance(structured, dict) else {}
    issuing_authority = _clean_text(str(raw.get("issuing_authority") or "")) or None
    certificate_no = _clean_text(str(raw.get("certificate_no") or ""))[:128] or None
    holder_name = _clean_text(str(raw.get("holder_name") or ""))[:200] or None
    project_name = _clean_text(str(raw.get("project_name") or ""))[:300] or None
    if material_type == "performance" and not project_name:
        project_name = _infer_project_name(evidence_text)
    if _should_drop_draft(
        material_type=material_type,
        evidence_text=evidence_text,
    ):
        return None
    name = _sanitize_material_name(
        raw_name,
        material_type=material_type,
        evidence_text=evidence_text,
        issuing_authority=issuing_authority,
        certificate_no=certificate_no,
        holder_name=holder_name,
        project_name=project_name,
        structured_fields=structured_fields,
    )
    return ExtractedMaterialDraft(
        material_type=material_type,
        name=name[:300],
        issuing_authority=issuing_authority,
        certificate_no=certificate_no,
        holder_name=holder_name,
        project_name=project_name,
        amount=_clean_text(str(raw.get("amount") or ""))[:100] or None,
        valid_from=_parse_date(raw.get("valid_from")),
        valid_until=_parse_date(raw.get("valid_until")),
        evidence_text=evidence_text,
        confidence=confidence_float,
        source_block_indexes=normalized_blocks or [1],
        structured_fields=structured_fields,
    )


def _extract_with_llm(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    blocks: list[SourceTextBlock],
    source_file_name: str,
) -> list[ExtractedMaterialDraft]:
    result = chat_completion(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        actor_type="user",
        task_type="history_material_extract",
        prompt_version=HISTORY_MATERIAL_EXTRACT_PROMPT_VERSION,
        complexity="complex",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "你是投标企业资料抽取助手。请只从用户给出的历史投标文件文本中抽取企业资料，"
                    "不得编造。每条资料必须是 pending_confirm 草稿，需要人工复核。"
                    "资料名称必须是简短标题，不得直接复制大段原文。"
                    "投标邀请、响应文件格式、供应商须知、签字盖章说明等不是企业资料，不要抽取。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"文件名：{source_file_name}\n"
                    "请输出 JSON：{\"materials\":[...]}。materials 每项字段：material_type、name、"
                    "issuing_authority、certificate_no、holder_name、project_name、amount、valid_from、"
                    "valid_until、evidence_text、confidence、source_block_indexes、structured_fields。\n"
                    "material_type 只能为 license/qualification/personnel/performance/business_template/"
                    "commitment/product_catalog/test_report/product_image/technical_proposal/other。\n"
                    "name 必须是 80 字以内的资料标题，例如“营业执照”“建筑工程施工总承包一级资质证书”"
                    "或“某项目业绩”，不能是整段响应文件原文。"
                    "performance 必须有明确项目/合同/中标/验收信息；没有项目事实的投标格式文本不要抽取。"
                    "source_block_indexes 必须引用下面 block 编号；evidence_text 必须摘自原文。\n\n"
                    f"{_blocks_for_llm(blocks)}"
                ),
            },
        ],
        evidence_refs={"source_file_name": source_file_name, "block_count": len(blocks)},
    )
    payload = _json_from_llm_content(result.content)
    raw_materials = payload.get("materials") or []
    if not isinstance(raw_materials, list):
        return []
    drafts = [_draft_from_mapping(item) for item in raw_materials if isinstance(item, dict)]
    return [draft for draft in drafts if draft is not None]


def _fallback_license(block: SourceTextBlock) -> ExtractedMaterialDraft | None:
    text = block.content_text
    if "营业执照" not in text and "统一社会信用代码" not in text:
        return None
    code = _first_match(r"统一社会信用代码[：:\s]*([0-9A-Z]{12,30})", text, flags=re.I)
    company = _first_match(r"(?:^|\n)(?:企业名称|名称)[：:\s]*([^\n]{4,80})", text)
    return ExtractedMaterialDraft(
        material_type="license",
        name=company or "营业执照",
        certificate_no=code,
        evidence_text=_clip(text),
        confidence=0.74 if code else 0.62,
        source_block_indexes=[block.block_index],
        structured_fields={"fallback_rule": "license.business_license"},
    )


def _fallback_qualification(block: SourceTextBlock) -> ExtractedMaterialDraft | None:
    text = block.content_text
    if not any(keyword in text for keyword in ("资质", "施工总承包", "专业承包", "安全生产许可证")):
        return None
    category = (
        _first_match(r"资质(?:名称|类别)?[：:\s]*([^\n]{3,80})", text)
        or _first_match(r"((?:[\u4e00-\u9fff]{2,20})(?:施工总承包|专业承包)[^\n]{0,30})", text)
    )
    grade = _first_match(r"(?:资质等级|等级)[：:\s]*([一二三级甲乙丙特级壹贰叁]{1,4})", text)
    cert_no = _first_match(r"(?:证书编号|编号)[：:\s]*([A-Z0-9\-]{6,40})", text, flags=re.I)
    name_parts = [part for part in (category, grade) if part]
    name = " ".join(name_parts) if name_parts else "企业资质证书"
    return ExtractedMaterialDraft(
        material_type="qualification",
        name=name[:300],
        certificate_no=cert_no,
        evidence_text=_clip(text),
        confidence=0.7 if category else 0.58,
        source_block_indexes=[block.block_index],
        structured_fields={
            "fallback_rule": "qualification.keyword",
            "qualification_category": category,
            "grade": grade,
        },
    )


def _fallback_personnel(block: SourceTextBlock) -> ExtractedMaterialDraft | None:
    text = block.content_text
    if not any(keyword in text for keyword in ("项目经理", "建造师", "注册证书", "职称证书")):
        return None
    holder = _first_match(r"(?:姓名|项目经理)[：:\s]*([\u4e00-\u9fff·]{2,12})", text)
    cert_no = _first_match(r"(?:注册编号|证书编号|编号)[：:\s]*([A-Z0-9\-]{6,40})", text, flags=re.I)
    return ExtractedMaterialDraft(
        material_type="personnel",
        name=f"{holder or '人员'}资格证书",
        holder_name=holder,
        certificate_no=cert_no,
        evidence_text=_clip(text),
        confidence=0.62,
        source_block_indexes=[block.block_index],
        structured_fields={"fallback_rule": "personnel.keyword"},
    )


def _fallback_performance(block: SourceTextBlock) -> ExtractedMaterialDraft | None:
    text = block.content_text
    if not any(keyword in text for keyword in ("类似业绩", "项目业绩", "合同金额", "竣工验收", "项目名称")):
        return None
    project_name = _first_match(r"(?:项目名称|工程名称)[：:\s]*([^\n]{4,120})", text)
    amount = _first_match(r"(?:合同金额|中标金额|金额)[：:\s]*([0-9,.]+(?:万)?元?)", text)
    return ExtractedMaterialDraft(
        material_type="performance",
        name=project_name or "历史项目业绩",
        project_name=project_name,
        amount=amount,
        evidence_text=_clip(text),
        confidence=0.6,
        source_block_indexes=[block.block_index],
        structured_fields={"fallback_rule": "performance.keyword"},
    )


def _fallback_commitment(block: SourceTextBlock) -> ExtractedMaterialDraft | None:
    text = block.content_text
    if "承诺" not in text:
        return None
    return ExtractedMaterialDraft(
        material_type="commitment",
        name="历史承诺材料",
        evidence_text=_clip(text),
        confidence=0.55,
        source_block_indexes=[block.block_index],
        structured_fields={"fallback_rule": "commitment.keyword"},
    )


def _extract_with_local_rules(blocks: list[SourceTextBlock]) -> list[ExtractedMaterialDraft]:
    drafts: list[ExtractedMaterialDraft] = []
    rules = (
        _fallback_license,
        _fallback_qualification,
        _fallback_personnel,
        _fallback_performance,
        _fallback_commitment,
    )
    for block in blocks:
        for rule in rules:
            draft = rule(block)
            if draft is not None:
                drafts.append(draft)
    return drafts


def extract_history_material_drafts(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    data: bytes,
    filename: str,
    content_type: str | None,
    pdf_mode: str = "auto",
    ocr_progress_callback: OcrProgressCallback | None = None,
) -> HistoryMaterialExtraction:
    source_file_name = safe_filename(filename)
    source_sha256 = hashlib.sha256(data).hexdigest()
    blocks, parser_summary, warnings = parse_history_file_to_blocks(
        data=data,
        filename=source_file_name,
        content_type=content_type,
        pdf_mode=pdf_mode,
        ocr_progress_callback=ocr_progress_callback,
    )
    if not blocks:
        raise HistoryMaterialExtractError("历史文件未解析到可用文本", code="HISTORY_TEXT_EMPTY")

    extraction_method = "llm"
    try:
        drafts = _extract_with_llm(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            blocks=blocks,
            source_file_name=source_file_name,
        )
    except (LLMGatewayError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        warnings.append(f"LLM 抽取不可用，已使用本地规则兜底：{getattr(exc, 'code', exc.__class__.__name__)}")
        extraction_method = "local_rules"
        drafts = _extract_with_local_rules(blocks)

    if not drafts:
        extraction_method = "local_rules" if extraction_method != "llm" else "llm_empty"
        drafts = _extract_with_local_rules(blocks)
    drafts = _dedupe_drafts(drafts)
    if not drafts:
        warnings.append("未从历史文件中识别到可入库的企业资料草稿，请人工新增或换一份历史资料。")

    return HistoryMaterialExtraction(
        source_file_name=source_file_name,
        source_content_type=content_type,
        source_file_size=len(data),
        source_sha256=source_sha256,
        parser_summary=parser_summary,
        text_blocks=blocks,
        drafts=drafts,
        extraction_method=extraction_method,
        warnings=warnings,
    )


def create_pending_materials_from_extraction(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    extraction: HistoryMaterialExtraction,
    bucket: str,
    object_key: str,
    source_data: bytes | None = None,
    source_kind: str = "history_upload",
    source_id: uuid.UUID | None = None,
    data_level: str = "internal",
) -> list[EnterpriseMaterial]:
    materials: list[EnterpriseMaterial] = []
    now = datetime.now(UTC)
    page_assets = _persist_pdf_page_assets_for_blocks(
        db,
        tenant_id=tenant_id,
        blocks=extraction.text_blocks,
        drafts=extraction.drafts,
        source_kind=source_kind,
        source_id=source_id,
        bucket=bucket,
        object_key=object_key,
        source_data=source_data,
        source_file_name=extraction.source_file_name,
        source_sha256=extraction.source_sha256,
    )
    for draft in extraction.drafts:
        source_images = _source_images_for_draft(
            draft,
            blocks=extraction.text_blocks,
            page_assets=page_assets,
            bucket=bucket,
            object_key=object_key,
            source_data=source_data,
            source_file_name=extraction.source_file_name,
            source_content_type=extraction.source_content_type,
            source_sha256=extraction.source_sha256,
        )
        material = EnterpriseMaterial(
            tenant_id=tenant_id,
            material_type=draft.material_type,
            name=draft.name,
            issuing_authority=draft.issuing_authority,
            certificate_no=draft.certificate_no,
            holder_name=draft.holder_name,
            project_name=draft.project_name,
            amount=draft.amount,
            valid_from=draft.valid_from,
            valid_until=draft.valid_until,
            data_level=data_level,
            verification_status="pending_confirm",
            structured_fields=_make_structured_fields(
                draft,
                blocks=extraction.text_blocks,
                source_file_name=extraction.source_file_name,
                source_sha256=extraction.source_sha256,
                extraction_method=extraction.extraction_method,
                source_images=source_images,
            ),
            evidence_text=draft.evidence_text,
            file_name=extraction.source_file_name,
            content_type=extraction.source_content_type,
            file_size=extraction.source_file_size,
            sha256=extraction.source_sha256,
            bucket=bucket,
            object_key=object_key,
            created_by=actor_user_id,
            updated_by=actor_user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(material)
        materials.append(material)
    return materials


def _coerce_task_id(task_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    try:
        return uuid.UUID(str(task_id))
    except ValueError as exc:
        raise HistoryMaterialExtractError("任务ID格式错误", code="INVALID_TASK_ID") from exc


def _history_extraction_output_json(
    extraction: HistoryMaterialExtraction,
    materials: list[EnterpriseMaterial],
) -> dict[str, Any]:
    return {
        "materials": [
            EnterpriseMaterialRead.model_validate(material).model_dump(mode="json")
            for material in materials
        ],
        "source_file_name": extraction.source_file_name,
        "source_file_size": extraction.source_file_size,
        "source_sha256": extraction.source_sha256,
        "parser_summary": extraction.parser_summary,
        "extraction_method": extraction.extraction_method,
        "warning_messages": extraction.warnings,
        "draft_count": len(materials),
        "text_block_count": len(extraction.text_blocks),
        "material_ids": [str(material.id) for material in materials],
    }


def _load_history_extract_task(db: Session, task_id: uuid.UUID | str) -> AsyncTask:
    task_uuid = _coerce_task_id(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "history_material_extract":
        raise HistoryMaterialExtractError("历史资料抽取任务不存在", code="TASK_NOT_FOUND")
    return task


@observed_task("history_material_extract")
def execute_history_material_extract_task(db: Session, task_id: uuid.UUID | str) -> dict[str, Any]:
    task = _load_history_extract_task(db, task_id)
    if task.status == "succeeded":
        return {"status": "already_succeeded", **(task.output_json or {})}

    input_json = task.input_json or {}
    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = max(task.progress, 5)
    task.output_json = {
        "stage": "reading_file",
        "source_file_name": input_json.get("source_file_name"),
        "source_file_size": input_json.get("source_file_size"),
    }
    db.commit()

    try:
        bucket = str(input_json.get("bucket") or "")
        object_key = str(input_json.get("object_key") or "")
        if not bucket or not object_key:
            raise HistoryMaterialExtractError("历史文件存储信息缺失", code="HISTORY_FILE_STORAGE_MISSING")

        data = get_object_bytes(bucket=bucket, object_key=object_key)
        task.progress = 10
        task.output_json = {
            **(task.output_json or {}),
            "stage": "extracting_text",
        }
        db.commit()

        def update_ocr_progress(done: int, total: int) -> None:
            task.progress = min(85, 10 + int((done / max(total, 1)) * 70))
            task.output_json = {
                **(task.output_json or {}),
                "stage": "ocr",
                "ocr_completed_pages": done,
                "ocr_total_pages": total,
            }
            db.commit()

        extraction = extract_history_material_drafts(
            db,
            tenant_id=task.tenant_id,
            actor_user_id=task.created_by,
            data=data,
            filename=str(input_json.get("source_file_name") or "history-material.bin"),
            content_type=input_json.get("content_type"),
            pdf_mode=str(input_json.get("pdf_mode") or "auto"),
            ocr_progress_callback=update_ocr_progress,
        )

        task.progress = max(task.progress, 88)
        task.output_json = {
            **(task.output_json or {}),
            "stage": "writing_materials",
            "parser_summary": extraction.parser_summary,
            "text_block_count": len(extraction.text_blocks),
        }
        db.commit()

        materials = create_pending_materials_from_extraction(
            db,
            tenant_id=task.tenant_id,
            actor_user_id=task.created_by,
            extraction=extraction,
            bucket=bucket,
            object_key=object_key,
            source_data=data,
            source_kind="history_upload",
            source_id=task.id,
            data_level=str(input_json.get("data_level") or "internal"),
        )
        db.flush()
        task.status = "succeeded"
        task.progress = 100
        task.finished_at = datetime.now(UTC)
        task.output_json = _history_extraction_output_json(extraction, materials)
        db.add(
            AuditLog(
                tenant_id=task.tenant_id,
                project_id=None,
                section_id=None,
                actor_user_id=task.created_by,
                actor_type="worker",
                action="enterprise.materials_extracted_from_history",
                object_type="async_task",
                object_id=task.id,
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
                reason="异步抽取历史投标文件中的企业资料草稿",
                severity="info",
            )
        )
        db.commit()
        return {"status": "succeeded", **(task.output_json or {})}
    except HistoryMaterialExtractError as exc:
        task.status = "failed"
        task.progress = max(task.progress, 1)
        task.error_code = exc.code
        task.error_message = str(exc)[:1000]
        task.finished_at = datetime.now(UTC)
        db.commit()
        return {"status": "failed", "error_code": exc.code, "error_message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - worker task must persist failure state
        task.status = "failed"
        task.progress = max(task.progress, 1)
        task.error_code = "HISTORY_MATERIAL_EXTRACT_FAILED"
        task.error_message = str(exc)[:1000]
        task.finished_at = datetime.now(UTC)
        db.commit()
        return {
            "status": "failed",
            "error_code": task.error_code,
            "error_message": task.error_message,
        }
