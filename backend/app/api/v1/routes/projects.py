from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import RequestContext, get_request_context
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    AsyncTask,
    AuditLog,
    ApprovalTask,
    BidSection,
    BusinessDraftChapter,
    BusinessDraftEvidenceRef,
    ComplianceEvidenceBinding,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentVersion,
    DraftFactCheck,
    EnterpriseMaterial,
    ExportFile,
    Project,
    ProjectMember,
    ModelInvocationLog,
    QualificationDecision,
    QualificationEvaluation,
    User,
    EnterpriseProfile,
)
from app.schemas.document import AsyncTaskRead, ComplianceMatrixExportRequest, ExportFileRead
from app.schemas.project import (
    AuditLogRead,
    ApprovalTaskCreateRequest,
    ApprovalTaskDecisionRequest,
    ApprovalTaskRead,
    BusinessDraftChapterRead,
    BusinessDraftChapterUpdateRequest,
    BusinessDraftEvidenceRefRead,
    BusinessDraftGenerateRequest,
    ComplianceItemAssignRequest,
    ComplianceEvidenceBindRequest,
    ComplianceEvidenceBindingRead,
    ComplianceEvidenceUnbindRequest,
    ComplianceItemsBulkAssignRequest,
    ComplianceItemsBulkConfirmRequest,
    ComplianceItemConfirmRequest,
    ComplianceMatrixGenerateRequest,
    DraftFactCheckRead,
    ComplianceItemRead,
    ComplianceItemUpdateRequest,
    ModelInvocationLogRead,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectImportConfirmRead,
    ProjectImportConfirmRequest,
    ProjectImportDraftRead,
    ProjectImportProjectDraft,
    ProjectImportSectionDraft,
    ProjectImportSourceRead,
    ProjectImportUrlRequest,
    QualificationDecisionConfirmRequest,
    QualificationDecisionRead,
    QualificationEvaluationConfirmRequest,
    QualificationEvaluationRead,
    ProjectSummary,
    SectionCreateRequest,
    SectionSummary,
)
from app.services.business_draft import (
    BusinessDraftError,
    export_business_draft_word,
    generate_business_draft_chapters,
    run_fact_checks,
)
from app.services.compliance_generation import execute_compliance_matrix_generation_task
from app.services.document_utils import MAX_FILE_BYTES
from app.services.export_excel import execute_compliance_matrix_excel_export_task
from app.services.file_acquisition import FileAcquisitionError
from app.services.project_import import (
    ImportDraft,
    build_upload_import_draft,
    build_url_import_draft,
    confirm_import_draft,
)
from app.services.qualification_evaluation import evaluation_snapshot, run_qualification_evaluation
from app.services.storage import get_object_bytes

router = APIRouter()


def visible_project_ids(ctx: RequestContext) -> Select[tuple[uuid.UUID]]:
    return select(ProjectMember.project_id).where(
        ProjectMember.tenant_id == ctx.tenant_id,
        ProjectMember.user_id == ctx.user_id,
        ProjectMember.status == "active",
    )


def get_project_or_404(
    db: Session,
    ctx: RequestContext,
    project_id: uuid.UUID,
) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.tenant_id == ctx.tenant_id,
            Project.id == project_id,
            Project.id.in_(visible_project_ids(ctx)),
        )
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not authorized",
        )
    return project


