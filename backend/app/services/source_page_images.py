from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SourcePageImage
from app.services.storage import put_object_bytes


@dataclass(frozen=True)
class RenderedPageImage:
    data: bytes
    width: int
    height: int
    image_format: str
    content_type: str
    render_scale: float
    max_width: int
    image_quality: int | None


def _image_format() -> str:
    value = settings.source_page_image_format.lower().strip()
    return value if value in {"jpeg", "png"} else "jpeg"


def _jpeg_quality() -> int:
    return max(30, min(95, int(settings.source_page_image_jpeg_quality)))


def _render_scale(page: fitz.Page, *, configured_scale: float, max_width: int) -> float:
    page_width = float(page.rect.width) or 1.0
    scale_by_width = max_width / page_width if max_width > 0 else configured_scale
    return max(0.5, min(configured_scale, scale_by_width))


def render_compressed_pdf_page_image(
    pdf_data: bytes,
    *,
    page_no: int,
) -> RenderedPageImage:
    image_format = _image_format()
    max_width = max(600, int(settings.source_page_image_max_width))
    configured_scale = max(0.5, float(settings.source_page_image_render_scale))
    with fitz.open(stream=pdf_data, filetype="pdf") as document:
        if page_no < 1 or page_no > len(document):
            raise ValueError(f"PDF page out of range: {page_no}")
        page = document.load_page(page_no - 1)
        scale = _render_scale(page, configured_scale=configured_scale, max_width=max_width)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        if image_format == "png":
            data = pixmap.tobytes("png")
            quality = None
            content_type = "image/png"
        else:
            quality = _jpeg_quality()
            data = pixmap.tobytes("jpeg", jpg_quality=quality)
            content_type = "image/jpeg"
    return RenderedPageImage(
        data=data,
        width=pixmap.width,
        height=pixmap.height,
        image_format=image_format,
        content_type=content_type,
        render_scale=scale,
        max_width=max_width,
        image_quality=quality,
    )


def source_page_image_object_key(
    *,
    tenant_id: uuid.UUID,
    source_sha256: str,
    page_no: int,
    image_format: str,
    max_width: int,
    image_quality: int | None,
    render_scale: float,
) -> str:
    suffix = "jpg" if image_format == "jpeg" else image_format
    quality_part = f"q{image_quality}" if image_quality is not None else "lossless"
    scale_part = str(round(render_scale, 3)).replace(".", "p")
    return (
        f"tenants/{tenant_id}/source-page-images/{source_sha256}/"
        f"scale-{scale_part}-w{max_width}-{quality_part}/page-{page_no:04d}.{suffix}"
    )


def page_image_payload(asset: SourcePageImage, *, block_index: int | None = None, parser: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(asset.id),
        "page_image_id": str(asset.id),
        "bucket": asset.image_bucket,
        "object_key": asset.image_object_key,
        "content_type": asset.image_content_type,
        "image_format": asset.image_format,
        "image_quality": asset.image_quality,
        "file_size": asset.image_file_size,
        "sha256": asset.image_sha256,
        "page_no": asset.page_no,
        "width": asset.width,
        "height": asset.height,
        "render_scale": asset.render_scale,
        "max_width": asset.max_width,
        "source": "source_page_image_asset",
        "source_file_name": asset.source_file_name,
        "source_sha256": asset.source_sha256,
    }
    if block_index is not None:
        payload["block_index"] = block_index
    if parser:
        payload["parser"] = parser
    return payload


def get_or_create_pdf_page_image_asset(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source_kind: str,
    source_id: uuid.UUID | None,
    source_bucket: str,
    source_object_key: str,
    source_sha256: str,
    source_file_name: str | None,
    pdf_data: bytes,
    page_no: int,
    image_bucket: str,
) -> SourcePageImage:
    rendered = render_compressed_pdf_page_image(pdf_data, page_no=page_no)
    existing = db.scalar(
        select(SourcePageImage).where(
            SourcePageImage.tenant_id == tenant_id,
            SourcePageImage.source_sha256 == source_sha256,
            SourcePageImage.page_no == page_no,
            SourcePageImage.render_scale == rendered.render_scale,
            SourcePageImage.image_format == rendered.image_format,
            SourcePageImage.max_width == rendered.max_width,
            SourcePageImage.image_quality == rendered.image_quality,
        )
    )
    if existing is not None:
        return existing

    image_sha256 = hashlib.sha256(rendered.data).hexdigest()
    image_object_key = source_page_image_object_key(
        tenant_id=tenant_id,
        source_sha256=source_sha256,
        page_no=page_no,
        image_format=rendered.image_format,
        max_width=rendered.max_width,
        image_quality=rendered.image_quality,
        render_scale=rendered.render_scale,
    )
    put_object_bytes(
        bucket=image_bucket,
        object_key=image_object_key,
        data=rendered.data,
        content_type=rendered.content_type,
    )
    asset = SourcePageImage(
        tenant_id=tenant_id,
        source_kind=source_kind,
        source_id=source_id,
        source_bucket=source_bucket,
        source_object_key=source_object_key,
        source_sha256=source_sha256,
        source_file_name=source_file_name,
        page_no=page_no,
        image_bucket=image_bucket,
        image_object_key=image_object_key,
        image_content_type=rendered.content_type,
        image_format=rendered.image_format,
        image_quality=rendered.image_quality,
        image_file_size=len(rendered.data),
        image_sha256=image_sha256,
        width=rendered.width,
        height=rendered.height,
        render_scale=rendered.render_scale,
        max_width=rendered.max_width,
        status="ready",
    )
    db.add(asset)
    db.flush()
    return asset
