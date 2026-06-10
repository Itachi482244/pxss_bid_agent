from __future__ import annotations

import re
from pathlib import Path


MAX_FILE_BYTES = 50 * 1024 * 1024
TENDER_DOCUMENT_FILE_MAX_BYTES = 200 * 1024 * 1024
HISTORY_MATERIAL_FILE_MAX_BYTES = 200 * 1024 * 1024


def readable_file_size(size: int) -> str:
    mib = size / 1024 / 1024
    return f"{mib:.0f} MiB" if mib.is_integer() else f"{mib:.1f} MiB"


def safe_filename(filename: str | None) -> str:
    raw_name = Path(filename or "document.bin").name
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", raw_name).strip("._")
    return cleaned or "document.bin"


def file_extension(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or None


def infer_parser_type(file_ext: str | None, content_type: str | None) -> str:
    if file_ext in {"doc", "docx"}:
        return "word"
    if file_ext in {"xls", "xlsx"}:
        return "excel"
    if file_ext in {"jpg", "jpeg", "png", "bmp", "tif", "tiff"}:
        return "ocr"
    if content_type and content_type.startswith("image/"):
        return "ocr"
    return "pdf_text"
