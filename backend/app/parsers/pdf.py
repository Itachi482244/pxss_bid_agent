from __future__ import annotations

import contextlib
from dataclasses import dataclass
from io import StringIO
from typing import Any

import fitz


MAX_CHUNK_CHARS = 1800
PDF_LAYOUT_PARSER_VERSION = "pymupdf-layout-v1"


class PdfTextEmptyError(Exception):
    code = "PDF_TEXT_EMPTY_OCR_REQUIRED"


@dataclass(frozen=True)
class ParsedPdfChunk:
    chunk_index: int
    page_no: int
    heading_path: str | None
    content_text: str
    bbox_json: dict | None = None
    table_json: dict | None = None


@dataclass(frozen=True)
class _PdfBlockCandidate:
    page_no: int
    sort_key: tuple[float, float, int]
    block_type: str
    content_text: str
    bbox: tuple[float, float, float, float]
    page_width: float
    page_height: float
    block_count: int = 1
    table_json: dict[str, Any] | None = None


def _clean_text(text: str) -> str:
    lines = [" ".join(line.split()).strip() for line in text.replace("\xa0", " ").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _split_text(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        split_at = max(text.rfind("\n", start, end), text.rfind("。", start, end))
        if split_at <= start + MAX_CHUNK_CHARS // 2:
            split_at = end
        else:
            split_at += 1
        chunks.append(text[start:split_at].strip())
        start = split_at
    return [chunk for chunk in chunks if chunk]


def _round(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def _normalize_bbox(value: Any) -> tuple[float, float, float, float]:
    if value is None:
        return (0, 0, 0, 0)
    try:
        x0, y0, x1, y1 = value
    except (TypeError, ValueError):
        return (0, 0, 0, 0)
    return (_round(x0), _round(y0), _round(x1), _round(y1))


def _bbox_center_in_any(
    bbox: tuple[float, float, float, float],
    candidates: list[tuple[float, float, float, float]],
) -> bool:
    if not candidates:
        return False
    x0, y0, x1, y1 = bbox
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2
    return any(left <= center_x <= right and top <= center_y <= bottom for left, top, right, bottom in candidates)


def _merge_bbox(bboxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    )


def _table_rows_to_text(rows: list[list[str]]) -> str:
    rendered_rows = [" | ".join(cell.strip() for cell in row if cell.strip()) for row in rows]
    return "\n".join(row for row in rendered_rows if row).strip()


def _text_from_block(block: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in block.get("lines", []):
        text = "".join(str(span.get("text") or "") for span in line.get("spans", []))
        text = " ".join(text.replace("\xa0", " ").split()).strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def _extract_table_candidates(page: fitz.Page, page_no: int) -> list[_PdfBlockCandidate]:
    try:
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            tables = page.find_tables().tables
    except Exception:
        return []

    candidates: list[_PdfBlockCandidate] = []
    for table_index, table in enumerate(tables):
        rows = [
            [_clean_text(str(cell or "")) for cell in row]
            for row in (table.extract() or [])
        ]
        rows = [row for row in rows if any(cell for cell in row)]
        text = _table_rows_to_text(rows)
        if not text:
            continue
        bbox = _normalize_bbox(getattr(table, "bbox", None))
        candidates.append(
            _PdfBlockCandidate(
                page_no=page_no,
                sort_key=(bbox[1], bbox[0], table_index),
                block_type="table",
                content_text=text,
                bbox=bbox,
                page_width=_round(page.rect.width),
                page_height=_round(page.rect.height),
                table_json={
                    "rows": rows,
                    "page_no": page_no,
                    "bbox": list(bbox),
                    "parser_version": PDF_LAYOUT_PARSER_VERSION,
                },
            )
        )
    return candidates


def _extract_text_candidates(
    page: fitz.Page,
    page_no: int,
    table_bboxes: list[tuple[float, float, float, float]],
) -> list[_PdfBlockCandidate]:
    page_dict = page.get_text("dict", sort=True)
    candidates: list[_PdfBlockCandidate] = []
    for block_index, block in enumerate(page_dict.get("blocks", [])):
        if block.get("type") != 0:
            continue
        bbox = _normalize_bbox(block.get("bbox"))
        if _bbox_center_in_any(bbox, table_bboxes):
            continue
        text = _clean_text(_text_from_block(block))
        if not text:
            continue
        candidates.append(
            _PdfBlockCandidate(
                page_no=page_no,
                sort_key=(bbox[1], bbox[0], block_index),
                block_type="text",
                content_text=text,
                bbox=bbox,
                page_width=_round(page.rect.width),
                page_height=_round(page.rect.height),
            )
        )
    return candidates


def _merge_text_candidates(candidates: list[_PdfBlockCandidate]) -> list[_PdfBlockCandidate]:
    merged: list[_PdfBlockCandidate] = []
    buffer: list[_PdfBlockCandidate] = []
    buffer_chars = 0

    def flush() -> None:
        nonlocal buffer, buffer_chars
        if not buffer:
            return
        text = "\n".join(candidate.content_text for candidate in buffer if candidate.content_text).strip()
        if text:
            first = buffer[0]
            merged.append(
                _PdfBlockCandidate(
                    page_no=first.page_no,
                    sort_key=first.sort_key,
                    block_type="text",
                    content_text=text,
                    bbox=_merge_bbox([candidate.bbox for candidate in buffer]),
                    page_width=first.page_width,
                    page_height=first.page_height,
                    block_count=sum(candidate.block_count for candidate in buffer),
                )
            )
        buffer = []
        buffer_chars = 0

    for candidate in candidates:
        if candidate.block_type != "text":
            flush()
            merged.append(candidate)
            continue
        candidate_length = len(candidate.content_text)
        if buffer and buffer_chars + candidate_length + 1 > MAX_CHUNK_CHARS:
            flush()
        buffer.append(candidate)
        buffer_chars += candidate_length + 1

    flush()
    return merged


def _bbox_json(candidate: _PdfBlockCandidate, block_index: int, split_index: int | None) -> dict[str, Any]:
    x0, y0, x1, y1 = candidate.bbox
    payload: dict[str, Any] = {
        "page_no": candidate.page_no,
        "page_width": candidate.page_width,
        "page_height": candidate.page_height,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "block_type": candidate.block_type,
        "block_index": block_index,
        "block_count": candidate.block_count,
        "parser_version": PDF_LAYOUT_PARSER_VERSION,
    }
    if split_index is not None:
        payload["split_index"] = split_index
    return payload


def parse_pdf_bytes(data: bytes) -> list[ParsedPdfChunk]:
    chunks: list[ParsedPdfChunk] = []
    with fitz.open(stream=data, filetype="pdf") as document:
        for page_index, page in enumerate(document, start=1):
            table_candidates = _extract_table_candidates(page, page_index)
            table_bboxes = [candidate.bbox for candidate in table_candidates]
            candidates = [
                *_extract_text_candidates(page, page_index, table_bboxes),
                *table_candidates,
            ]
            candidates.sort(key=lambda candidate: candidate.sort_key)
            candidates = _merge_text_candidates(candidates)

            for candidate_index, candidate in enumerate(candidates):
                parts = _split_text(candidate.content_text)
                for split_index, part in enumerate(parts):
                    if not part:
                        continue
                    is_split = len(parts) > 1
                    bbox_json = _bbox_json(
                        candidate,
                        block_index=candidate_index,
                        split_index=split_index if is_split else None,
                    )
                    table_json = candidate.table_json if candidate.block_type == "table" else None
                    if is_split and table_json is not None:
                        table_json = {**table_json, "split_index": split_index}
                    chunks.append(
                        ParsedPdfChunk(
                            chunk_index=len(chunks) + 1,
                            page_no=page_index,
                            heading_path=f"PDF 第 {page_index} 页",
                            content_text=part,
                            bbox_json=bbox_json,
                            table_json=table_json,
                        )
                    )
    if not chunks:
        raise PdfTextEmptyError("PDF 未提取到可用文本，当前版本暂不支持扫描件/OCR 解析")
    return chunks
