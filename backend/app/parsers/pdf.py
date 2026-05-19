from __future__ import annotations

from dataclasses import dataclass

import fitz


MAX_CHUNK_CHARS = 1800


@dataclass(frozen=True)
class ParsedPdfChunk:
    chunk_index: int
    page_no: int
    heading_path: str | None
    content_text: str
    bbox_json: dict | None = None
    table_json: dict | None = None


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


def parse_pdf_bytes(data: bytes) -> list[ParsedPdfChunk]:
    chunks: list[ParsedPdfChunk] = []
    with fitz.open(stream=data, filetype="pdf") as document:
        for page_index, page in enumerate(document, start=1):
            text = _clean_text(page.get_text("text"))
            if not text:
                continue
            for part in _split_text(text):
                chunks.append(
                    ParsedPdfChunk(
                        chunk_index=len(chunks) + 1,
                        page_no=page_index,
                        heading_path=f"PDF 第 {page_index} 页",
                        content_text=part,
                        bbox_json={"page": page_index},
                    )
                )
    return chunks
