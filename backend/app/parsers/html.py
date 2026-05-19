from __future__ import annotations

import html
import re
from dataclasses import dataclass


MAX_CHUNK_CHARS = 1800


@dataclass(frozen=True)
class ParsedHtmlChunk:
    chunk_index: int
    heading_path: str | None
    content_text: str
    table_json: dict | None = None


def html_bytes_to_text(data: bytes, content_type: str | None = None) -> str:
    encoding = "utf-8"
    if content_type:
        match = re.search(r"charset=([\w.-]+)", content_type, flags=re.IGNORECASE)
        if match:
            encoding = match.group(1)

    text = data.decode(encoding, errors="replace")
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", "\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [" ".join(line.replace("\xa0", " ").split()).strip() for line in text.splitlines()]
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


def parse_html_bytes(data: bytes, content_type: str | None = None) -> list[ParsedHtmlChunk]:
    text = html_bytes_to_text(data, content_type)
    return [
        ParsedHtmlChunk(
            chunk_index=index,
            heading_path="网页公告",
            content_text=part,
        )
        for index, part in enumerate(_split_text(text), start=1)
    ]