def get_section_or_404(
    db: Session,
    ctx: RequestContext,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> BidSection:
    get_project_or_404(db, ctx, project_id)
    section = db.scalar(
        select(BidSection).where(
            BidSection.tenant_id == ctx.tenant_id,
            BidSection.project_id == project_id,
            BidSection.id == section_id,
        )
    )
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


def get_compliance_item_or_404(
    db: Session,
    ctx: RequestContext,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
) -> ComplianceItem:
    get_section_or_404(db, ctx, project_id, section_id)
    item = db.scalar(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.id == item_id,
            ComplianceItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance item not found",
        )
    return item


def get_active_user_or_404(
    db: Session,
    ctx: RequestContext,
    user_id: uuid.UUID,
) -> User:
    user = db.scalar(
        select(User).where(
            User.tenant_id == ctx.tenant_id,
            User.id == user_id,
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner user not found")
    return user


def compliance_item_snapshot(item: ComplianceItem) -> dict[str, object]:
    return {
        "id": str(item.id),
        "requirement_text": item.requirement_text,
        "response_suggestion": item.response_suggestion,
        "status": item.status,
        "risk_level": item.risk_level,
        "is_mandatory": item.is_mandatory,
        "is_batch_confirm_allowed": item.is_batch_confirm_allowed,
        "explanation_json": item.explanation_json,
        "owner_user_id": str(item.owner_user_id) if item.owner_user_id else None,
        "confirmed_by": str(item.confirmed_by) if item.confirmed_by else None,
        "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None,
        "modified_by": str(item.modified_by) if item.modified_by else None,
        "modified_at": item.modified_at.isoformat() if item.modified_at else None,
        "modify_reason": item.modify_reason,
    }


def enterprise_material_snapshot(material: EnterpriseMaterial) -> dict[str, object]:
    return {
        "id": str(material.id),
        "material_type": material.material_type,
        "name": material.name,
        "issuing_authority": material.issuing_authority,
        "certificate_no": material.certificate_no,
        "holder_name": material.holder_name,
        "project_name": material.project_name,
        "amount": material.amount,
        "valid_from": material.valid_from.isoformat() if material.valid_from else None,
        "valid_until": material.valid_until.isoformat() if material.valid_until else None,
        "data_level": material.data_level,
        "verification_status": material.verification_status,
        "structured_fields": material.structured_fields,
        "evidence_text": material.evidence_text,
        "file_name": material.file_name,
        "sha256": material.sha256,
    }


def evidence_binding_snapshot(binding: ComplianceEvidenceBinding) -> dict[str, object]:
    return {
        "id": str(binding.id),
        "compliance_item_id": str(binding.compliance_item_id),
        "enterprise_material_id": str(binding.enterprise_material_id),
        "material_name": binding.material_snapshot.get("name"),
        "evidence_text": binding.evidence_text,
        "confidence_score": str(binding.confidence_score) if binding.confidence_score is not None else None,
        "bind_reason": binding.bind_reason,
        "status": binding.status,
        "created_by": str(binding.created_by),
        "created_at": binding.created_at.isoformat() if binding.created_at else None,
        "deleted_by": str(binding.deleted_by) if binding.deleted_by else None,
        "deleted_at": binding.deleted_at.isoformat() if binding.deleted_at else None,
    }


def evidence_binding_read_from_binding(binding: ComplianceEvidenceBinding) -> ComplianceEvidenceBindingRead:
    snapshot = binding.material_snapshot or {}
    return ComplianceEvidenceBindingRead(
        id=binding.id,
        project_id=binding.project_id,
        section_id=binding.section_id,
        compliance_item_id=binding.compliance_item_id,
        enterprise_material_id=binding.enterprise_material_id,
        material_name=snapshot.get("name"),
        material_type=snapshot.get("material_type"),
        material_verification_status=snapshot.get("verification_status"),
        evidence_text=binding.evidence_text,
        confidence_score=binding.confidence_score,
        bind_reason=binding.bind_reason,
        status=binding.status,
        created_by=binding.created_by,
        created_at=binding.created_at,
        deleted_by=binding.deleted_by,
        deleted_at=binding.deleted_at,
    )


def enterprise_evidence_summary_for_item(
    db: Session,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
) -> tuple[int, str | None]:
    bindings = db.scalars(
        select(ComplianceEvidenceBinding)
        .where(
            ComplianceEvidenceBinding.tenant_id == tenant_id,
            ComplianceEvidenceBinding.compliance_item_id == item_id,
            ComplianceEvidenceBinding.status == "active",
        )
        .order_by(ComplianceEvidenceBinding.created_at.desc())
    ).all()
    names = [
        str(binding.material_snapshot.get("name") or binding.evidence_text)
        for binding in bindings
    ]
    if not names:
        return 0, None
    summary = "；".join(names[:2])
    if len(names) > 2:
        summary = f"{summary} 等 {len(names)} 项"
    return len(names), summary


def refresh_batch_confirm_guard(item: ComplianceItem) -> None:
    item.is_batch_confirm_allowed = (
        item.risk_level != "high" and not item.is_mandatory and item.status != "needs_material"
    )


def add_matrix_audit_log(
    db: Session,
    ctx: RequestContext,
    *,
    project_id: uuid.UUID,
    section_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID | None,
    before_json: dict | None,
    after_json: dict | None,
    reason: str,
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
            severity=severity,
        )
    )


def compliance_item_read_from_item(db: Session, item: ComplianceItem) -> ComplianceItemRead:
    document = db.get(Document, item.source_document_id)
    version = db.get(DocumentVersion, item.source_version_id)
    source_chunk = db.get(DocumentChunk, item.source_chunk_id) if item.source_chunk_id else None
    owner_name = None
    if item.owner_user_id is not None:
        owner_name = db.scalar(select(User.name).where(User.id == item.owner_user_id))
    evidence_count, evidence_summary = enterprise_evidence_summary_for_item(
        db,
        item.tenant_id,
        item.id,
    )
    return ComplianceItemRead(
        id=item.id,
        project_id=item.project_id,
        section_id=item.section_id,
        source_document_id=item.source_document_id,
        source_document_title=document.title if document else None,
        source_version_id=item.source_version_id,
        source_version_label=version.version_label if version else None,
        source_chunk_id=item.source_chunk_id,
        source_page_no=item.source_page_no,
        source_heading_path=source_chunk.heading_path if source_chunk else None,
        source_chunk_index=source_chunk.chunk_index if source_chunk else None,
        source_content_text=source_chunk.content_text if source_chunk else None,
        source_bbox_json=source_chunk.bbox_json if source_chunk else None,
        source_table_json=source_chunk.table_json if source_chunk else None,
        item_type=item.item_type,
        requirement_text=item.requirement_text,
        normalized_requirement=item.normalized_requirement,
        response_suggestion=item.response_suggestion,
        evidence_text=item.evidence_text,
        rule_explanation=item.explanation_json,
        enterprise_evidence_count=evidence_count,
        enterprise_evidence_summary=evidence_summary,
        status=item.status,
        risk_level=item.risk_level,
        is_mandatory=item.is_mandatory,
        is_batch_confirm_allowed=item.is_batch_confirm_allowed,
        owner_user_id=item.owner_user_id,
        owner_name=owner_name,
        confidence_score=item.confidence_score,
        confirmed_by=item.confirmed_by,
        confirmed_at=item.confirmed_at,
        modified_by=item.modified_by,
        modified_at=item.modified_at,
        modify_reason=item.modify_reason,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def project_counts_subqueries(tenant_id: uuid.UUID):
    section_counts = (
        select(
            BidSection.project_id.label("project_id"),
            func.count(BidSection.id).label("section_count"),
        )
        .where(BidSection.tenant_id == tenant_id)
        .group_by(BidSection.project_id)
        .subquery()
    )
    compliance_counts = (
        select(
            ComplianceItem.project_id.label("project_id"),
            func.count(ComplianceItem.id).label("compliance_item_count"),
            func.count(ComplianceItem.id)
            .filter(ComplianceItem.risk_level == "high")
            .label("high_risk_count"),
            func.count(ComplianceItem.id)
            .filter(ComplianceItem.status == "pending_confirm")
            .label("pending_confirm_count"),
        )
        .where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .group_by(ComplianceItem.project_id)
        .subquery()
    )
    return section_counts, compliance_counts


def project_summary_from_row(row) -> ProjectSummary:
    project = row[0]
    return ProjectSummary(
        id=project.id,
        name=project.name,
        purchaser=project.purchaser,
        agency=project.agency,
        budget_amount=project.budget_amount,
        region_code=project.region_code,
        industry_code=project.industry_code,
        status=project.status,
        bid_deadline_at=project.bid_deadline_at,
        section_count=row.section_count,
        compliance_item_count=row.compliance_item_count,
        high_risk_count=row.high_risk_count,
        pending_confirm_count=row.pending_confirm_count,
    )


def export_file_read(export_file: ExportFile) -> ExportFileRead:
    return ExportFileRead.model_validate(export_file)


def business_draft_chapter_read(db: Session, chapter: BusinessDraftChapter) -> BusinessDraftChapterRead:
    evidence_refs = db.scalars(
        select(BusinessDraftEvidenceRef)
        .where(
            BusinessDraftEvidenceRef.tenant_id == chapter.tenant_id,
            BusinessDraftEvidenceRef.chapter_id == chapter.id,
        )
        .order_by(BusinessDraftEvidenceRef.created_at.asc())
    ).all()
    fact_checks = db.scalars(
        select(DraftFactCheck)
        .where(
            DraftFactCheck.tenant_id == chapter.tenant_id,
            DraftFactCheck.chapter_id == chapter.id,
        )
        .order_by(DraftFactCheck.created_at.asc())
    ).all()
    payload = BusinessDraftChapterRead.model_validate(chapter)
    payload.evidence_refs = [BusinessDraftEvidenceRefRead.model_validate(ref) for ref in evidence_refs]
    payload.fact_checks = [DraftFactCheckRead.model_validate(check) for check in fact_checks]
    return payload


def project_import_draft_read(draft: ImportDraft) -> ProjectImportDraftRead:
    return ProjectImportDraftRead(
        source=ProjectImportSourceRead(**draft.source.__dict__),
        project=ProjectImportProjectDraft(**draft.project.__dict__),
        sections=[ProjectImportSectionDraft(**section.__dict__) for section in draft.sections],
        confidence=draft.confidence,
        warnings=draft.warnings,
        preview_text=draft.preview_text,
    )


@router.get("", response_model=list[ProjectSummary])
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProjectSummary]:
    section_counts, compliance_counts = project_counts_subqueries(ctx.tenant_id)

    stmt = (
        select(
            Project,
            func.coalesce(section_counts.c.section_count, 0).label("section_count"),
            func.coalesce(compliance_counts.c.compliance_item_count, 0).label(
                "compliance_item_count"
            ),
            func.coalesce(compliance_counts.c.high_risk_count, 0).label("high_risk_count"),
            func.coalesce(compliance_counts.c.pending_confirm_count, 0).label(
                "pending_confirm_count"
            ),
        )
        .outerjoin(section_counts, section_counts.c.project_id == Project.id)
        .outerjoin(compliance_counts, compliance_counts.c.project_id == Project.id)
        .where(
            Project.tenant_id == ctx.tenant_id,
            Project.id.in_(visible_project_ids(ctx)),
        )
        .order_by(Project.updated_at.desc(), Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        stmt = stmt.where(Project.status == status_filter)
    else:
        stmt = stmt.where(Project.status != "archived")

    return [project_summary_from_row(row) for row in db.execute(stmt).all()]


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectDetail:
    project = Project(
        tenant_id=ctx.tenant_id,
        name=payload.name.strip(),
        purchaser=payload.purchaser,
        agency=payload.agency,
        budget_amount=payload.budget_amount,
        region_code=payload.region_code,
        industry_code=payload.industry_code,
        notice_url=payload.notice_url,
        status="pending_files",
        bid_deadline_at=payload.bid_deadline_at,
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
    section_name = payload.section_name or "一标段"
    db.add(
        BidSection(
            tenant_id=ctx.tenant_id,
            project_id=project.id,
            code=payload.section_code or "section-001",
            name=section_name.strip(),
            budget_amount=payload.section_budget_amount or payload.budget_amount,
            status="pending_files",
            bid_deadline_at=payload.bid_deadline_at,
            created_by=ctx.user_id,
        )
    )
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project.id,
        section_id=None,
        action="project.created",
        object_type="project",
        object_id=project.id,
        before_json=None,
        after_json={
            "name": project.name,
            "section_name": section_name,
            "notice_url": project.notice_url,
        },
        reason="用户手工创建项目和默认标段",
    )
    db.commit()
    return get_project(project.id, db, ctx)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> None:
    project = get_project_or_404(db, ctx, project_id)
    if project.status == "archived":
        return None

    before_json = {
        "status": project.status,
        "archived_at": project.archived_at.isoformat() if project.archived_at else None,
    }
    archived_at = datetime.now(UTC)
    project.status = "archived"
    project.archived_at = archived_at

    sections = db.scalars(
        select(BidSection).where(
            BidSection.tenant_id == ctx.tenant_id,
            BidSection.project_id == project.id,
        )
    ).all()
    for section in sections:
        section.status = "archived"

    add_matrix_audit_log(
        db,
        ctx,
        project_id=project.id,
        section_id=None,
        action="project.archived",
        object_type="project",
        object_id=project.id,
        before_json=before_json,
        after_json={
            "status": "archived",
            "archived_at": archived_at.isoformat(),
            "section_count": len(sections),
        },
        reason="用户删除项目，系统归档隐藏项目及标段",
    )
    db.commit()
    return None


@router.post(
    "/import-drafts/upload",
    response_model=ProjectImportDraftRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_import_draft_from_upload(
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    file: Annotated[UploadFile, File()],
) -> ProjectImportDraftRead:
    payload = await file.read(MAX_FILE_BYTES + 1)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(payload) > MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large")
    draft = build_upload_import_draft(
        ctx=ctx,
        filename=file.filename or "import-document.bin",
        content_type=file.content_type,
        data=payload,
    )
    return project_import_draft_read(draft)


@router.post(
    "/import-drafts/public-url",
    response_model=ProjectImportDraftRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_import_draft_from_public_url(
    payload: ProjectImportUrlRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectImportDraftRead:
    try:
        draft = build_url_import_draft(
            ctx=ctx,
            source_url=payload.source_url,
            source_site=payload.source_site,
            title=payload.title,
        )
    except FileAcquisitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return project_import_draft_read(draft)


@router.post(
    "/import-drafts/confirm",
    response_model=ProjectImportConfirmRead,
    status_code=status.HTTP_201_CREATED,
)
def confirm_project_import(
    payload: ProjectImportConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectImportConfirmRead:
    try:
        result = confirm_import_draft(
            db,
            ctx=ctx,
            project_payload=payload.project.model_dump(),
            sections_payload=[section.model_dump() for section in payload.sections],
            source_payload=payload.source.model_dump(mode="json"),
            auto_parse=payload.auto_parse,
            auto_generate_matrix=payload.auto_generate_matrix,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProjectImportConfirmRead(
        project=get_project(result.project_id, db, ctx),
        section_id=result.section_id,
        document_id=result.document_id,
        parse_task_id=result.parse_task_id,
        matrix_task_id=result.matrix_task_id,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectDetail:
    section_counts, compliance_counts = project_counts_subqueries(ctx.tenant_id)
    stmt = (
        select(
            Project,
            func.coalesce(section_counts.c.section_count, 0).label("section_count"),
            func.coalesce(compliance_counts.c.compliance_item_count, 0).label(
                "compliance_item_count"
            ),
            func.coalesce(compliance_counts.c.high_risk_count, 0).label("high_risk_count"),
            func.coalesce(compliance_counts.c.pending_confirm_count, 0).label(
                "pending_confirm_count"
            ),
        )
        .outerjoin(section_counts, section_counts.c.project_id == Project.id)
        .outerjoin(compliance_counts, compliance_counts.c.project_id == Project.id)
        .where(
            Project.tenant_id == ctx.tenant_id,
            Project.id == project_id,
            Project.id.in_(visible_project_ids(ctx)),
        )
    )
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not authorized",
        )

    summary = project_summary_from_row(row)
    project = row[0]
    return ProjectDetail(
        **summary.model_dump(),
        notice_url=project.notice_url,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archived_at=project.archived_at,
    )


@router.get("/{project_id}/sections", response_model=list[SectionSummary])
def list_sections(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[SectionSummary]:
    get_project_or_404(db, ctx, project_id)

    document_counts = (
        select(
            Document.section_id.label("section_id"),
            func.count(Document.id).label("document_count"),
        )
        .where(
            Document.tenant_id == ctx.tenant_id,
            Document.project_id == project_id,
            Document.status != "deleted",
        )
        .group_by(Document.section_id)
        .subquery()
    )
    compliance_counts = (
        select(
            ComplianceItem.section_id.label("section_id"),
            func.count(ComplianceItem.id).label("compliance_item_count"),
            func.count(ComplianceItem.id)
            .filter(ComplianceItem.risk_level == "high")
            .label("high_risk_count"),
            func.count(ComplianceItem.id)
            .filter(ComplianceItem.status == "pending_confirm")
            .label("pending_confirm_count"),
        )
        .where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .group_by(ComplianceItem.section_id)
        .subquery()
    )

    stmt = (
        select(
            BidSection,
            func.coalesce(document_counts.c.document_count, 0).label("document_count"),
            func.coalesce(compliance_counts.c.compliance_item_count, 0).label(
                "compliance_item_count"
            ),
            func.coalesce(compliance_counts.c.high_risk_count, 0).label("high_risk_count"),
            func.coalesce(compliance_counts.c.pending_confirm_count, 0).label(
                "pending_confirm_count"
            ),
        )
        .outerjoin(document_counts, document_counts.c.section_id == BidSection.id)
        .outerjoin(compliance_counts, compliance_counts.c.section_id == BidSection.id)
        .where(
            BidSection.tenant_id == ctx.tenant_id,
            BidSection.project_id == project_id,
        )
        .order_by(BidSection.code.asc().nulls_last(), BidSection.created_at.asc())
    )

    items: list[SectionSummary] = []
    for section, document_count, compliance_item_count, high_risk_count, pending_count in db.execute(
        stmt
    ).all():
        items.append(
            SectionSummary(
                id=section.id,
                project_id=section.project_id,
                code=section.code,
                name=section.name,
                budget_amount=section.budget_amount,
                status=section.status,
                bid_deadline_at=section.bid_deadline_at,
                document_count=document_count,
                compliance_item_count=compliance_item_count,
                high_risk_count=high_risk_count,
                pending_confirm_count=pending_count,
                created_at=section.created_at,
                updated_at=section.updated_at,
            )
        )
    return items


@router.post("/{project_id}/sections", response_model=SectionSummary, status_code=status.HTTP_201_CREATED)
def create_section(
    project_id: uuid.UUID,
    payload: SectionCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> SectionSummary:
    project = get_project_or_404(db, ctx, project_id)
    section = BidSection(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        code=payload.code,
        name=payload.name.strip(),
        budget_amount=payload.budget_amount,
        status="pending_files",
        bid_deadline_at=payload.bid_deadline_at or project.bid_deadline_at,
        created_by=ctx.user_id,
    )
    db.add(section)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section.id,
        action="section.created",
        object_type="bid_section",
        object_id=section.id,
        before_json=None,
        after_json={
            "name": section.name,
            "code": section.code,
            "bid_deadline_at": section.bid_deadline_at.isoformat()
            if section.bid_deadline_at
            else None,
        },
        reason="用户手工创建标段",
    )
    db.commit()
    db.refresh(section)
    return SectionSummary(
        id=section.id,
        project_id=section.project_id,
        code=section.code,
        name=section.name,
        budget_amount=section.budget_amount,
        status=section.status,
        bid_deadline_at=section.bid_deadline_at,
        document_count=0,
        compliance_item_count=0,
        high_risk_count=0,
        pending_confirm_count=0,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/generate",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_compliance_matrix_generation_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceMatrixGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AsyncTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    idempotency_payload = {
        "section_id": str(section_id),
        "document_id": str(payload.document_id) if payload.document_id else None,
        "document_version_id": str(payload.document_version_id)
        if payload.document_version_id
        else None,
        "force": payload.force,
    }
    idempotency_seed = uuid.uuid4().hex if payload.force else str(idempotency_payload)
    idempotency_key = "matrix-generate:" + hashlib.sha256(
        idempotency_seed.encode("utf-8")
    ).hexdigest()

    existing_task = db.scalar(
        select(AsyncTask).where(
            AsyncTask.tenant_id == ctx.tenant_id,
            AsyncTask.task_type == "matrix_generate",
            AsyncTask.idempotency_key == idempotency_key,
        )
    )
    if existing_task is not None:
        return AsyncTaskRead.model_validate(existing_task)

    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="matrix_generate",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json=idempotency_payload,
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            actor_type="user",
            action="compliance.matrix_generate_requested",
            object_type="async_task",
            object_id=task.id,
            after_json=task.input_json,
            reason="用户请求生成合规矩阵候选项",
            severity="info",
        )
    )
    db.commit()
    db.refresh(task)

    if settings.run_tasks_inline:
        execute_compliance_matrix_generation_task(db, task.id)
        db.refresh(task)
    else:
        try:
            from app.worker import run_compliance_matrix_generation_task

            run_compliance_matrix_generation_task.delay(str(task.id))
        except Exception:
            pass
    return AsyncTaskRead.model_validate(task)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/export-excel",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_compliance_matrix_excel_export_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceMatrixExportRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AsyncTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    filter_payload = payload.model_dump(mode="json", exclude_none=True)
    idempotency_key = "excel-export:" + hashlib.sha256(
        f"{section_id}:{filter_payload}:{uuid.uuid4().hex}".encode("utf-8")
    ).hexdigest()
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="excel_export",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json=filter_payload,
        retry_count=0,
        max_retries=3,
        created_by=ctx.user_id,
    )
    db.add(task)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="export.excel_requested",
        object_type="async_task",
        object_id=task.id,
        before_json=None,
        after_json=filter_payload,
        reason="用户请求导出合规矩阵快照用于归档或外部协作",
    )
    db.commit()
    db.refresh(task)

    if settings.run_tasks_inline:
        execute_compliance_matrix_excel_export_task(db, task.id)
        db.refresh(task)
    else:
        try:
            from app.worker import run_compliance_matrix_excel_export_task

            run_compliance_matrix_excel_export_task.delay(str(task.id))
        except Exception:
            pass
    return AsyncTaskRead.model_validate(task)


@router.get(
    "/{project_id}/sections/{section_id}/export-files",
    response_model=list[ExportFileRead],
)
def list_export_files(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[ExportFileRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    export_files = db.scalars(
        select(ExportFile)
        .where(
            ExportFile.tenant_id == ctx.tenant_id,
            ExportFile.project_id == project_id,
            ExportFile.section_id == section_id,
            ExportFile.status != "deleted",
        )
        .order_by(ExportFile.created_at.desc())
        .limit(20)
    ).all()
    return [export_file_read(item) for item in export_files]


@router.get("/{project_id}/export-files/{export_file_id}/download")
def download_export_file(
    project_id: uuid.UUID,
    export_file_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> StreamingResponse:
    get_project_or_404(db, ctx, project_id)
    export_file = db.scalar(
        select(ExportFile).where(
            ExportFile.tenant_id == ctx.tenant_id,
            ExportFile.project_id == project_id,
            ExportFile.id == export_file_id,
            ExportFile.status == "available",
        )
    )
    if export_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
    data = get_object_bytes(bucket=export_file.bucket, object_key=export_file.object_key)
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if export_file.export_type == "business_draft_word"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=export_file.section_id,
        action="export.file_downloaded",
        object_type="export_file",
        object_id=export_file.id,
        before_json=None,
        after_json={"file_name": export_file.file_name, "sha256": export_file.sha256},
        reason="用户下载导出文件",
    )
    db.commit()
    return StreamingResponse(
        iter([data]),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(export_file.file_name)}"
        },
    )


@router.get("/{project_id}/export-files/{export_file_id}", response_model=ExportFileRead)
def get_export_file(
    project_id: uuid.UUID,
    export_file_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ExportFileRead:
    get_project_or_404(db, ctx, project_id)
    export_file = db.scalar(
        select(ExportFile).where(
            ExportFile.tenant_id == ctx.tenant_id,
            ExportFile.project_id == project_id,
            ExportFile.id == export_file_id,
            ExportFile.status != "deleted",
        )
    )
    if export_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
    return export_file_read(export_file)


@router.get(
    "/{project_id}/sections/{section_id}/qualification-evaluations",
    response_model=list[QualificationEvaluationRead],
)
def list_qualification_evaluations(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[QualificationEvaluationRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    evaluations = db.scalars(
        select(QualificationEvaluation)
        .where(
            QualificationEvaluation.tenant_id == ctx.tenant_id,
            QualificationEvaluation.project_id == project_id,
            QualificationEvaluation.section_id == section_id,
        )
        .order_by(QualificationEvaluation.risk_level.desc(), QualificationEvaluation.created_at.asc())
    ).all()
    return [QualificationEvaluationRead.model_validate(item) for item in evaluations]


@router.post(
    "/{project_id}/sections/{section_id}/qualification-evaluations/run",
    response_model=list[QualificationEvaluationRead],
)
def run_section_qualification_evaluation(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[QualificationEvaluationRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    evaluations = run_qualification_evaluation(
        db,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=ctx.user_id,
    )
    db.commit()
    return [QualificationEvaluationRead.model_validate(item) for item in evaluations]


@router.post(
    "/{project_id}/sections/{section_id}/qualification-evaluations/{evaluation_id}/confirm",
    response_model=QualificationEvaluationRead,
)
def confirm_qualification_evaluation(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    payload: QualificationEvaluationConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> QualificationEvaluationRead:
    get_section_or_404(db, ctx, project_id, section_id)
    evaluation = db.scalar(
        select(QualificationEvaluation).where(
            QualificationEvaluation.tenant_id == ctx.tenant_id,
            QualificationEvaluation.project_id == project_id,
            QualificationEvaluation.section_id == section_id,
            QualificationEvaluation.id == evaluation_id,
        )
    )
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qualification evaluation not found",
        )
    before = evaluation_snapshot(evaluation)
    evaluation.confirmed_by = ctx.user_id
    evaluation.confirmed_at = datetime.now(UTC)
    evaluation.confirm_reason = payload.reason
    evaluation.updated_by = ctx.user_id
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="qualification.evaluation_confirmed",
        object_type="qualification_evaluation",
        object_id=evaluation.id,
        before_json=before,
        after_json=evaluation_snapshot(evaluation),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(evaluation)
    return QualificationEvaluationRead.model_validate(evaluation)


def _build_qualification_decision(
    evaluations: list[QualificationEvaluation],
    *,
    project: Project,
    section: BidSection,
    profile: EnterpriseProfile | None,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> QualificationDecision:
    satisfied_count = sum(1 for item in evaluations if item.evaluation_status == "satisfied")
    blocking = [item for item in evaluations if item.is_blocking]
    missing = [item for item in evaluations if item.evaluation_status == "needs_material"]
    pending = [item for item in evaluations if item.evaluation_status == "pending_confirm"]
    profile_policy = _evaluate_profile_policy(project, section, profile)
    profile_blocking = profile_policy["forbidden_matches"]
    profile_pending = profile_policy["preference_mismatches"]
    if blocking or profile_blocking:
        recommendation = "no_go"
        summary = (
            f"存在 {len(blocking) + len(profile_blocking)} 项阻断性资格风险，"
            "建议暂不参标，待补齐或人工确认后再决策。"
        )
    elif missing or pending or profile_pending:
        recommendation = "conditional_go"
        summary = (
            f"存在 {len(missing)} 项缺材料、{len(pending) + len(profile_pending)} 项待确认，"
            "建议有条件参标并先完成补证。"
        )
    else:
        recommendation = "go"
        summary = "当前资格预评估未发现阻断项，可进入商务标草稿和参标审批。"
    return QualificationDecision(
        tenant_id=tenant_id,
        project_id=project_id,
        section_id=section_id,
        recommendation=recommendation,
        status="draft",
        summary=summary,
        satisfied_count=satisfied_count,
        blocking_count=len(blocking) + len(profile_blocking),
        missing_count=len(missing),
        pending_count=len(pending) + len(profile_pending),
        reasons_json={
            "blocking": [evaluation_snapshot(item) for item in blocking[:10]],
            "missing": [evaluation_snapshot(item) for item in missing[:10]],
            "pending": [evaluation_snapshot(item) for item in pending[:10]],
            "profile_policy": profile_policy,
        },
        created_by=actor_user_id,
    )


def _norm_policy_text(value: object) -> str:
    return str(value or "").strip().lower()


def _project_policy_fields(project: Project, section: BidSection) -> list[str]:
    return [
        _norm_policy_text(project.name),
        _norm_policy_text(project.purchaser),
        _norm_policy_text(project.agency),
        _norm_policy_text(project.region_code),
        _norm_policy_text(project.industry_code),
        _norm_policy_text(section.code),
        _norm_policy_text(section.name),
    ]


def _profile_list(value: list[str] | None) -> list[str]:
    return [item.strip() for item in value or [] if item and item.strip()]


def _evaluate_profile_policy(
    project: Project,
    section: BidSection,
    profile: EnterpriseProfile | None,
) -> dict[str, object]:
    context_fields = [field for field in _project_policy_fields(project, section) if field]
    context_text = " ".join(context_fields)
    region_preferences = _profile_list(profile.region_preferences if profile else None)
    industry_preferences = _profile_list(profile.industry_preferences if profile else None)
    forbidden_rules = _profile_list(profile.forbidden_rules if profile else None)

    forbidden_matches = []
    for rule in forbidden_rules:
        normalized_rule = _norm_policy_text(rule)
        if not normalized_rule:
            continue
        matched_terms = [
            field for field in context_fields if len(field) >= 2 and field in normalized_rule
        ]
        if normalized_rule in context_text or matched_terms:
            forbidden_matches.append(
                {
                    "rule": rule,
                    "matched_terms": matched_terms or [rule],
                    "severity": "blocking",
                    "reason": "企业禁投规则命中当前项目上下文，需要人工确认后再参标。",
                }
            )

    preference_mismatches = []
    if region_preferences and not any(_norm_policy_text(item) in context_text for item in region_preferences):
        preference_mismatches.append(
            {
                "type": "region",
                "preferences": region_preferences,
                "severity": "pending_confirm",
                "reason": "项目地区未命中企业地域偏好，需要确认是否例外参标。",
            }
        )
    if industry_preferences and not any(_norm_policy_text(item) in context_text for item in industry_preferences):
        preference_mismatches.append(
            {
                "type": "industry",
                "preferences": industry_preferences,
                "severity": "pending_confirm",
                "reason": "项目行业未命中企业行业偏好，需要确认是否例外参标。",
            }
        )
    return {
        "context": {
            "project_name": project.name,
            "purchaser": project.purchaser,
            "agency": project.agency,
            "region_code": project.region_code,
            "industry_code": project.industry_code,
            "section_name": section.name,
        },
        "forbidden_matches": forbidden_matches,
        "preference_mismatches": preference_mismatches,
    }


@router.get(
    "/{project_id}/sections/{section_id}/qualification-decision",
    response_model=QualificationDecisionRead | None,
)
def get_qualification_decision(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> QualificationDecisionRead | None:
    get_section_or_404(db, ctx, project_id, section_id)
    decision = db.scalar(
        select(QualificationDecision)
        .where(
            QualificationDecision.tenant_id == ctx.tenant_id,
            QualificationDecision.project_id == project_id,
            QualificationDecision.section_id == section_id,
            QualificationDecision.status != "superseded",
        )
        .order_by(QualificationDecision.created_at.desc())
    )
    return QualificationDecisionRead.model_validate(decision) if decision else None


@router.post(
    "/{project_id}/sections/{section_id}/qualification-decision/generate",
    response_model=QualificationDecisionRead,
)
def generate_qualification_decision(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> QualificationDecisionRead:
    get_section_or_404(db, ctx, project_id, section_id)
    project = get_project_or_404(db, ctx, project_id)
    section = get_section_or_404(db, ctx, project_id, section_id)
    profile = db.scalar(select(EnterpriseProfile).where(EnterpriseProfile.tenant_id == ctx.tenant_id))
    evaluations = db.scalars(
        select(QualificationEvaluation).where(
            QualificationEvaluation.tenant_id == ctx.tenant_id,
            QualificationEvaluation.project_id == project_id,
            QualificationEvaluation.section_id == section_id,
        )
    ).all()
    if not evaluations:
        evaluations = run_qualification_evaluation(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
        )

    existing = db.scalars(
        select(QualificationDecision).where(
            QualificationDecision.tenant_id == ctx.tenant_id,
            QualificationDecision.project_id == project_id,
            QualificationDecision.section_id == section_id,
            QualificationDecision.status != "superseded",
        )
    ).all()
    for item in existing:
        item.status = "superseded"
    decision = _build_qualification_decision(
        evaluations,
        project=project,
        section=section,
        profile=profile,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=ctx.user_id,
    )
    db.add(decision)
    db.flush()
    db.add(
        ApprovalTask(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            task_type="qualification_decision",
            title="确认参标资格评估建议",
            description=decision.summary,
            status="pending",
            related_object_type="qualification_decision",
            related_object_id=decision.id,
            assignee_user_id=ctx.user_id,
            evidence_snapshot_json=decision.reasons_json,
            created_by=ctx.user_id,
        )
    )
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="qualification.decision_generated",
        object_type="qualification_decision",
        object_id=decision.id,
        before_json=None,
        after_json=QualificationDecisionRead.model_validate(decision).model_dump(mode="json"),
        reason="生成 Go/No-Go 参标资格建议",
    )
    db.commit()
    db.refresh(decision)
    return QualificationDecisionRead.model_validate(decision)


@router.post(
    "/{project_id}/sections/{section_id}/qualification-decision/{decision_id}/confirm",
    response_model=QualificationDecisionRead,
)
def confirm_qualification_decision(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    decision_id: uuid.UUID,
    payload: QualificationDecisionConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> QualificationDecisionRead:
    get_section_or_404(db, ctx, project_id, section_id)
    decision = db.scalar(
        select(QualificationDecision).where(
            QualificationDecision.tenant_id == ctx.tenant_id,
            QualificationDecision.project_id == project_id,
            QualificationDecision.section_id == section_id,
            QualificationDecision.id == decision_id,
        )
    )
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    before = QualificationDecisionRead.model_validate(decision).model_dump(mode="json")
    decision.status = "confirmed"
    decision.confirmed_by = ctx.user_id
    decision.confirmed_at = datetime.now(UTC)
    decision.confirm_reason = payload.reason.strip()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="qualification.decision_confirmed",
        object_type="qualification_decision",
        object_id=decision.id,
        before_json=before,
        after_json=QualificationDecisionRead.model_validate(decision).model_dump(mode="json"),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(decision)
    return QualificationDecisionRead.model_validate(decision)


@router.get(
    "/{project_id}/sections/{section_id}/business-draft/chapters",
    response_model=list[BusinessDraftChapterRead],
)
def list_business_draft_chapters(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[BusinessDraftChapterRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    chapters = db.scalars(
        select(BusinessDraftChapter)
        .where(
            BusinessDraftChapter.tenant_id == ctx.tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.status != "superseded",
        )
        .order_by(BusinessDraftChapter.sort_order.asc(), BusinessDraftChapter.created_at.asc())
    ).all()
    return [business_draft_chapter_read(db, chapter) for chapter in chapters]


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/chapters/generate",
    response_model=list[BusinessDraftChapterRead],
)
def generate_business_draft(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: BusinessDraftGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[BusinessDraftChapterRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        chapters = generate_business_draft_chapters(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    for chapter in chapters:
        db.add(
            ApprovalTask(
                tenant_id=ctx.tenant_id,
                project_id=project_id,
                section_id=section_id,
                task_type="draft_chapter",
                title=f"复核商务标章节：{chapter.title}",
                description="章节草稿由系统生成，需人工复核事实和引用证据。",
                status="pending",
                related_object_type="business_draft_chapter",
                related_object_id=chapter.id,
                assignee_user_id=ctx.user_id,
                evidence_snapshot_json=chapter.evidence_summary_json,
                created_by=ctx.user_id,
            )
        )
    db.commit()
    return [business_draft_chapter_read(db, chapter) for chapter in chapters]


@router.patch(
    "/{project_id}/sections/{section_id}/business-draft/chapters/{chapter_id}",
    response_model=BusinessDraftChapterRead,
)
def update_business_draft_chapter(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    chapter_id: uuid.UUID,
    payload: BusinessDraftChapterUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> BusinessDraftChapterRead:
    get_section_or_404(db, ctx, project_id, section_id)
    chapter = db.scalar(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == ctx.tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.id == chapter_id,
            BusinessDraftChapter.status != "superseded",
        )
    )
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft chapter not found")
    before = business_draft_chapter_read(db, chapter).model_dump(mode="json")
    chapter.content_text = payload.content_text
    chapter.version_no += 1
    chapter.updated_by = ctx.user_id
    chapter.edit_reason = payload.reason.strip()
    chapter.status = "pending_review"
    project = get_project_or_404(db, ctx, project_id)
    run_fact_checks(db, chapter=chapter, project=project, actor_user_id=ctx.user_id)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="business_draft.chapter_updated",
        object_type="business_draft_chapter",
        object_id=chapter.id,
        before_json=before,
        after_json=business_draft_chapter_read(db, chapter).model_dump(mode="json"),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(chapter)
    return business_draft_chapter_read(db, chapter)


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/chapters/{chapter_id}/fact-checks/run",
    response_model=BusinessDraftChapterRead,
)
def rerun_business_draft_fact_checks(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    chapter_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> BusinessDraftChapterRead:
    project = get_project_or_404(db, ctx, project_id)
    get_section_or_404(db, ctx, project_id, section_id)
    chapter = db.scalar(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == ctx.tenant_id,
            BusinessDraftChapter.project_id == project_id,
            BusinessDraftChapter.section_id == section_id,
            BusinessDraftChapter.id == chapter_id,
            BusinessDraftChapter.status != "superseded",
        )
    )
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft chapter not found")
    run_fact_checks(db, chapter=chapter, project=project, actor_user_id=ctx.user_id)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="business_draft.fact_checked",
        object_type="business_draft_chapter",
        object_id=chapter.id,
        before_json=None,
        after_json={"fact_check_status": chapter.fact_check_status},
        reason="重新执行商务标章节事实性校验",
    )
    db.commit()
    return business_draft_chapter_read(db, chapter)


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/export-word",
    response_model=ExportFileRead,
)
def export_business_draft_word_file(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ExportFileRead:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        export_file = export_business_draft_word(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(export_file)
    return export_file_read(export_file)


@router.get(
    "/{project_id}/sections/{section_id}/approval-tasks",
    response_model=list[ApprovalTaskRead],
)
def list_approval_tasks(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[ApprovalTaskRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    stmt = (
        select(ApprovalTask)
        .where(
            ApprovalTask.tenant_id == ctx.tenant_id,
            ApprovalTask.project_id == project_id,
            ApprovalTask.section_id == section_id,
        )
        .order_by(ApprovalTask.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(ApprovalTask.status == status_filter)
    return [ApprovalTaskRead.model_validate(item) for item in db.scalars(stmt).all()]


@router.post(
    "/{project_id}/sections/{section_id}/approval-tasks",
    response_model=ApprovalTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_approval_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ApprovalTaskCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ApprovalTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    task = ApprovalTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type=payload.task_type,
        title=payload.title,
        description=payload.description,
        status="pending",
        related_object_type=payload.related_object_type,
        related_object_id=payload.related_object_id,
        assignee_user_id=payload.assignee_user_id or ctx.user_id,
        evidence_snapshot_json=None,
        created_by=ctx.user_id,
        due_at=payload.due_at,
    )
    db.add(task)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="approval.task_created",
        object_type="approval_task",
        object_id=task.id,
        before_json=None,
        after_json=ApprovalTaskRead.model_validate(task).model_dump(mode="json"),
        reason="创建审批任务",
    )
    db.commit()
    db.refresh(task)
    return ApprovalTaskRead.model_validate(task)


@router.post(
    "/{project_id}/sections/{section_id}/approval-tasks/{approval_task_id}/decision",
    response_model=ApprovalTaskRead,
)
def decide_approval_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    approval_task_id: uuid.UUID,
    payload: ApprovalTaskDecisionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ApprovalTaskRead:
    get_section_or_404(db, ctx, project_id, section_id)
    task = db.scalar(
        select(ApprovalTask).where(
            ApprovalTask.tenant_id == ctx.tenant_id,
            ApprovalTask.project_id == project_id,
            ApprovalTask.section_id == section_id,
            ApprovalTask.id == approval_task_id,
            ApprovalTask.status == "pending",
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending approval task not found")
    before = ApprovalTaskRead.model_validate(task).model_dump(mode="json")
    task.status = "approved" if payload.action == "approve" else "rejected"
    task.decision_reason = payload.reason.strip()
    task.decided_by = ctx.user_id
    task.decided_at = datetime.now(UTC)

    if task.related_object_type == "business_draft_chapter" and task.related_object_id:
        chapter = db.get(BusinessDraftChapter, task.related_object_id)
        if chapter and chapter.tenant_id == ctx.tenant_id:
            chapter.status = "approved" if task.status == "approved" else "rejected"
            chapter.approved_by = ctx.user_id if task.status == "approved" else None
            chapter.approved_at = task.decided_at if task.status == "approved" else None
    if task.related_object_type == "qualification_decision" and task.related_object_id:
        decision = db.get(QualificationDecision, task.related_object_id)
        if decision and decision.tenant_id == ctx.tenant_id and task.status == "approved":
            decision.status = "confirmed"
            decision.confirmed_by = ctx.user_id
            decision.confirmed_at = task.decided_at
            decision.confirm_reason = payload.reason.strip()

    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action=f"approval.task_{task.status}",
        object_type="approval_task",
        object_id=task.id,
        before_json=before,
        after_json=ApprovalTaskRead.model_validate(task).model_dump(mode="json"),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(task)
    return ApprovalTaskRead.model_validate(task)


@router.get(
    "/{project_id}/sections/{section_id}/compliance-items",
    response_model=list[ComplianceItemRead],
)
def list_compliance_items(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    risk_level: str | None = None,
    owner_user_id: uuid.UUID | None = None,
    item_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ComplianceItemRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    owner = aliased(User)

    stmt = (
        select(
            ComplianceItem,
            Document.title.label("source_document_title"),
            DocumentVersion.version_label.label("source_version_label"),
            owner.name.label("owner_name"),
            DocumentChunk,
        )
        .join(Document, Document.id == ComplianceItem.source_document_id)
        .join(DocumentVersion, DocumentVersion.id == ComplianceItem.source_version_id)
        .outerjoin(DocumentChunk, DocumentChunk.id == ComplianceItem.source_chunk_id)
        .outerjoin(owner, owner.id == ComplianceItem.owner_user_id)
        .where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(
            case(
                (ComplianceItem.risk_level == "high", 0),
                (ComplianceItem.risk_level == "medium", 1),
                (ComplianceItem.risk_level == "low", 2),
                else_=3,
            ),
            ComplianceItem.created_at.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        stmt = stmt.where(ComplianceItem.status == status_filter)
    if risk_level:
        stmt = stmt.where(ComplianceItem.risk_level == risk_level)
    if owner_user_id:
        stmt = stmt.where(ComplianceItem.owner_user_id == owner_user_id)
    if item_type:
        stmt = stmt.where(ComplianceItem.item_type == item_type)

    results: list[ComplianceItemRead] = []
    for item, source_document_title, source_version_label, owner_name, source_chunk in db.execute(stmt).all():
        evidence_count, evidence_summary = enterprise_evidence_summary_for_item(
            db,
            ctx.tenant_id,
            item.id,
        )
        results.append(
            ComplianceItemRead(
                id=item.id,
                project_id=item.project_id,
                section_id=item.section_id,
                source_document_id=item.source_document_id,
                source_document_title=source_document_title,
                source_version_id=item.source_version_id,
                source_version_label=source_version_label,
                source_chunk_id=item.source_chunk_id,
                source_page_no=item.source_page_no,
                source_heading_path=source_chunk.heading_path if source_chunk else None,
                source_chunk_index=source_chunk.chunk_index if source_chunk else None,
                source_content_text=source_chunk.content_text if source_chunk else None,
                source_bbox_json=source_chunk.bbox_json if source_chunk else None,
                source_table_json=source_chunk.table_json if source_chunk else None,
                item_type=item.item_type,
                requirement_text=item.requirement_text,
                normalized_requirement=item.normalized_requirement,
                response_suggestion=item.response_suggestion,
                evidence_text=item.evidence_text,
                rule_explanation=item.explanation_json,
                enterprise_evidence_count=evidence_count,
                enterprise_evidence_summary=evidence_summary,
                status=item.status,
                risk_level=item.risk_level,
                is_mandatory=item.is_mandatory,
                is_batch_confirm_allowed=item.is_batch_confirm_allowed,
                owner_user_id=item.owner_user_id,
                owner_name=owner_name,
                confidence_score=item.confidence_score,
                confirmed_by=item.confirmed_by,
                confirmed_at=item.confirmed_at,
                modified_by=item.modified_by,
                modified_at=item.modified_at,
                modify_reason=item.modify_reason,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return results


@router.patch(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}",
    response_model=ComplianceItemRead,
)
def update_compliance_item(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceItemUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceItemRead:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    fields_to_update = payload.model_fields_set - {"reason"}
    if not fields_to_update:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    before = compliance_item_snapshot(item)
    if "requirement_text" in fields_to_update:
        if payload.requirement_text is None or not payload.requirement_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="requirement_text cannot be empty",
            )
        item.requirement_text = payload.requirement_text.strip()
    if "response_suggestion" in fields_to_update:
        item.response_suggestion = (
            payload.response_suggestion.strip() if payload.response_suggestion else None
        )
    if "status" in fields_to_update and payload.status is not None:
        item.status = payload.status
    if "risk_level" in fields_to_update and payload.risk_level is not None:
        item.risk_level = payload.risk_level
    if "is_mandatory" in fields_to_update and payload.is_mandatory is not None:
        item.is_mandatory = payload.is_mandatory
    if "owner_user_id" in fields_to_update:
        if payload.owner_user_id is not None:
            get_active_user_or_404(db, ctx, payload.owner_user_id)
        item.owner_user_id = payload.owner_user_id

    refresh_batch_confirm_guard(item)
    item.modified_by = ctx.user_id
    item.modified_at = datetime.now(UTC)
    item.modify_reason = payload.reason.strip()
    after = compliance_item_snapshot(item)
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.item_updated",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json=after,
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    return compliance_item_read_from_item(db, item)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/confirm",
    response_model=ComplianceItemRead,
)
def confirm_compliance_item(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceItemConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceItemRead:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    if item.source_chunk_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot confirm item without source evidence",
        )

    before = compliance_item_snapshot(item)
    now = datetime.now(UTC)
    item.status = "confirmed"
    item.confirmed_by = ctx.user_id
    item.confirmed_at = now
    item.modified_by = ctx.user_id
    item.modified_at = now
    item.modify_reason = payload.reason.strip()
    refresh_batch_confirm_guard(item)
    after = compliance_item_snapshot(item)
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.item_confirmed",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json=after,
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    return compliance_item_read_from_item(db, item)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/assign",
    response_model=ComplianceItemRead,
)
def assign_compliance_item(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceItemAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceItemRead:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    owner_user_id = payload.owner_user_id or ctx.user_id
    get_active_user_or_404(db, ctx, owner_user_id)

    before = compliance_item_snapshot(item)
    item.owner_user_id = owner_user_id
    item.modified_by = ctx.user_id
    item.modified_at = datetime.now(UTC)
    item.modify_reason = payload.reason.strip()
    after = compliance_item_snapshot(item)
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.item_assigned",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json=after,
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    return compliance_item_read_from_item(db, item)


@router.get(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-bindings",
    response_model=list[ComplianceEvidenceBindingRead],
)
def list_compliance_evidence_bindings(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[ComplianceEvidenceBindingRead]:
    get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    bindings = db.scalars(
        select(ComplianceEvidenceBinding)
        .where(
            ComplianceEvidenceBinding.tenant_id == ctx.tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.compliance_item_id == item_id,
            ComplianceEvidenceBinding.status == "active",
        )
        .order_by(ComplianceEvidenceBinding.created_at.desc())
    ).all()
    return [evidence_binding_read_from_binding(binding) for binding in bindings]


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-bindings",
    response_model=ComplianceEvidenceBindingRead,
    status_code=status.HTTP_201_CREATED,
)
def bind_compliance_evidence(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceEvidenceBindRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceEvidenceBindingRead:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    material = db.scalar(
        select(EnterpriseMaterial).where(
            EnterpriseMaterial.tenant_id == ctx.tenant_id,
            EnterpriseMaterial.id == payload.enterprise_material_id,
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if material.verification_status in {"conflict", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict or expired material cannot be bound as evidence",
        )

    duplicate = db.scalar(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == ctx.tenant_id,
            ComplianceEvidenceBinding.compliance_item_id == item_id,
            ComplianceEvidenceBinding.enterprise_material_id == payload.enterprise_material_id,
            ComplianceEvidenceBinding.status == "active",
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material already bound")

    before = {
        "item": compliance_item_snapshot(item),
        "active_evidence_count": enterprise_evidence_summary_for_item(db, ctx.tenant_id, item.id)[0],
    }
    evidence_text = (
        payload.evidence_text.strip()
        if payload.evidence_text and payload.evidence_text.strip()
        else material.evidence_text or material.name
    )
    binding = ComplianceEvidenceBinding(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        compliance_item_id=item.id,
        enterprise_material_id=material.id,
        evidence_text=evidence_text,
        material_snapshot=enterprise_material_snapshot(material),
        confidence_score=payload.confidence_score or Decimal("0.7500"),
        bind_reason=payload.reason.strip(),
        status="active",
        created_by=ctx.user_id,
    )
    db.add(binding)

    if item.status == "needs_material":
        now = datetime.now(UTC)
        item.status = "pending_confirm"
        item.modified_by = ctx.user_id
        item.modified_at = now
        item.modify_reason = payload.reason.strip()
        refresh_batch_confirm_guard(item)

    db.flush()
    after = {
        "item": compliance_item_snapshot(item),
        "binding": evidence_binding_snapshot(binding),
        "material": enterprise_material_snapshot(material),
    }
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.evidence_bound",
        object_type="compliance_evidence_binding",
        object_id=binding.id,
        before_json=before,
        after_json=after,
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(binding)
    return evidence_binding_read_from_binding(binding)


@router.delete(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-bindings/{binding_id}",
    response_model=ComplianceEvidenceBindingRead,
)
def unbind_compliance_evidence(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: ComplianceEvidenceUnbindRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceEvidenceBindingRead:
    get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    binding = db.scalar(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == ctx.tenant_id,
            ComplianceEvidenceBinding.project_id == project_id,
            ComplianceEvidenceBinding.section_id == section_id,
            ComplianceEvidenceBinding.compliance_item_id == item_id,
            ComplianceEvidenceBinding.id == binding_id,
            ComplianceEvidenceBinding.status == "active",
        )
    )
    if binding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence binding not found")

    before = evidence_binding_snapshot(binding)
    binding.status = "deleted"
    binding.deleted_by = ctx.user_id
    binding.deleted_at = datetime.now(UTC)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.evidence_unbound",
        object_type="compliance_evidence_binding",
        object_id=binding.id,
        before_json=before,
        after_json=evidence_binding_snapshot(binding),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(binding)
    return evidence_binding_read_from_binding(binding)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/bulk-assign",
    response_model=list[ComplianceItemRead],
)
def bulk_assign_compliance_items(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceItemsBulkAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[ComplianceItemRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    owner_user_id = payload.owner_user_id or ctx.user_id
    get_active_user_or_404(db, ctx, owner_user_id)
    unique_item_ids = list(dict.fromkeys(payload.item_ids))
    items = db.scalars(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.id.in_(unique_item_ids),
            ComplianceItem.deleted_at.is_(None),
        )
    ).all()
    if len(items) != len(unique_item_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some compliance items were not found",
        )

    before_items = [compliance_item_snapshot(item) for item in items]
    now = datetime.now(UTC)
    for item in items:
        item.owner_user_id = owner_user_id
        item.modified_by = ctx.user_id
        item.modified_at = now
        item.modify_reason = payload.reason.strip()
    after_items = [compliance_item_snapshot(item) for item in items]
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.items_assigned",
        object_type="compliance_item_batch",
        object_id=None,
        before_json={"items": before_items},
        after_json={"items": after_items, "owner_user_id": str(owner_user_id)},
        reason=payload.reason.strip(),
    )
    db.commit()
    return [compliance_item_read_from_item(db, item) for item in items]


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/bulk-confirm",
    response_model=list[ComplianceItemRead],
)
def bulk_confirm_compliance_items(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceItemsBulkConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[ComplianceItemRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    unique_item_ids = list(dict.fromkeys(payload.item_ids))
    items = db.scalars(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.id.in_(unique_item_ids),
            ComplianceItem.deleted_at.is_(None),
        )
    ).all()
    if len(items) != len(unique_item_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some compliance items were not found",
        )

    blocked_items = [
        item
        for item in items
        if not item.is_batch_confirm_allowed or item.source_chunk_id is None
    ]
    if blocked_items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="High-risk, mandatory, missing-material, or sourceless items must be confirmed one by one",
        )

    before_items = [compliance_item_snapshot(item) for item in items]
    now = datetime.now(UTC)
    for item in items:
        item.status = "confirmed"
        item.confirmed_by = ctx.user_id
        item.confirmed_at = now
        item.modified_by = ctx.user_id
        item.modified_at = now
        item.modify_reason = payload.reason.strip()
        refresh_batch_confirm_guard(item)
    after_items = [compliance_item_snapshot(item) for item in items]
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.items_batch_confirmed",
        object_type="compliance_item_batch",
        object_id=None,
        before_json={"items": before_items},
        after_json={"items": after_items},
        reason=payload.reason.strip(),
    )
    db.commit()
    return [compliance_item_read_from_item(db, item) for item in items]


@router.get("/{project_id}/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    section_id: uuid.UUID | None = None,
    action: str | None = None,
    object_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogRead]:
    get_project_or_404(db, ctx, project_id)
    actor = aliased(User)

    stmt = (
        select(AuditLog, actor.name.label("actor_name"))
        .outerjoin(actor, actor.id == AuditLog.actor_user_id)
        .where(
            AuditLog.tenant_id == ctx.tenant_id,
            AuditLog.project_id == project_id,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if section_id:
        stmt = stmt.where(AuditLog.section_id == section_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if object_type:
        stmt = stmt.where(AuditLog.object_type == object_type)

    return [
        AuditLogRead(
            id=log.id,
            project_id=log.project_id,
            section_id=log.section_id,
            actor_user_id=log.actor_user_id,
            actor_name=actor_name,
            actor_type=log.actor_type,
            action=log.action,
            object_type=log.object_type,
            object_id=log.object_id,
            before_json=log.before_json,
            after_json=log.after_json,
            reason=log.reason,
            severity=log.severity,
            created_at=log.created_at,
        )
        for log, actor_name in db.execute(stmt).all()
    ]


@router.get("/{project_id}/model-invocation-logs", response_model=list[ModelInvocationLogRead])
def list_model_invocation_logs(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    section_id: uuid.UUID | None = None,
    task_type: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ModelInvocationLogRead]:
    get_project_or_404(db, ctx, project_id)

    stmt = (
        select(ModelInvocationLog)
        .where(
            ModelInvocationLog.tenant_id == ctx.tenant_id,
            ModelInvocationLog.project_id == project_id,
        )
        .order_by(ModelInvocationLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if section_id:
        stmt = stmt.where(ModelInvocationLog.section_id == section_id)
    if task_type:
        stmt = stmt.where(ModelInvocationLog.task_type == task_type)
    if status_filter:
        stmt = stmt.where(ModelInvocationLog.status == status_filter)

    return [ModelInvocationLogRead.model_validate(item) for item in db.scalars(stmt).all()]
