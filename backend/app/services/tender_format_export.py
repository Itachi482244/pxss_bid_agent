from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AuditLog,
    BidSection,
    ComplianceEvidenceBinding,
    ComplianceItem,
    EnterpriseMaterial,
    ExportFile,
    Project,
)
from app.services.context_pack import _material_applies_to_project, _project_facts
from app.services.storage import get_object_bytes, put_object_bytes
from app.services.tender_directory import derive_directory
from app.services.tender_format_assembler import (
    assemble_format_docx,
    build_form_facts,
    material_render_candidate_ids,
)
from app.services.tender_outline import load_tender_text, map_nodes_to_chapters
from app.services.template_profile import get_template_profile


class TenderFormatExportError(Exception):
    pass


_EMBED_ALLOWED_DATA_LEVELS = {"public", "internal"}
_EMBED_CONFIRMED_STATUSES = {"confirmed"}
_EMBED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}
_EMBED_PDF_MAX_PAGES = 8


def _bump_diag(diag: dict[str, int] | None, key: str, amount: int = 1) -> None:
    if diag is not None:
        diag[key] = int(diag.get(key, 0)) + amount


def _as_dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _material_confirmed_for_export(material: EnterpriseMaterial) -> bool:
    return (
        material.verification_status in _EMBED_CONFIRMED_STATUSES
        and material.data_level in _EMBED_ALLOWED_DATA_LEVELS
    )


def _source_image_refs(material: EnterpriseMaterial) -> list[dict[str, Any]]:
    fields = material.structured_fields if isinstance(material.structured_fields, dict) else {}
    refs: list[dict[str, Any]] = []
    primary = fields.get("primary_source_image")
    if isinstance(primary, dict):
        refs.append(primary)
    refs.extend(_as_dict_list(fields.get("source_images")))
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for ref in refs:
        bucket = str(ref.get("bucket") or "")
        object_key = str(ref.get("object_key") or "")
        if not bucket or not object_key or (bucket, object_key) in seen:
            continue
        seen.add((bucket, object_key))
        unique.append(ref)
    return unique


