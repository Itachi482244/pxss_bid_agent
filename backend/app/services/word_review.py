from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from xml.etree import ElementTree as ET

from app.models import Document, DocumentChunk, DocumentVersion
from app.schemas.project import (
    ReviewDocumentBlock,
    ReviewDocumentPage,
    ReviewDocumentPageMargins,
    ReviewDocumentParagraph,
    ReviewDocumentParagraphStyle,
    ReviewDocumentRun,
    ReviewDocumentRunStyle,
    ReviewDocumentTableCell,
    ReviewDocumentTableRow,
    MatrixReviewDocumentRead,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}


class WordReviewError(Exception):
    pass


@dataclass
class StyleDef:
    style_id: str
    style_type: str
    name: str | None = None
    paragraph: dict[str, object | None] = field(default_factory=dict)
    run: dict[str, object | None] = field(default_factory=dict)


def _qn(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def _attr(element: ET.Element | None, name: str) -> str | None:
    if element is None:
        return None
    return element.attrib.get(_qn(name))


def _twips_to_pt(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return round(int(value) / 20, 2)
    except ValueError:
        return None


def _half_points_to_pt(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return round(int(value) / 2, 2)
    except ValueError:
        return None


def _clean_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _text_from_element(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.tag == _qn("t") and node.text:
            parts.append(node.text)
        elif node.tag == _qn("tab"):
            parts.append("\t")
        elif node.tag in {_qn("br"), _qn("cr")}:
            parts.append("\n")
    return "".join(parts)


def _parse_run_style(r_pr: ET.Element | None) -> dict[str, object | None]:
    if r_pr is None:
        return {}
    fonts = r_pr.find("w:rFonts", NS)
    font_family = None
    if fonts is not None:
        font_family = (
            _attr(fonts, "eastAsia")
            or _attr(fonts, "ascii")
            or _attr(fonts, "hAnsi")
            or _attr(fonts, "cs")
        )
    color = _attr(r_pr.find("w:color", NS), "val")
    if color in {None, "auto"}:
        color = None
    elif color and not color.startswith("#"):
        color = f"#{color}"
    underline = r_pr.find("w:u", NS) is not None and _attr(r_pr.find("w:u", NS), "val") != "none"
    return {
        "font_family": font_family,
        "font_size_pt": _half_points_to_pt(_attr(r_pr.find("w:sz", NS), "val")),
        "bold": r_pr.find("w:b", NS) is not None,
        "italic": r_pr.find("w:i", NS) is not None,
        "underline": underline,
        "color": color,
    }


def _parse_paragraph_style(p_pr: ET.Element | None) -> dict[str, object | None]:
    if p_pr is None:
        return {}
    ind = p_pr.find("w:ind", NS)
    spacing = p_pr.find("w:spacing", NS)
    line_spacing = None
    if spacing is not None and _attr(spacing, "line") is not None:
        try:
            line_spacing = round(int(_attr(spacing, "line") or "0") / 240, 2)
        except ValueError:
            line_spacing = None
    return {
        "style_id": _attr(p_pr.find("w:pStyle", NS), "val"),
        "alignment": _attr(p_pr.find("w:jc", NS), "val"),
        "indent_left_pt": _twips_to_pt(_attr(ind, "left")),
        "first_line_indent_pt": _twips_to_pt(_attr(ind, "firstLine")),
        "line_spacing": line_spacing,
    }


def _merge_run_style(base: dict[str, object | None], direct: dict[str, object | None]) -> ReviewDocumentRunStyle:
    merged = {**base, **{key: value for key, value in direct.items() if value is not None}}
    return ReviewDocumentRunStyle(
        font_family=merged.get("font_family") if isinstance(merged.get("font_family"), str) else None,
        font_size_pt=merged.get("font_size_pt") if isinstance(merged.get("font_size_pt"), (int, float)) else None,
        bold=bool(merged.get("bold")),
        italic=bool(merged.get("italic")),
        underline=bool(merged.get("underline")),
        color=merged.get("color") if isinstance(merged.get("color"), str) else None,
    )


def _merge_paragraph_style(
    style_id: str | None,
    styles: dict[str, StyleDef],
    direct: dict[str, object | None],
) -> ReviewDocumentParagraphStyle:
    style_def = styles.get(style_id or "")
    base = style_def.paragraph if style_def else {}
    merged = {**base, **{key: value for key, value in direct.items() if value is not None}}
    return ReviewDocumentParagraphStyle(
        style_id=style_id,
        style_name=style_def.name if style_def else None,
        alignment=merged.get("alignment") if isinstance(merged.get("alignment"), str) else None,
        indent_left_pt=merged.get("indent_left_pt") if isinstance(merged.get("indent_left_pt"), (int, float)) else None,
        first_line_indent_pt=(
            merged.get("first_line_indent_pt")
            if isinstance(merged.get("first_line_indent_pt"), (int, float))
            else None
        ),
        line_spacing=merged.get("line_spacing") if isinstance(merged.get("line_spacing"), (int, float)) else None,
    )


def _parse_styles(archive: zipfile.ZipFile) -> dict[str, StyleDef]:
    try:
        root = ET.fromstring(archive.read("word/styles.xml"))
    except KeyError:
        return {}
    styles: dict[str, StyleDef] = {}
    for style in root.findall("w:style", NS):
        style_id = _attr(style, "styleId")
        if not style_id:
            continue
        name = _attr(style.find("w:name", NS), "val")
        style_type = _attr(style, "type") or "paragraph"
        styles[style_id] = StyleDef(
            style_id=style_id,
            style_type=style_type,
            name=name,
            paragraph=_parse_paragraph_style(style.find("w:pPr", NS)),
            run=_parse_run_style(style.find("w:rPr", NS)),
        )
    return styles


def _parse_page_margins(root: ET.Element) -> ReviewDocumentPageMargins | None:
    sect_pr = root.find(".//w:sectPr", NS)
    pg_mar = sect_pr.find("w:pgMar", NS) if sect_pr is not None else None
    if pg_mar is None:
        return None
    return ReviewDocumentPageMargins(
        top=_twips_to_pt(_attr(pg_mar, "top")),
        right=_twips_to_pt(_attr(pg_mar, "right")),
        bottom=_twips_to_pt(_attr(pg_mar, "bottom")),
        left=_twips_to_pt(_attr(pg_mar, "left")),
    )


def _parse_header_footer_texts(archive: zipfile.ZipFile, prefix: str) -> list[str]:
    texts: list[str] = []
    for name in sorted(item for item in archive.namelist() if item.startswith(prefix) and item.endswith(".xml")):
        try:
            root = ET.fromstring(archive.read(name))
        except ET.ParseError:
            continue
        text = _clean_text(_text_from_element(root))
        if text and text not in texts:
            texts.append(text)
    return texts


def _paragraph_from_xml(element: ET.Element, styles: dict[str, StyleDef]) -> ReviewDocumentParagraph:
    p_pr = element.find("w:pPr", NS)
    direct_p = _parse_paragraph_style(p_pr)
    style_id = direct_p.get("style_id") if isinstance(direct_p.get("style_id"), str) else None
    paragraph_style = _merge_paragraph_style(style_id, styles, direct_p)
    style_run = styles.get(style_id or "").run if style_id in styles else {}

    runs: list[ReviewDocumentRun] = []
    for run_node in element.findall("w:r", NS):
        raw_text = _text_from_element(run_node)
        if raw_text == "":
            continue
        runs.append(
            ReviewDocumentRun(
                text=raw_text,
                style=_merge_run_style(style_run, _parse_run_style(run_node.find("w:rPr", NS))),
            )
        )
    text = "".join(run.text for run in runs)
    return ReviewDocumentParagraph(text=text, runs=runs, style=paragraph_style)


def _table_text(rows: list[ReviewDocumentTableRow]) -> str:
    rendered_rows: list[str] = []
    for row in rows:
        cells = [" ".join(paragraph.text.split()).strip() for cell in row.cells for paragraph in cell.paragraphs]
        rendered_rows.append(" | ".join(cell for cell in cells if cell))
    return "\n".join(row for row in rendered_rows if row).strip()


def _chunk_by_text(chunks: list[DocumentChunk]) -> dict[str, list[DocumentChunk]]:
    by_text: dict[str, list[DocumentChunk]] = {}
    for chunk in chunks:
        by_text.setdefault(_clean_text(chunk.content_text), []).append(chunk)
    return by_text


def _take_matching_chunk(text: str, by_text: dict[str, list[DocumentChunk]]) -> DocumentChunk | None:
    matches = by_text.get(_clean_text(text))
    if not matches:
        return None
    return matches.pop(0)


def build_chunk_fallback_review_document(
    document: Document | None,
    version: DocumentVersion | None,
    chunks: list[DocumentChunk],
    *,
    reason: str,
) -> MatrixReviewDocumentRead:
    blocks = [
        ReviewDocumentBlock(
            id=f"chunk-{chunk.id}",
            type="paragraph",
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            page_no=chunk.page_no,
            bbox_json=chunk.bbox_json,
            text=chunk.content_text,
            paragraph=ReviewDocumentParagraph(
                text=chunk.content_text,
                runs=[ReviewDocumentRun(text=chunk.content_text)],
            ),
        )
        for chunk in chunks
    ]
    return MatrixReviewDocumentRead(
        mode="chunk_fallback",
        document_id=document.id if document else None,
        title=document.title if document else None,
        original_filename=document.original_filename if document else None,
        version_id=version.id if version else None,
        version_label=version.version_label if version else None,
        reason=reason,
        blocks=blocks,
)


def _paragraph_from_text(text: str) -> ReviewDocumentParagraph:
    return ReviewDocumentParagraph(
        text=text,
        runs=[ReviewDocumentRun(text=text)],
    )


def _table_rows_from_json(table_json: dict | None) -> list[ReviewDocumentTableRow]:
    raw_rows = table_json.get("rows") if isinstance(table_json, dict) else None
    if not isinstance(raw_rows, list):
        return []
    rows: list[ReviewDocumentTableRow] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, list):
            continue
        cells = [
            ReviewDocumentTableCell(paragraphs=[_paragraph_from_text(str(cell or ""))])
            for cell in raw_row
        ]
        rows.append(ReviewDocumentTableRow(cells=cells))
    return rows


def _is_pdf_layout_chunk(chunk: DocumentChunk) -> bool:
    bbox = chunk.bbox_json
    if not isinstance(bbox, dict):
        return False
    return all(key in bbox for key in ("page_width", "page_height", "x0", "y0", "x1", "y1"))


def _pdf_pages(chunks: list[DocumentChunk]) -> list[ReviewDocumentPage]:
    pages: dict[int, ReviewDocumentPage] = {}
    for chunk in chunks:
        if chunk.page_no is None:
            continue
        bbox = chunk.bbox_json if isinstance(chunk.bbox_json, dict) else {}
        width = bbox.get("page_width")
        height = bbox.get("page_height")
        pages.setdefault(
            chunk.page_no,
            ReviewDocumentPage(
                page_no=chunk.page_no,
                width=width if isinstance(width, (int, float)) else None,
                height=height if isinstance(height, (int, float)) else None,
            ),
        )
    return [pages[key] for key in sorted(pages)]


def build_pdf_review_document(
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
) -> MatrixReviewDocumentRead:
    if document.file_ext != "pdf":
        raise WordReviewError("Only .pdf documents can use pdf_layout review mode")
    if not chunks:
        raise WordReviewError("PDF 解析版本暂无可展示原文")
    if not any(_is_pdf_layout_chunk(chunk) for chunk in chunks):
        raise WordReviewError("当前 PDF 解析版本缺少版面信息，请重新解析 PDF 后再审阅。")

    blocks: list[ReviewDocumentBlock] = []
    for chunk in sorted(chunks, key=lambda item: (item.page_no or 0, item.chunk_index)):
        rows = _table_rows_from_json(chunk.table_json)
        block_type = "table" if rows else "paragraph"
        blocks.append(
            ReviewDocumentBlock(
                id=f"pdf-chunk-{chunk.id}",
                type=block_type,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                page_no=chunk.page_no,
                bbox_json=chunk.bbox_json,
                text=chunk.content_text,
                paragraph=None if rows else _paragraph_from_text(chunk.content_text),
                rows=rows,
            )
        )

    return MatrixReviewDocumentRead(
        mode="pdf_layout",
        document_id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        version_id=version.id,
        version_label=version.version_label,
        pages=_pdf_pages(chunks),
        blocks=blocks,
    )


def build_word_review_document(
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
    data: bytes,
) -> MatrixReviewDocumentRead:
    if document.file_ext != "docx":
        raise WordReviewError("Only .docx documents can use word_xml review mode")

    try:
        archive = zipfile.ZipFile(BytesIO(data))
        root = ET.fromstring(archive.read("word/document.xml"))
    except (KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise WordReviewError("Failed to parse Word OpenXML document") from exc

    styles = _parse_styles(archive)
    by_text = _chunk_by_text(chunks)
    blocks: list[ReviewDocumentBlock] = []

    body = root.find("w:body", NS)
    if body is None:
        raise WordReviewError("Word document body not found")

    for child in body:
        if child.tag == _qn("p"):
            paragraph = _paragraph_from_xml(child, styles)
            clean = _clean_text(paragraph.text)
            if not clean:
                continue
            chunk = _take_matching_chunk(clean, by_text)
            style_name = (paragraph.style.style_name or "").lower()
            block_type = "heading" if "heading" in style_name or "标题" in style_name else "paragraph"
            blocks.append(
                ReviewDocumentBlock(
                    id=f"block-{len(blocks) + 1}",
                    type=block_type,
                    chunk_id=chunk.id if chunk else None,
                    chunk_index=chunk.chunk_index if chunk else None,
                    page_no=chunk.page_no if chunk else None,
                    bbox_json=chunk.bbox_json if chunk else None,
                    text=clean,
                    paragraph=paragraph,
                )
            )
        elif child.tag == _qn("tbl"):
            rows: list[ReviewDocumentTableRow] = []
            for tr in child.findall("w:tr", NS):
                cells: list[ReviewDocumentTableCell] = []
                for tc in tr.findall("w:tc", NS):
                    paragraphs = [
                        _paragraph_from_xml(p, styles)
                        for p in tc.findall("w:p", NS)
                        if _clean_text(_text_from_element(p))
                    ]
                    cells.append(ReviewDocumentTableCell(paragraphs=paragraphs))
                rows.append(ReviewDocumentTableRow(cells=cells))
            text = _table_text(rows)
            if not text:
                continue
            chunk = _take_matching_chunk(text, by_text)
            blocks.append(
                ReviewDocumentBlock(
                    id=f"block-{len(blocks) + 1}",
                    type="table",
                    chunk_id=chunk.id if chunk else None,
                    chunk_index=chunk.chunk_index if chunk else None,
                    page_no=chunk.page_no if chunk else None,
                    bbox_json=chunk.bbox_json if chunk else None,
                    text=text,
                    rows=rows,
                )
            )

    return MatrixReviewDocumentRead(
        mode="word_xml",
        document_id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        version_id=version.id,
        version_label=version.version_label,
        page_margins=_parse_page_margins(root),
        headers=_parse_header_footer_texts(archive, "word/header"),
        footers=_parse_header_footer_texts(archive, "word/footer"),
        blocks=blocks,
    )
