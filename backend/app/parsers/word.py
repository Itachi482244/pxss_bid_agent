from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

from docx import Document as load_docx
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


MAX_CHUNK_CHARS = 1800
TOP_NUMBERED_HEADING_RE = re.compile(r"^\s*(?P<number>[1-9]\d?)[.．、]\s*(?P<title>\S.*)$")
SUB_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?P<number>[1-9]\d?(?:[.．]\d{1,2})+)\s*(?P<title>\S.*)$"
)
CHINESE_NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?P<number>[一二三四五六七八九十]+)[、.．]\s*(?P<title>\S.*)$"
)
SENTENCE_ENDINGS = ("。", "；", ";")


@dataclass(frozen=True)
class ParsedWordChunk:
    chunk_index: int
    heading_path: str | None
    content_text: str
    table_json: dict | None = None


def _iter_block_items(document: DocxDocument) -> Iterable[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _heading_level(paragraph: Paragraph) -> int | None:
    style_name = paragraph.style.name if paragraph.style is not None else ""
    if not style_name.startswith("Heading "):
        return None
    suffix = style_name.removeprefix("Heading ").strip()
    return int(suffix) if suffix.isdigit() else None


def _clean_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _numbered_heading_level(text: str) -> int | None:
    chinese_match = CHINESE_NUMBERED_HEADING_RE.match(text)
    if chinese_match is not None:
        title = chinese_match.group("title").strip()
        if len(title) <= 40 and not title.endswith(SENTENCE_ENDINGS):
            return 1
        return None

    match = SUB_NUMBERED_HEADING_RE.match(text) or TOP_NUMBERED_HEADING_RE.match(text)
    if match is None:
        return None
    title = match.group("title").strip()
    if len(title) > 40 or title.endswith(SENTENCE_ENDINGS):
        return None
    number = match.group("number").replace("．", ".")
    return number.count(".") + 1


def _heading_path(headings: list[str]) -> str | None:
    return "/".join(item for item in headings if item) or None


def _update_headings(headings: list[str], level: int, text: str) -> list[str]:
    normalized_level = max(1, level)
    headings = headings[: normalized_level - 1]
    headings.append(text)
    return headings


def _numbered_heading_path_level(headings: list[str], level: int) -> int:
    has_document_title = bool(headings and _numbered_heading_level(headings[0]) is None)
    return level + 1 if has_document_title else level


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


def _table_to_rows(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        rows.append([" ".join(cell.text.split()).strip() for cell in row.cells])
    return rows


def _table_to_text(rows: list[list[str]]) -> str:
    return "\n".join(" | ".join(cell for cell in row) for row in rows if any(row)).strip()


def parse_docx_bytes(data: bytes) -> list[ParsedWordChunk]:
    document = load_docx(BytesIO(data))
    headings: list[str] = []
    chunks: list[ParsedWordChunk] = []

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            text = _clean_text(block.text)
            if not text:
                continue

            level = _heading_level(block)
            if level is not None:
                if not headings and level > 1:
                    level = 1
                headings = _update_headings(headings, level, text)
                chunks.append(
                    ParsedWordChunk(
                        chunk_index=len(chunks) + 1,
                        heading_path=_heading_path(headings),
                        content_text=text,
                    )
                )
                continue

            level = _numbered_heading_level(text)
            if level is not None:
                headings = _update_headings(
                    headings,
                    _numbered_heading_path_level(headings, level),
                    text,
                )
                chunks.append(
                    ParsedWordChunk(
                        chunk_index=len(chunks) + 1,
                        heading_path=_heading_path(headings),
                        content_text=text,
                    )
                )
                continue

            for part in _split_text(text):
                chunks.append(
                    ParsedWordChunk(
                        chunk_index=len(chunks) + 1,
                        heading_path=_heading_path(headings),
                        content_text=part,
                    )
                )
        else:
            rows = _table_to_rows(block)
            text = _table_to_text(rows)
            if not text:
                continue
            chunks.append(
                ParsedWordChunk(
                    chunk_index=len(chunks) + 1,
                    heading_path=_heading_path(headings),
                    content_text=text,
                    table_json={"rows": rows},
                )
            )

    return chunks