def _fetch_source_images(
    material: EnterpriseMaterial,
    *,
    diag: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    for index, ref in enumerate(_source_image_refs(material), start=1):
        content_type = str(ref.get("content_type") or "").lower()
        if content_type not in _EMBED_IMAGE_CONTENT_TYPES:
            _bump_diag(diag, "source_image_unsupported_count")
            continue
        try:
            data = get_object_bytes(bucket=str(ref["bucket"]), object_key=str(ref["object_key"]))
        except Exception:
            _bump_diag(diag, "source_image_fetch_failed_count")
            continue
        images.append(
            {
                "data": data,
                "content_type": content_type,
                "caption": f"{material.name} 第{ref.get('page_no') or index}页",
                "source": ref.get("source") or "source_image",
            }
        )
    return images


def _render_pdf_images(
    pdf_data: bytes,
    *,
    material_name: str,
    diag: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    try:
        with fitz.open(stream=pdf_data, filetype="pdf") as document:
            page_count = min(len(document), _EMBED_PDF_MAX_PAGES)
            for page_index in range(page_count):
                try:
                    page = document.load_page(page_index)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                except Exception:
                    _bump_diag(diag, "pdf_page_render_failed_count")
                    continue
                images.append(
                    {
                        "data": pixmap.tobytes("png"),
                        "content_type": "image/png",
                        "caption": f"{material_name} 第{page_index + 1}页",
                        "source": "rendered_pdf_page",
                    }
                )
    except Exception:
        _bump_diag(diag, "pdf_open_failed_count")
        return []
    return images


def _fetch_original_file_images(
    material: EnterpriseMaterial,
    *,
    diag: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    if not material.bucket or not material.object_key:
        return []
    content_type = (material.content_type or "").lower()
    try:
        data = get_object_bytes(bucket=material.bucket, object_key=material.object_key)
    except Exception:
        _bump_diag(diag, "original_file_fetch_failed_count")
        return []
    if content_type in _EMBED_IMAGE_CONTENT_TYPES:
        return [
            {
                "data": data,
                "content_type": content_type,
                "caption": material.name,
                "source": "original_image",
            }
        ]
    if content_type == "application/pdf" or (material.file_name or "").lower().endswith(".pdf"):
        return _render_pdf_images(data, material_name=material.name, diag=diag)
    _bump_diag(diag, "original_file_unsupported_count")
    return []


def _material_snapshots(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project: Project,
    chapters: list[dict[str, Any]] | None = None,
    response_items: list[dict[str, Any]] | None = None,
    image_diag: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    materials = db.scalars(
        select(EnterpriseMaterial)
        .where(EnterpriseMaterial.tenant_id == tenant_id)
        .order_by(EnterpriseMaterial.created_at.desc())
    ).all()
    snapshots: list[dict[str, Any]] = []
    exportable_materials: list[EnterpriseMaterial] = []
    for material in materials:
        if not _material_applies_to_project(material, project):
            continue
        if not _material_confirmed_for_export(material):
            continue
        exportable_materials.append(material)
        snapshots.append(
            {
                "material_id": str(material.id),
                "material_name": material.name,
                "material_type": material.material_type,
                "verification_status": material.verification_status,
                "data_level": material.data_level,
                "certificate_no": material.certificate_no,
                "evidence_text": material.evidence_text,
                "file_name": material.file_name,
                "content_type": material.content_type,
                "bucket": material.bucket,
                "object_key": material.object_key,
                "embedded_images": [],
                "embedded_image_count": 0,
                "image_fetch_selected": False,
            }
        )

    if chapters is None:
        selected_material_ids = {str(material.id) for material in exportable_materials}
    else:
        selected_material_ids = material_render_candidate_ids(
            chapters,
            snapshots,
            compliance_items=response_items,
        )
    selected_material_ids &= {str(material.id) for material in exportable_materials}
    if image_diag is not None:
        image_diag["material_snapshot_count"] = len(snapshots)
        image_diag["material_image_candidate_count"] = len(selected_material_ids)

    for material, snapshot in zip(exportable_materials, snapshots, strict=True):
        if str(material.id) not in selected_material_ids:
            continue
        _bump_diag(image_diag, "material_image_fetch_selected_count")
        embedded_images = _fetch_source_images(material, diag=image_diag) or _fetch_original_file_images(
            material,
            diag=image_diag,
        )
        snapshot["embedded_images"] = embedded_images
        snapshot["embedded_image_count"] = len(embedded_images)
        snapshot["image_fetch_selected"] = True
        _bump_diag(image_diag, "embedded_image_count", len(embedded_images))
    return snapshots


def _material_snapshot_for_audit(material: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in material.items()
        if key not in {"embedded_images"}
    }


def _response_item_snapshots(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> list[dict[str, Any]]:
    items = db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.item_type.in_(["scoring", "technical_response"]),
            ComplianceItem.deleted_at.is_(None),
            ComplianceItem.status.notin_(["rejected", "superseded"]),
        )
        .order_by(ComplianceItem.source_page_no.asc().nullslast(), ComplianceItem.created_at.asc())
    ).all()
    if not items:
        return []
    item_ids = [item.id for item in items]
    bindings = db.scalars(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.compliance_item_id.in_(item_ids),
            ComplianceEvidenceBinding.status == "active",
        )
    ).all()
    bindings_by_item: dict[uuid.UUID, list[ComplianceEvidenceBinding]] = {}
    for binding in bindings:
        bindings_by_item.setdefault(binding.compliance_item_id, []).append(binding)

    snapshots: list[dict[str, Any]] = []
    for item in items:
        evidence_bindings = []
        for binding in bindings_by_item.get(item.id, []):
            material_snapshot = binding.material_snapshot or {}
            evidence_bindings.append(
                {
                    "id": str(binding.id),
                    "enterprise_material_id": str(binding.enterprise_material_id),
                    "material_name": material_snapshot.get("name")
                    or material_snapshot.get("material_name"),
                    "material_type": material_snapshot.get("material_type"),
                    "evidence_text": binding.evidence_text,
                    "confidence_score": str(binding.confidence_score)
                    if binding.confidence_score is not None
                    else None,
                    "status": binding.status,
                }
            )
        snapshots.append(
            {
                "id": str(item.id),
                "item_type": item.item_type,
                "requirement_text": item.requirement_text,
                "normalized_requirement": item.normalized_requirement,
                "status": item.status,
                "risk_level": item.risk_level,
                "is_mandatory": item.is_mandatory,
                "response_suggestion": item.response_suggestion,
                "evidence_text": item.evidence_text,
                "source_page_no": item.source_page_no,
                "evidence_bindings": evidence_bindings,
            }
        )
    return snapshots


def export_tender_format_docx(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    profile_id: str | None = None,
    export_mode: str = "review",
) -> ExportFile:
    project = db.get(Project, project_id)
    section = db.get(BidSection, section_id)
    if project is None or section is None or project.tenant_id != tenant_id or section.tenant_id != tenant_id:
        raise TenderFormatExportError("项目或标段不存在")

    text, source_meta = load_tender_text(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    if text is None:
        raise TenderFormatExportError(f"当前标段没有可装配的招标正文：{source_meta.get('reason')}")

    outline = derive_directory(text)
    profile = get_template_profile(profile_id)
    chapters = map_nodes_to_chapters(outline.nodes, profile)
    if not chapters:
        raise TenderFormatExportError("未能从招标文件推导出响应文件目录")

    project_facts = _project_facts(db, tenant_id=tenant_id, project=project, section=section)
    form_facts = build_form_facts(project_facts, outline.signals)
    response_items = _response_item_snapshots(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    material_image_diag: dict[str, int] = {}
    material_snapshots = _material_snapshots(
        db,
        tenant_id=tenant_id,
        project=project,
        chapters=chapters,
        response_items=response_items,
        image_diag=material_image_diag,
    )
    data, diag = assemble_format_docx(
        text=text,
        chapters=chapters,
        facts=form_facts,
        project_name=project.name,
        supplier_name=form_facts.get("supplier_name"),
        available_materials=material_snapshots,
        compliance_items=response_items,
        budget_amount=section.budget_amount or project.budget_amount,
        export_mode=export_mode,
    )

    content_hash = hashlib.sha256(data).hexdigest()
    export_id = uuid.uuid4()
    now = datetime.now(UTC)
    mode_label = "审阅版" if export_mode == "review" else "正式版"
    file_name = f"格式标装配-{mode_label}-{now.strftime('%Y%m%d%H%M%S')}.docx"
    object_key = (
        f"tenant/{tenant_id}/project/{project_id}/section/{section_id}/"
        f"exports/{export_id}/{file_name}"
    )
    put_object_bytes(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    source_snapshot = {
        "exported_at": now.isoformat(),
        "export_mode": export_mode,
        "profile_id": profile["profile_id"],
        "profile_version": profile["version"],
        "directory_source": source_meta,
        "procurement_method": outline.procurement_method,
        "document_term": outline.document_term,
        "signals": outline.signals,
        "chapter_count": len(chapters),
        "material_snapshot_count": len(material_snapshots),
        "material_image_diag": material_image_diag,
        "material_snapshots": [_material_snapshot_for_audit(material) for material in material_snapshots],
        "response_item_count": len(response_items),
        "scoring_item_count": sum(1 for item in response_items if item.get("item_type") == "scoring"),
        "technical_response_item_count": sum(
            1 for item in response_items if item.get("item_type") == "technical_response"
        ),
        "assembler_diag": diag,
    }
    export_file = ExportFile(
        id=export_id,
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_id=None,
        export_type="tender_format_docx",
        file_name=file_name,
        bucket=settings.minio_bucket,
        object_key=object_key,
        sha256=content_hash,
        filter_json={"export_mode": export_mode},
        source_snapshot_json=source_snapshot,
        status="available",
        created_by=actor_user_id,
    )
    db.add(export_file)
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="tender_format.docx_exported",
            object_type="export_file",
            object_id=export_file.id,
            after_json={"file_name": file_name, "sha256": content_hash, "source_snapshot": source_snapshot},
            reason=f"导出投标文件格式装配 {mode_label}",
            severity="warning" if diag.get("disqualifying_gaps") else "info",
        )
    )
    return export_file
