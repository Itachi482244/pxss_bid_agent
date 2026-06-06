from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, aliased

from app.api.deps import RequestContext, get_request_context
from app.core.config import settings
from app.db.session import SessionLocal, get_db
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
    DraftBlock,
    DraftContextPack,
    DraftCoverageReview,
    DraftFactCheck,
    DraftSectionContextPack,
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
    BusinessDraftContextPackGenerateRequest,
    BusinessDraftContextPackGenerateResult,
    BusinessDraftContextPackPreviewRead,
    BusinessDraftContextPackRead,
    BusinessDraftContextPackRequest,
    BusinessDraftEvidenceRefRead,
    BusinessDraftExportRequest,
    BusinessDraftGenerateRequest,
    ComplianceItemAssignRequest,
    ComplianceEvidenceBindRequest,
    ComplianceEvidenceBindingRead,
    ComplianceEvidenceUnbindRequest,
    ComplianceEvidenceWaiveRequest,
    ComplianceItemsBulkAssignRequest,
    ComplianceItemsBulkConfirmRequest,
    ComplianceItemConfirmRequest,
    ComplianceItemFromSourceRequest,
    ComplianceItemFromSourceResult,
    ComplianceMatrixGenerateRequest,
    DraftBlockRead,
    DraftBlockUpdateRequest,
    DraftCoverageReviewRead,
    DraftFactCheckRead,
    DraftSectionContextPackRead,
    DuplicateGroupActionRequest,
    DuplicateGroupActionResult,
    ComplianceItemRead,
    ComplianceItemUpdateRequest,
    MatrixReviewDuplicateGroupRead,
    MatrixReviewHighlightRead,
    MatrixReviewRead,
    MatrixReviewStats,
    MatrixReviewUncoveredChunkRead,
    ModelInvocationLogRead,
    PreflightCheckItem,
    PreflightCheckRead,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectImportConfirmRead,
    ProjectImportConfirmRequest,
    ProjectImportDraftRead,
    ProjectImportProjectDraft,
    ProjectImportSectionDraft,
    ProjectImportSourceRead,
    ProjectImportUrlRequest,
    ProjectUpdateRequest,
    QualificationDecisionConfirmRequest,
    QualificationDecisionRead,
    QualificationEvaluationConfirmRequest,
    QualificationEvaluationRead,
    ProjectSummary,
    SectionCreateRequest,
    SectionSummary,
    SectionUpdateRequest,
    SimilarCandidateApplyRequest,
    SimilarCandidateRead,
    TextDiffSegment,
)
from app.schemas.document import DocumentChunkRead
from app.services.business_draft import (
    BusinessDraftError,
    export_business_draft_word,
    generate_business_draft_chapters,
    recompose_chapter_text_from_blocks,
    run_fact_checks,
)
from app.services.context_pack import (
    build_context_pack_preview,
    create_context_pack,
    create_coverage_review,
    execute_business_draft_generation_task,
    generate_draft_from_context_pack,
)
from app.services.compliance_generation import execute_compliance_matrix_generation_task
from app.services.document_utils import MAX_FILE_BYTES
from app.services.evidence_policy import (
    enterprise_evidence_not_required as policy_enterprise_evidence_not_required,
)
from app.services.evidence_policy import (
    enterprise_evidence_not_required_reason as policy_enterprise_evidence_not_required_reason,
)
from app.services.evidence_policy import requires_enterprise_evidence
from app.services.export_excel import execute_compliance_matrix_excel_export_task
from app.services.file_acquisition import FileAcquisitionError
from app.services.material_identity import enterprise_material_identity_key, material_snapshot_identity_key
from app.services.project_import import (
    ImportDraft,
    build_upload_import_draft,
    build_url_import_draft,
    confirm_import_draft,
    execute_import_processing_background,
)
from app.services.qualification_evaluation import evaluation_snapshot, run_qualification_evaluation
from app.services.storage import get_object_bytes
from app.services.task_dispatch import TaskDispatchError, enqueue_celery_task
from app.services.word_review import (
    WordReviewError,
    build_chunk_fallback_review_document,
    build_pdf_review_document,
    build_word_review_document,
)

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
        "dedup_key": item.dedup_key,
        "duplicate_group_id": str(item.duplicate_group_id) if item.duplicate_group_id else None,
        "duplicate_group_status": item.duplicate_group_status,
        "selected_text": item.selected_text,
        "selection_start_offset": item.selection_start_offset,
        "selection_end_offset": item.selection_end_offset,
        "source_create_method": item.source_create_method,
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


def dedupe_evidence_bindings(
    bindings: list[ComplianceEvidenceBinding],
) -> list[ComplianceEvidenceBinding]:
    deduped: list[ComplianceEvidenceBinding] = []
    seen_material_keys: set[str] = set()
    for binding in bindings:
        material_key = material_snapshot_identity_key(binding.material_snapshot)
        if material_key in seen_material_keys:
            continue
        seen_material_keys.add(material_key)
        deduped.append(binding)
    return deduped


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
    bindings = dedupe_evidence_bindings(list(bindings))
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


def refresh_qualification_after_evidence_change(
    db: Session,
    ctx: RequestContext,
    *,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> dict[str, int]:
    evaluations = run_qualification_evaluation(
        db,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        actor_user_id=ctx.user_id,
    )
    active_decisions = list(
        db.scalars(
            select(QualificationDecision).where(
                QualificationDecision.tenant_id == ctx.tenant_id,
                QualificationDecision.project_id == project_id,
                QualificationDecision.section_id == section_id,
                QualificationDecision.status != "superseded",
            )
        ).all()
    )
    for decision in active_decisions:
        decision.status = "superseded"
    if active_decisions:
        db.add(
            AuditLog(
                tenant_id=ctx.tenant_id,
                project_id=project_id,
                section_id=section_id,
                actor_user_id=ctx.user_id,
                actor_type="user",
                action="qualification.decision_invalidated",
                object_type="qualification_decision",
                object_id=None,
                before_json={"decision_ids": [str(item.id) for item in active_decisions]},
                after_json={"reason": "enterprise_evidence_changed"},
                reason="企业资料证据发生变化，原参标建议已失效",
                severity="warning",
            )
        )
    return {
        "evaluation_count": len(evaluations),
        "invalidated_decision_count": len(active_decisions),
    }


REVIEW_SIGNAL_KEYWORDS = (
    "必须",
    "不得",
    "应当",
    "须",
    "资格",
    "资质",
    "许可证",
    "截止",
    "保证金",
    "评分",
    "响应",
    "验收",
    "证书",
    "承诺",
)
POLLUTION_KEYWORDS = (
    "采购人：",
    "采购人:",
    "代理机构：",
    "代理机构:",
    "联系人",
    "联系电话",
    "联系方式",
    "项目编号",
    "公告标题",
)


def normalize_requirement_key(text: str) -> str:
    compact = re.sub(r"\s+", "", text.lower())
    compact = re.sub(r"[，。、“”‘’：:；;,.!?！？（）()\[\]【】<>《》\-_/\\|]+", "", compact)
    return compact[:160]


def is_pollution_text(text: str, heading_path: str | None = None) -> bool:
    combined = f"{heading_path or ''} {text}"
    if any(keyword in combined for keyword in POLLUTION_KEYWORDS):
        return True
    return bool(re.fullmatch(r"\s*(公开招标公告|招标公告|采购公告|竞争性磋商公告)\s*", text.strip()))


def chunk_has_review_signals(chunk: DocumentChunk) -> bool:
    if is_pollution_text(chunk.content_text, chunk.heading_path):
        return False
    return any(keyword in chunk.content_text for keyword in REVIEW_SIGNAL_KEYWORDS)


def duplicate_group_count_for_item(db: Session, item: ComplianceItem) -> int:
    if item.duplicate_group_id is not None:
        count = db.scalar(
            select(func.count(ComplianceItem.id)).where(
                ComplianceItem.tenant_id == item.tenant_id,
                ComplianceItem.project_id == item.project_id,
                ComplianceItem.section_id == item.section_id,
                ComplianceItem.duplicate_group_id == item.duplicate_group_id,
                ComplianceItem.deleted_at.is_(None),
            )
        )
        return int(count or 0)
    if item.dedup_key:
        count = db.scalar(
            select(func.count(ComplianceItem.id)).where(
                ComplianceItem.tenant_id == item.tenant_id,
                ComplianceItem.project_id == item.project_id,
                ComplianceItem.section_id == item.section_id,
                ComplianceItem.dedup_key == item.dedup_key,
                ComplianceItem.deleted_at.is_(None),
            )
        )
        return int(count or 0)
    return 0


def item_summary(item: ComplianceItem) -> dict[str, object]:
    return {
        "id": str(item.id),
        "requirement_text": item.requirement_text,
        "status": item.status,
        "risk_level": item.risk_level,
        "source_chunk_id": str(item.source_chunk_id) if item.source_chunk_id else None,
        "duplicate_group_id": str(item.duplicate_group_id) if item.duplicate_group_id else None,
    }


def build_text_diff(base_text: str, candidate_text: str) -> list[TextDiffSegment]:
    matcher = SequenceMatcher(None, base_text, candidate_text)
    segments: list[TextDiffSegment] = []
    for op_code, base_start, base_end, candidate_start, candidate_end in matcher.get_opcodes():
        base_part = base_text[base_start:base_end]
        candidate_part = candidate_text[candidate_start:candidate_end]
        if op_code == "equal":
            if candidate_part:
                segments.append(TextDiffSegment(operation="equal", base_text=base_part, candidate_text=candidate_part))
        elif op_code == "delete":
            segments.append(TextDiffSegment(operation="delete", base_text=base_part, candidate_text=None))
        elif op_code == "insert":
            segments.append(TextDiffSegment(operation="insert", base_text=None, candidate_text=candidate_part))
        elif op_code == "replace":
            segments.append(TextDiffSegment(operation="replace", base_text=base_part, candidate_text=candidate_part))
    return segments


def best_chunk_match(base_text: str, chunk_text: str) -> tuple[str, int | None, int | None, float, str] | None:
    base = base_text.strip()
    if len(normalize_requirement_key(base)) < 8:
        return None
    exact_index = chunk_text.find(base)
    if exact_index >= 0:
        return base, exact_index, exact_index + len(base), 1.0, "exact"

    normalized_base = normalize_requirement_key(base)
    normalized_chunk = normalize_requirement_key(chunk_text)
    if normalized_base and normalized_base in normalized_chunk:
        return base, None, None, 0.96, "contains"

    parts = [part.strip() for part in re.split(r"[。；;\n]", chunk_text) if part.strip()]
    best: tuple[str, int | None, int | None, float, str] | None = None
    for part in parts:
        if len(normalize_requirement_key(part)) < 8:
            continue
        ratio = SequenceMatcher(None, normalize_requirement_key(base), normalize_requirement_key(part)).ratio()
        if ratio >= 0.72 and (best is None or ratio > best[3]):
            start = chunk_text.find(part)
            best = (part, start if start >= 0 else None, (start + len(part)) if start >= 0 else None, ratio, "fuzzy")
    return best


def matrix_review_highlights(
    items: list[ComplianceItem],
    chunks_by_id: dict[uuid.UUID, DocumentChunk],
    chunk_id_aliases: dict[uuid.UUID, uuid.UUID] | None = None,
) -> list[MatrixReviewHighlightRead]:
    chunk_id_aliases = chunk_id_aliases or {}
    highlights: list[MatrixReviewHighlightRead] = []
    for item in items:
        if item.source_chunk_id is None:
            continue
        chunk = chunks_by_id.get(item.source_chunk_id)
        if chunk is None or not chunk.content_text:
            continue

        start: int | None = None
        end: int | None = None
        match_source = "chunk_fallback"
        if (
            item.selection_start_offset is not None
            and item.selection_end_offset is not None
            and 0 <= item.selection_start_offset < item.selection_end_offset <= len(chunk.content_text)
        ):
            start = item.selection_start_offset
            end = item.selection_end_offset
            match_source = "selection_offset"
        else:
            explanation = item.explanation_json or {}
            source_quote = str(explanation.get("source_quote") or "")
            candidates = [
                ("selected_text", item.selected_text or ""),
                ("source_quote", source_quote),
                ("requirement_text", item.requirement_text),
            ]
            for candidate_source, candidate in candidates:
                text = candidate.strip()
                if not text:
                    continue
                index = chunk.content_text.find(text)
                if index >= 0:
                    start = index
                    end = index + len(text)
                    match_source = candidate_source
                    break

        if start is None or end is None:
            start = 0
            end = len(chunk.content_text)

        highlights.append(
            MatrixReviewHighlightRead(
                item_id=item.id,
                chunk_id=chunk_id_aliases.get(chunk.id, chunk.id),
                start_offset=start,
                end_offset=end,
                risk_level=item.risk_level,
                status=item.status,
                item_type=item.item_type,
                match_source=match_source,
                text=chunk.content_text[start:end],
            )
        )
    return highlights


def normalized_review_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def review_chunk_aliases(
    items: list[ComplianceItem],
    chunks_by_id: dict[uuid.UUID, DocumentChunk],
    review_chunks: list[DocumentChunk],
) -> dict[uuid.UUID, uuid.UUID]:
    review_chunks_by_text: dict[str, DocumentChunk] = {}
    for chunk in review_chunks:
        review_chunks_by_text.setdefault(normalized_review_text(chunk.content_text), chunk)

    aliases: dict[uuid.UUID, uuid.UUID] = {}
    for item in items:
        if item.source_chunk_id is None:
            continue
        source_chunk = chunks_by_id.get(item.source_chunk_id)
        if source_chunk is None or source_chunk.id in {chunk.id for chunk in review_chunks}:
            continue
        review_chunk = review_chunks_by_text.get(normalized_review_text(source_chunk.content_text))
        if review_chunk is not None:
            aliases[source_chunk.id] = review_chunk.id
    return aliases


def select_review_document(documents: list[Document], items: list[ComplianceItem]) -> Document | None:
    current_documents = [document for document in documents if document.current_version_id is not None]
    documents_by_id = {document.id: document for document in current_documents}
    source_counts: dict[uuid.UUID, int] = {}
    for item in items:
        source_counts[item.source_document_id] = source_counts.get(item.source_document_id, 0) + 1
    used_documents = sorted(
        (
            document
            for document_id in source_counts
            if (document := documents_by_id.get(document_id)) is not None
        ),
        key=lambda document: (
            source_counts.get(document.id, 0),
            document.file_ext == "docx",
            document.doc_type == "tender",
        ),
        reverse=True,
    )
    if used_documents:
        return used_documents[0]
    docx_tender = next(
        (document for document in current_documents if document.doc_type == "tender" and document.file_ext == "docx"),
        None,
    )
    if docx_tender is not None:
        return docx_tender
    tender = next((document for document in current_documents if document.doc_type == "tender"), None)
    if tender is not None:
        return tender
    if current_documents:
        return current_documents[0]
    first_source_document_id = next((item.source_document_id for item in items), None)
    if first_source_document_id is None:
        return None
    return next((document for document in documents if document.id == first_source_document_id), None)


def build_similar_candidates(
    db: Session,
    ctx: RequestContext,
    *,
    base_item: ComplianceItem,
    limit: int = 20,
) -> list[SimilarCandidateRead]:
    base_text = (base_item.selected_text or base_item.requirement_text).strip()
    if not base_text:
        return []
    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_version_id == base_item.source_version_id,
            DocumentChunk.section_id == base_item.section_id,
        )
        .order_by(DocumentChunk.chunk_index.asc())
    ).all()
    existing_by_chunk = {
        row.source_chunk_id: row.id
        for row in db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == ctx.tenant_id,
                ComplianceItem.project_id == base_item.project_id,
                ComplianceItem.section_id == base_item.section_id,
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
        if row.source_chunk_id is not None and row.dedup_key == base_item.dedup_key
    }
    candidates: list[SimilarCandidateRead] = []
    for chunk in chunks:
        if chunk.id == base_item.source_chunk_id:
            continue
        if is_pollution_text(chunk.content_text, chunk.heading_path):
            continue
        match = best_chunk_match(base_text, chunk.content_text)
        if match is None:
            continue
        snippet, start_offset, end_offset, similarity, match_type = match
        candidate_key = hashlib.sha1(
            f"{chunk.id}:{start_offset}:{end_offset}:{normalize_requirement_key(snippet)}".encode("utf-8")
        ).hexdigest()
        candidates.append(
            SimilarCandidateRead(
                candidate_key=candidate_key,
                source_chunk_id=chunk.id,
                source_chunk_index=chunk.chunk_index,
                page_no=chunk.page_no,
                heading_path=chunk.heading_path,
                selected_text=snippet,
                selection_start_offset=start_offset,
                selection_end_offset=end_offset,
                similarity=round(float(similarity), 4),
                match_type=match_type,
                diff_segments=build_text_diff(base_text, snippet),
                existing_item_id=existing_by_chunk.get(chunk.id),
            )
        )
    return sorted(candidates, key=lambda item: item.similarity, reverse=True)[:limit]


def ensure_duplicate_group(
    items: list[ComplianceItem],
    *,
    ctx: RequestContext,
    now: datetime,
) -> uuid.UUID:
    existing_group_id = next((item.duplicate_group_id for item in items if item.duplicate_group_id), None)
    group_id = existing_group_id or uuid.uuid4()
    for item in items:
        item.duplicate_group_id = group_id
        item.duplicate_group_status = "confirmed"
        item.duplicate_group_confirmed_at = now
        item.duplicate_group_confirmed_by = ctx.user_id
    return group_id


def read_items(db: Session, items: list[ComplianceItem]) -> list[ComplianceItemRead]:
    return [compliance_item_read_from_item(db, item) for item in items]


def confirmation_requires_source_verified(item: ComplianceItem) -> bool:
    return item.risk_level == "high" or item.is_mandatory or item.item_type == "qualification"


def enterprise_evidence_not_required(item: ComplianceItem) -> bool:
    return policy_enterprise_evidence_not_required(item)


def enterprise_evidence_not_required_reason(item: ComplianceItem) -> str | None:
    return policy_enterprise_evidence_not_required_reason(item)


def compliance_priority_for_item(item: ComplianceItem, evidence_count: int) -> tuple[int, str, str]:
    technical_signals = ("技术", "设备", "参数", "验收", "净化", "洁净")
    text = f"{item.requirement_text}\n{item.response_suggestion or ''}"
    evidence_required = not enterprise_evidence_not_required(item)
    if item.item_type in {"qualification", "mandatory_response", "deadline"} or (
        item.risk_level == "high" and item.is_mandatory
    ):
        return 0, "P0-资格/强制阻断", "资格、强制或截止类条款需要优先确认，避免实质性响应遗漏"
    if item.risk_level == "high" or (item.status == "needs_material" and evidence_required) or (
        item.is_mandatory and evidence_count == 0 and evidence_required
    ):
        return 1, "P1-高风险/缺证据", "该条款存在高风险或缺少企业资料证据，建议优先补齐"
    if item.item_type in {"scoring", "technical_response"} or (
        item.item_type == "other" and any(signal in text for signal in technical_signals)
    ):
        return 2, "P2-评分/技术待确认", "该条款涉及评分或技术响应，建议转交业务/技术人员复核"
    return 3, "P3-一般响应", "普通响应项，按常规流程处理"


def compliance_item_read_payload(
    *,
    item: ComplianceItem,
    source_document_title: str | None,
    source_version_label: str | None,
    owner_name: str | None,
    source_chunk: DocumentChunk | None,
    evidence_count: int,
    evidence_summary: str | None,
    duplicate_group_count: int = 0,
    cascade_affected_count: int = 0,
    cascade_affected_items: list[dict[str, object]] | None = None,
) -> ComplianceItemRead:
    priority_rank, priority_label, priority_reason = compliance_priority_for_item(item, evidence_count)
    explanation = item.explanation_json or {}
    return ComplianceItemRead(
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
        dedup_key=item.dedup_key,
        duplicate_group_id=item.duplicate_group_id,
        duplicate_group_status=item.duplicate_group_status,
        duplicate_group_confirmed_at=item.duplicate_group_confirmed_at,
        duplicate_group_confirmed_by=item.duplicate_group_confirmed_by,
        duplicate_group_count=duplicate_group_count,
        selected_text=item.selected_text,
        selection_start_offset=item.selection_start_offset,
        selection_end_offset=item.selection_end_offset,
        source_create_method=item.source_create_method,
        review_hint=explanation.get("review_hint"),
        classification_reason=explanation.get("classification_reason") or explanation.get("rule_reason"),
        split_reason=explanation.get("split_reason"),
        source_quote=explanation.get("source_quote"),
        needs_human_review=bool(explanation.get("needs_human_review")),
        enterprise_evidence_count=evidence_count,
        enterprise_evidence_summary=evidence_summary,
        enterprise_evidence_not_required=enterprise_evidence_not_required(item),
        enterprise_evidence_not_required_reason=enterprise_evidence_not_required_reason(item),
        priority_rank=priority_rank,
        priority_label=priority_label,
        priority_reason=priority_reason,
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
        cascade_affected_count=cascade_affected_count,
        cascade_affected_items=cascade_affected_items or [],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


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
    duplicate_group_count = duplicate_group_count_for_item(db, item)
    return compliance_item_read_payload(
        item=item,
        source_document_title=document.title if document else None,
        source_version_label=version.version_label if version else None,
        owner_name=owner_name,
        source_chunk=source_chunk,
        evidence_count=evidence_count,
        evidence_summary=evidence_summary,
        duplicate_group_count=duplicate_group_count,
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


def section_summary_for_section(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    section: BidSection,
) -> SectionSummary:
    document_count = db.scalar(
        select(func.count(Document.id)).where(
            Document.tenant_id == tenant_id,
            Document.project_id == section.project_id,
            Document.section_id == section.id,
            Document.status != "deleted",
        )
    ) or 0
    compliance_item_count = db.scalar(
        select(func.count(ComplianceItem.id)).where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == section.project_id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.deleted_at.is_(None),
        )
    ) or 0
    high_risk_count = db.scalar(
        select(func.count(ComplianceItem.id)).where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == section.project_id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.risk_level == "high",
            ComplianceItem.deleted_at.is_(None),
        )
    ) or 0
    pending_confirm_count = db.scalar(
        select(func.count(ComplianceItem.id)).where(
            ComplianceItem.tenant_id == tenant_id,
            ComplianceItem.project_id == section.project_id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.status == "pending_confirm",
            ComplianceItem.deleted_at.is_(None),
        )
    ) or 0
    return SectionSummary(
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
        pending_confirm_count=pending_confirm_count,
        created_at=section.created_at,
        updated_at=section.updated_at,
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


def draft_section_context_pack_read(
    section_context_pack: DraftSectionContextPack,
) -> DraftSectionContextPackRead:
    return DraftSectionContextPackRead.model_validate(section_context_pack)


def draft_context_pack_read(db: Session, context_pack: DraftContextPack) -> BusinessDraftContextPackRead:
    section_context_packs = db.scalars(
        select(DraftSectionContextPack)
        .where(
            DraftSectionContextPack.tenant_id == context_pack.tenant_id,
            DraftSectionContextPack.context_pack_id == context_pack.id,
            DraftSectionContextPack.status != "superseded",
        )
        .order_by(DraftSectionContextPack.sort_order.asc())
    ).all()
    payload = BusinessDraftContextPackRead.model_validate(context_pack)
    payload.section_context_packs = [
        draft_section_context_pack_read(section_context_pack)
        for section_context_pack in section_context_packs
    ]
    return payload


def draft_block_read(block: DraftBlock) -> DraftBlockRead:
    return DraftBlockRead.model_validate(block)


def draft_coverage_review_read(review: DraftCoverageReview) -> DraftCoverageReviewRead:
    return DraftCoverageReviewRead.model_validate(review)


def draft_block_review_summary(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    section_id: uuid.UUID,
) -> dict[str, int | list[str]]:
    blocks = db.scalars(
        select(DraftBlock).where(
            DraftBlock.tenant_id == tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
        )
    ).all()
    status_counts: dict[str, int] = {}
    for block in blocks:
        status_counts[block.review_status] = status_counts.get(block.review_status, 0) + 1
    unresolved_statuses = sorted(status for status in status_counts if status != "approved")
    return {
        "total": len(blocks),
        "approved": status_counts.get("approved", 0),
        "unresolved": sum(count for status, count in status_counts.items() if status != "approved"),
        "unresolved_statuses": unresolved_statuses,
        "needs_evidence": status_counts.get("needs_evidence", 0),
        "needs_fact": status_counts.get("needs_fact", 0),
        "rejected": status_counts.get("rejected", 0),
        "pending": status_counts.get("pending", 0) + status_counts.get("covered", 0),
    }


def build_preflight_check(
    db: Session,
    *,
    ctx: RequestContext,
    project: Project,
    section: BidSection,
) -> PreflightCheckRead:
    documents = db.scalars(
        select(Document)
        .where(
            Document.tenant_id == ctx.tenant_id,
            Document.project_id == project.id,
            Document.section_id == section.id,
            Document.status != "deleted",
        )
        .order_by(Document.acquired_at.desc(), Document.created_at.desc())
    ).all()
    current_version_ids = {document.id: document.current_version_id for document in documents if document.current_version_id}
    current_versions = {
        version.id: version
        for version in db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == ctx.tenant_id,
                DocumentVersion.id.in_(list(current_version_ids.values()) or [uuid.uuid4()]),
            )
        ).all()
    }
    latest_document = next((document for document in documents if document.doc_type == "tender"), documents[0] if documents else None)
    latest_version = current_versions.get(latest_document.current_version_id) if latest_document else None

    items = db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project.id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(ComplianceItem.created_at.asc())
    ).all()
    evidence_counts = {
        row.compliance_item_id: row.count
        for row in db.execute(
            select(
                ComplianceEvidenceBinding.compliance_item_id,
                func.count(ComplianceEvidenceBinding.id).label("count"),
            )
            .where(
                ComplianceEvidenceBinding.tenant_id == ctx.tenant_id,
                ComplianceEvidenceBinding.project_id == project.id,
                ComplianceEvidenceBinding.section_id == section.id,
                ComplianceEvidenceBinding.status == "active",
            )
            .group_by(ComplianceEvidenceBinding.compliance_item_id)
        ).all()
    }

    matrix_version_ids = sorted({item.source_version_id for item in items}, key=str)
    version_labels = {
        version.id: version.version_label
        for version in db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == ctx.tenant_id,
                DocumentVersion.id.in_(matrix_version_ids or [uuid.uuid4()]),
            )
        ).all()
    }
    outdated_items = [
        item
        for item in items
        if current_version_ids.get(item.source_document_id)
        and current_version_ids[item.source_document_id] != item.source_version_id
    ]
    unresolved_statuses = {"draft", "pending_confirm", "needs_material", "rejected"}
    pending_qualification_count = sum(
        1 for item in items if item.item_type == "qualification" and item.status in unresolved_statuses
    )
    qualification_decision = db.scalar(
        select(QualificationDecision)
        .where(
            QualificationDecision.tenant_id == ctx.tenant_id,
            QualificationDecision.project_id == project.id,
            QualificationDecision.section_id == section.id,
            QualificationDecision.status != "superseded",
        )
        .order_by(QualificationDecision.created_at.desc())
    )
    high_risk_unconfirmed_count = sum(
        1 for item in items if item.risk_level == "high" and item.status != "confirmed"
    )
    mandatory_missing_evidence_count = sum(
        1
        for item in items
        if item.is_mandatory
        and requires_enterprise_evidence(item)
        and evidence_counts.get(item.id, 0) == 0
    )
    missing_evidence_count = sum(
        1
        for item in items
        if requires_enterprise_evidence(item)
        and (item.is_mandatory or item.status == "needs_material")
        and evidence_counts.get(item.id, 0) == 0
    )
    technical_signals = ("技术", "设备", "参数", "验收", "净化", "洁净")
    technical_pending_count = sum(
        1
        for item in items
        if item.status != "confirmed"
        and (
            item.item_type in {"technical_response", "scoring"}
            or (item.item_type == "other" and any(signal in item.requirement_text for signal in technical_signals))
        )
    )

    chapters = db.scalars(
        select(BusinessDraftChapter).where(
            BusinessDraftChapter.tenant_id == ctx.tenant_id,
            BusinessDraftChapter.project_id == project.id,
            BusinessDraftChapter.section_id == section.id,
            BusinessDraftChapter.status != "superseded",
        )
    ).all()
    chapter_ids = [chapter.id for chapter in chapters]
    fact_checks = db.scalars(
        select(DraftFactCheck).where(
            DraftFactCheck.tenant_id == ctx.tenant_id,
            DraftFactCheck.chapter_id.in_(chapter_ids or [uuid.uuid4()]),
        )
    ).all()
    unverified_fact_count = sum(1 for check in fact_checks if check.check_status == "unverified")
    failed_fact_count = sum(1 for check in fact_checks if check.check_status == "warning")
    pending_fact_check_chapter_count = sum(1 for chapter in chapters if chapter.fact_check_status == "pending")
    block_review = draft_block_review_summary(
        db,
        tenant_id=ctx.tenant_id,
        project_id=project.id,
        section_id=section.id,
    )

    approval_tasks = db.scalars(
        select(ApprovalTask).where(
            ApprovalTask.tenant_id == ctx.tenant_id,
            ApprovalTask.project_id == project.id,
            ApprovalTask.section_id == section.id,
        )
    ).all()
    pending_approval_count = sum(1 for task in approval_tasks if task.status == "pending")
    rejected_approval_count = sum(1 for task in approval_tasks if task.status == "rejected")

    has_deadline_item = any(item.item_type == "deadline" for item in items)
    missing_bid_deadline = not (section.bid_deadline_at or project.bid_deadline_at)
    missing_deadline_item = bool(items) and not has_deadline_item

    checks: list[PreflightCheckItem] = []

    def add_check(
        code: str,
        title: str,
        check_status: str,
        count: int,
        message: str,
        action_label: str | None = None,
        target: str | None = None,
    ) -> None:
        checks.append(
            PreflightCheckItem(
                code=code,
                title=title,
                status=check_status,
                count=count,
                message=message,
                action_label=action_label,
                target=target,
            )
        )

    add_check(
        "matrix_version",
        "矩阵版本",
        "block" if outdated_items else "pass",
        len(outdated_items),
        "矩阵已落后于最新解析版本，建议重新生成。" if outdated_items else "矩阵基于当前解析版本。",
        "重新生成矩阵" if outdated_items else None,
        "matrix",
    )
    add_check(
        "high_risk",
        "高风险项",
        "block" if high_risk_unconfirmed_count else "pass",
        high_risk_unconfirmed_count,
        f"还有 {high_risk_unconfirmed_count} 条高风险项未确认。" if high_risk_unconfirmed_count else "高风险项已处理。",
        "查看合规矩阵",
        "matrix",
    )
    add_check(
        "mandatory_evidence",
        "强制项证据",
        "block" if mandatory_missing_evidence_count else "pass",
        mandatory_missing_evidence_count,
        f"还有 {mandatory_missing_evidence_count} 条强制项缺少企业资料证据。"
        if mandatory_missing_evidence_count
        else "强制项证据已补齐。",
        "绑定企业资料",
        "evidence",
    )
    add_check(
        "draft_facts",
        "草稿事实",
        "block" if unverified_fact_count else "warn" if failed_fact_count or pending_fact_check_chapter_count else "pass",
        unverified_fact_count + failed_fact_count + pending_fact_check_chapter_count,
        "草稿中存在无法验证或待校验事实。"
        if unverified_fact_count or failed_fact_count or pending_fact_check_chapter_count
        else "草稿事实校验通过。",
        "查看商务草稿",
        "chapter",
    )
    if block_review["total"]:
        add_check(
            "draft_block_review",
            "结构化草稿审阅",
            "block" if block_review["unresolved"] else "pass",
            int(block_review["unresolved"]),
            f"还有 {block_review['unresolved']} 个结构化草稿 block 未人工通过。"
            if block_review["unresolved"]
            else "结构化草稿 block 已全部人工通过。",
            "审阅草稿 block",
            "chapter",
        )
    add_check(
        "qualification",
        "资格项确认",
        "warn" if pending_qualification_count else "pass",
        pending_qualification_count,
        f"还有 {pending_qualification_count} 条资格项待确认。" if pending_qualification_count else "资格项已确认。",
        "查看资格预评估",
        "qualification",
    )
    if qualification_decision is None:
        qualification_decision_status = "block"
        qualification_decision_message = "尚未生成参标建议，需先运行资格预评估并人工确认。"
        qualification_decision_action = "运行资格预评估"
        qualification_decision_count = 1
    elif qualification_decision.status != "confirmed":
        qualification_decision_status = "block"
        qualification_decision_message = "参标建议尚未人工确认，不能进入正式 ContextPack 和草稿生成。"
        qualification_decision_action = "确认参标建议"
        qualification_decision_count = 1
    elif qualification_decision.recommendation == "no_go":
        qualification_decision_status = "block"
        qualification_decision_message = "已确认的参标建议为 No-Go，只能在风险接受后生成内部草稿。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 1
    elif qualification_decision.recommendation == "conditional_go":
        qualification_decision_status = "warn"
        qualification_decision_message = "参标建议为有条件 Go，生成草稿和提交前仍需复核缺材料/待确认事项。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 1
    else:
        qualification_decision_status = "pass"
        qualification_decision_message = "参标建议已确认。"
        qualification_decision_action = "查看资格结论"
        qualification_decision_count = 0
    add_check(
        "qualification_decision",
        "参标建议",
        qualification_decision_status,
        qualification_decision_count,
        qualification_decision_message,
        qualification_decision_action,
        "qualification",
    )
    add_check(
        "technical",
        "技术响应",
        "warn" if technical_pending_count else "pass",
        technical_pending_count,
        f"还有 {technical_pending_count} 条技术/评分项待确认。" if technical_pending_count else "技术响应项无明显阻塞。",
        "查看技术响应",
        "technical",
    )
    add_check(
        "deadline",
        "关键日期",
        "warn" if missing_bid_deadline or missing_deadline_item else "pass",
        int(missing_bid_deadline) + int(missing_deadline_item),
        "项目截止时间或招标文件关键日期缺失，建议人工补充。"
        if missing_bid_deadline or missing_deadline_item
        else "关键日期已有记录。",
        "查看项目文件",
        "documents",
    )
    add_check(
        "approvals",
        "审批任务",
        "warn" if pending_approval_count or rejected_approval_count else "pass",
        pending_approval_count + rejected_approval_count,
        f"待处理审批 {pending_approval_count} 个，退回审批 {rejected_approval_count} 个。"
        if pending_approval_count or rejected_approval_count
        else "审批任务无阻塞。",
        "查看审批",
        "approval",
    )

    if not chapters:
        draft_message = "尚未生成商务/资格草稿。"
        draft_action = "生成草稿"
        draft_target = "chapter"
        if qualification_decision is None or qualification_decision.status != "confirmed":
            draft_message = "尚未完成资格预评估确认，先生成并确认参标建议后再生成草稿。"
            draft_action = "运行资格预评估"
            draft_target = "qualification"
        add_check(
            "draft_exists",
            "商务草稿",
            "warn",
            1,
            draft_message,
            draft_action,
            draft_target,
        )

    if any(item.status == "block" for item in checks):
        overall_status = "block"
        summary = "存在阻塞项，建议先处理版本、风险、证据或事实校验问题。"
    elif any(item.status == "warn" for item in checks):
        overall_status = "warn"
        summary = "主链路可继续推进，但仍有待确认事项需要人工复核。"
    else:
        overall_status = "pass"
        summary = "提交前核验通过，当前无明显阻塞项。"

    suggested_actions = [
        item.message for item in checks if item.status in {"block", "warn"}
    ][:5]
    if not suggested_actions:
        suggested_actions = ["可进入审批、导出和归档流程。"]

    return PreflightCheckRead(
        project_id=project.id,
        section_id=section.id,
        status=overall_status,
        summary=summary,
        latest_document_version_id=latest_version.id if latest_version else None,
        latest_document_version_label=latest_version.version_label if latest_version else None,
        matrix_version_ids=matrix_version_ids,
        matrix_version_labels=[version_labels.get(version_id, str(version_id)) for version_id in matrix_version_ids],
        matrix_outdated=bool(outdated_items),
        outdated_item_count=len(outdated_items),
        pending_qualification_count=pending_qualification_count,
        high_risk_unconfirmed_count=high_risk_unconfirmed_count,
        mandatory_missing_evidence_count=mandatory_missing_evidence_count,
        technical_pending_count=technical_pending_count,
        missing_evidence_count=missing_evidence_count,
        unverified_fact_count=unverified_fact_count,
        failed_fact_count=failed_fact_count,
        pending_fact_check_chapter_count=pending_fact_check_chapter_count,
        pending_approval_count=pending_approval_count,
        rejected_approval_count=rejected_approval_count,
        missing_bid_deadline=missing_bid_deadline,
        missing_deadline_item=missing_deadline_item,
        checks=checks,
        suggested_actions=suggested_actions,
    )


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


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ProjectDetail:
    project = get_project_or_404(db, ctx, project_id)
    before_json = {
        "name": project.name,
        "purchaser": project.purchaser,
        "agency": project.agency,
        "budget_amount": str(project.budget_amount) if project.budget_amount is not None else None,
        "region_code": project.region_code,
        "industry_code": project.industry_code,
        "notice_url": project.notice_url,
        "bid_deadline_at": project.bid_deadline_at.isoformat() if project.bid_deadline_at else None,
    }
    fields = payload.model_fields_set - {"reason"}
    for field in fields:
        value = getattr(payload, field)
        if field == "name" and value is not None:
            value = value.strip()
        setattr(project, field, value)
    db.flush()
    after_json = {
        "name": project.name,
        "purchaser": project.purchaser,
        "agency": project.agency,
        "budget_amount": str(project.budget_amount) if project.budget_amount is not None else None,
        "region_code": project.region_code,
        "industry_code": project.industry_code,
        "notice_url": project.notice_url,
        "bid_deadline_at": project.bid_deadline_at.isoformat() if project.bid_deadline_at else None,
        "updated_fields": sorted(fields),
    }
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project.id,
        section_id=None,
        action="project.updated",
        object_type="project",
        object_id=project.id,
        before_json=before_json,
        after_json=after_json,
        reason=payload.reason,
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
    background_tasks: BackgroundTasks,
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
            async_processing=payload.async_processing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if payload.async_processing and payload.auto_parse and result.parse_task_id is not None:
        matrix_task_id = result.matrix_task_id if payload.auto_generate_matrix else None
        if settings.run_tasks_inline:
            background_tasks.add_task(
                execute_import_processing_background,
                parse_task_id=result.parse_task_id,
                matrix_task_id=matrix_task_id,
            )
        else:
            parse_task = db.get(AsyncTask, result.parse_task_id)
            if parse_task is not None:
                from app.worker import run_import_processing_task

                try:
                    enqueue_celery_task(
                        db,
                        parse_task,
                        lambda: run_import_processing_task.delay(
                            str(result.parse_task_id),
                            str(matrix_task_id) if matrix_task_id is not None else None,
                        ),
                    )
                except TaskDispatchError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"导入处理任务派发失败：{exc}",
                    ) from exc
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
    return section_summary_for_section(db, tenant_id=ctx.tenant_id, section=section)


@router.patch("/{project_id}/sections/{section_id}", response_model=SectionSummary)
def update_section(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: SectionUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> SectionSummary:
    section = get_section_or_404(db, ctx, project_id, section_id)
    before_json = {
        "code": section.code,
        "name": section.name,
        "budget_amount": str(section.budget_amount) if section.budget_amount is not None else None,
        "bid_deadline_at": section.bid_deadline_at.isoformat() if section.bid_deadline_at else None,
    }
    fields = payload.model_fields_set - {"reason"}
    for field in fields:
        value = getattr(payload, field)
        if field == "name" and value is not None:
            value = value.strip()
        setattr(section, field, value)
    db.flush()
    after_json = {
        "code": section.code,
        "name": section.name,
        "budget_amount": str(section.budget_amount) if section.budget_amount is not None else None,
        "bid_deadline_at": section.bid_deadline_at.isoformat() if section.bid_deadline_at else None,
        "updated_fields": sorted(fields),
    }
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section.id,
        action="section.updated",
        object_type="bid_section",
        object_id=section.id,
        before_json=before_json,
        after_json=after_json,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(section)
    return section_summary_for_section(db, tenant_id=ctx.tenant_id, section=section)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/generate",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_compliance_matrix_generation_task(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceMatrixGenerateRequest,
    background_tasks: BackgroundTasks,
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

    if payload.async_processing and settings.run_tasks_inline:
        background_tasks.add_task(_execute_matrix_generation_background, task.id)
    elif settings.run_tasks_inline:
        execute_compliance_matrix_generation_task(db, task.id)
        db.refresh(task)
    else:
        from app.worker import run_compliance_matrix_generation_task

        try:
            enqueue_celery_task(
                db,
                task,
                lambda: run_compliance_matrix_generation_task.delay(str(task.id)),
            )
        except TaskDispatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"合规矩阵生成任务派发失败：{exc}",
            ) from exc
        db.refresh(task)
    return AsyncTaskRead.model_validate(task)


def _execute_matrix_generation_background(task_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        execute_compliance_matrix_generation_task(db, task_id)


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
        from app.worker import run_compliance_matrix_excel_export_task

        try:
            enqueue_celery_task(
                db,
                task,
                lambda: run_compliance_matrix_excel_export_task.delay(str(task.id)),
            )
        except TaskDispatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Excel 导出任务派发失败：{exc}",
            ) from exc
        db.refresh(task)
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


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/context-pack/preview",
    response_model=BusinessDraftContextPackPreviewRead,
)
def preview_business_draft_context_pack(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: BusinessDraftContextPackRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> BusinessDraftContextPackPreviewRead:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        preview = build_context_pack_preview(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            profile_id=payload.profile_id,
            section_types=payload.section_types,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BusinessDraftContextPackPreviewRead.model_validate(preview)


@router.get(
    "/{project_id}/sections/{section_id}/business-draft/context-pack",
    response_model=list[BusinessDraftContextPackRead],
)
def list_business_draft_context_packs(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[BusinessDraftContextPackRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    context_packs = db.scalars(
        select(DraftContextPack)
        .where(
            DraftContextPack.tenant_id == ctx.tenant_id,
            DraftContextPack.project_id == project_id,
            DraftContextPack.section_id == section_id,
            DraftContextPack.status != "superseded",
        )
        .order_by(DraftContextPack.created_at.desc())
    ).all()
    return [draft_context_pack_read(db, context_pack) for context_pack in context_packs]


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/context-pack",
    response_model=BusinessDraftContextPackRead,
)
def create_business_draft_context_pack(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: BusinessDraftContextPackRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> BusinessDraftContextPackRead:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        context_pack = create_context_pack(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            profile_id=payload.profile_id,
            section_types=payload.section_types,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(context_pack)
    return draft_context_pack_read(db, context_pack)


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/context-pack/{context_pack_id}/generate",
    response_model=BusinessDraftContextPackGenerateResult,
)
def generate_business_draft_from_context_pack(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    payload: BusinessDraftContextPackGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> BusinessDraftContextPackGenerateResult:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        chapters, blocks, coverage_review = generate_draft_from_context_pack(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            context_pack_id=context_pack_id,
            actor_user_id=ctx.user_id,
            allow_blocked_internal_draft=payload.allow_blocked_internal_draft,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    context_pack = db.get(DraftContextPack, context_pack_id)
    if context_pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ContextPack not found")
    db.commit()
    db.refresh(context_pack)
    for chapter in chapters:
        db.refresh(chapter)
    for block in blocks:
        db.refresh(block)
    db.refresh(coverage_review)
    return BusinessDraftContextPackGenerateResult(
        context_pack=draft_context_pack_read(db, context_pack),
        chapters=[business_draft_chapter_read(db, chapter) for chapter in chapters],
        blocks=[draft_block_read(block) for block in blocks],
        coverage_review=draft_coverage_review_read(coverage_review),
    )


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/context-pack/{context_pack_id}/generate-async",
    response_model=AsyncTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_business_draft_from_context_pack_async(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    payload: BusinessDraftContextPackGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AsyncTaskRead:
    """Dispatch ContextPack draft generation as an async task.

    Large documents can produce many chapters/blocks plus a coverage review;
    running that synchronously risks request timeouts. The result is fetched via
    the generic ``GET /tasks/{task_id}`` poll plus the existing blocks/chapters
    and coverage-review read endpoints once the task succeeds.
    """
    get_section_or_404(db, ctx, project_id, section_id)
    context_pack = db.get(DraftContextPack, context_pack_id)
    if (
        context_pack is None
        or context_pack.tenant_id != ctx.tenant_id
        or context_pack.project_id != project_id
        or context_pack.section_id != section_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ContextPack not found")

    idempotency_key = "business-draft-generate:" + hashlib.sha256(
        f"{context_pack_id}:{uuid.uuid4().hex}".encode("utf-8")
    ).hexdigest()
    task = AsyncTask(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        task_type="business_draft_generate",
        status="pending",
        idempotency_key=idempotency_key,
        progress=0,
        input_json={
            "context_pack_id": str(context_pack_id),
            "allow_blocked_internal_draft": payload.allow_blocked_internal_draft,
        },
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
            action="business_draft.context_pack_generate_requested",
            object_type="async_task",
            object_id=task.id,
            after_json=task.input_json,
            reason="用户请求异步生成 ContextPack 商务/资格草稿",
            severity="info",
        )
    )
    db.commit()
    db.refresh(task)

    if settings.run_tasks_inline:
        execute_business_draft_generation_task(db, task.id)
        db.refresh(task)
    else:
        from app.worker import run_business_draft_generation_task

        try:
            enqueue_celery_task(
                db,
                task,
                lambda: run_business_draft_generation_task.delay(str(task.id)),
            )
        except TaskDispatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"商务草稿生成任务派发失败：{exc}",
            ) from exc
        db.refresh(task)
    return AsyncTaskRead.model_validate(task)


@router.post(
    "/{project_id}/sections/{section_id}/business-draft/context-pack/{context_pack_id}/coverage-review",
    response_model=DraftCoverageReviewRead,
)
def run_business_draft_context_pack_coverage_review(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    context_pack_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DraftCoverageReviewRead:
    get_section_or_404(db, ctx, project_id, section_id)
    try:
        review = create_coverage_review(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            context_pack_id=context_pack_id,
            actor_user_id=ctx.user_id,
        )
    except BusinessDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(review)
    return draft_coverage_review_read(review)


@router.get(
    "/{project_id}/sections/{section_id}/business-draft/blocks",
    response_model=list[DraftBlockRead],
)
def list_business_draft_blocks(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[DraftBlockRead]:
    get_section_or_404(db, ctx, project_id, section_id)
    blocks = db.scalars(
        select(DraftBlock)
        .where(
            DraftBlock.tenant_id == ctx.tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
        )
        .order_by(DraftBlock.created_at.desc(), DraftBlock.sort_order.asc())
    ).all()
    return [draft_block_read(block) for block in blocks]


@router.patch(
    "/{project_id}/sections/{section_id}/business-draft/blocks/{block_id}",
    response_model=DraftBlockRead,
)
def update_business_draft_block(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    block_id: uuid.UUID,
    payload: DraftBlockUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DraftBlockRead:
    get_section_or_404(db, ctx, project_id, section_id)
    block = db.scalar(
        select(DraftBlock).where(
            DraftBlock.tenant_id == ctx.tenant_id,
            DraftBlock.project_id == project_id,
            DraftBlock.section_id == section_id,
            DraftBlock.id == block_id,
        )
    )
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft block not found")
    before = draft_block_read(block).model_dump(mode="json")
    block.review_status = payload.review_status
    if payload.content_text is not None:
        block.content_text = payload.content_text
        if block.chapter_id and block.block_type != "heading":
            chapter = db.get(BusinessDraftChapter, block.chapter_id)
            project = db.get(Project, project_id)
            if chapter is not None:
                db.flush()
                chapter.content_text = recompose_chapter_text_from_blocks(db, chapter)
                chapter.updated_by = ctx.user_id
                chapter.edit_reason = payload.reason.strip()
                if project is not None:
                    run_fact_checks(db, chapter=chapter, project=project, actor_user_id=ctx.user_id)
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="business_draft.block_updated",
        object_type="draft_block",
        object_id=block.id,
        before_json=before,
        after_json=draft_block_read(block).model_dump(mode="json"),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(block)
    return draft_block_read(block)


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
    payload: BusinessDraftExportRequest | None = None,
) -> ExportFileRead:
    project = get_project_or_404(db, ctx, project_id)
    section = get_section_or_404(db, ctx, project_id, section_id)
    preflight = build_preflight_check(db, ctx=ctx, project=project, section=section)
    block_review = draft_block_review_summary(
        db,
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
    )
    risk_acceptance_reason = (payload.risk_acceptance_reason or "").strip() if payload else ""
    if preflight.status == "block" and not risk_acceptance_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前存在提交前核验阻塞项，导出内部草稿需填写风险接受说明",
        )
    blocking_summary = [
        item.model_dump(mode="json")
        for item in preflight.checks
        if item.status in {"block", "warn"}
    ][:8]
    try:
        export_file = export_business_draft_word(
            db,
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=ctx.user_id,
            extra_snapshot={
                "preflight_status": preflight.status,
                "preflight_summary": preflight.summary,
                "blocking_summary": blocking_summary,
                "draft_block_review": block_review,
                "risk_acceptance_reason": risk_acceptance_reason or None,
                "captured_at": datetime.now(UTC).isoformat(),
                "internal_draft": preflight.status == "block",
            },
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
    project = get_project_or_404(db, ctx, project_id)
    section = get_section_or_404(db, ctx, project_id, section_id)
    preflight = build_preflight_check(db, ctx=ctx, project=project, section=section)
    risk_acceptance_reason = (payload.risk_acceptance_reason or "").strip()
    if payload.task_type == "submit_confirmation" and preflight.status == "block" and not risk_acceptance_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前存在提交前核验阻塞项，创建提交确认审批需填写风险接受说明",
        )
    blocking_summary = [
        item.model_dump(mode="json")
        for item in preflight.checks
        if item.status in {"block", "warn"}
    ][:8]
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
        evidence_snapshot_json={
            "preflight_status": preflight.status,
            "preflight_summary": preflight.summary,
            "blocking_summary": blocking_summary,
            "suggested_actions": preflight.suggested_actions,
            "risk_acceptance_reason": risk_acceptance_reason or None,
            "captured_at": datetime.now(UTC).isoformat(),
        },
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
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="approval.blocking_snapshot_created",
        object_type="approval_task",
        object_id=task.id,
        before_json=None,
        after_json=task.evidence_snapshot_json,
        reason="创建审批任务时记录提交前核验快照",
        severity="warning" if preflight.status == "block" else "info",
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
    "/{project_id}/sections/{section_id}/preflight-check",
    response_model=PreflightCheckRead,
)
def get_preflight_check(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> PreflightCheckRead:
    project = get_project_or_404(db, ctx, project_id)
    section = get_section_or_404(db, ctx, project_id, section_id)
    return build_preflight_check(db, ctx=ctx, project=project, section=section)


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
        duplicate_group_count = duplicate_group_count_for_item(db, item)
        results.append(
            compliance_item_read_payload(
                item=item,
                source_document_title=source_document_title,
                source_version_label=source_version_label,
                owner_name=owner_name,
                source_chunk=source_chunk,
                evidence_count=evidence_count,
                evidence_summary=evidence_summary,
                duplicate_group_count=duplicate_group_count,
            )
        )
    return results


@router.get(
    "/{project_id}/sections/{section_id}/matrix-review",
    response_model=MatrixReviewRead,
)
def get_matrix_review(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> MatrixReviewRead:
    get_section_or_404(db, ctx, project_id, section_id)
    documents = db.scalars(
        select(Document).where(
            Document.tenant_id == ctx.tenant_id,
            Document.project_id == project_id,
            Document.section_id == section_id,
            Document.current_version_id.is_not(None),
            Document.status != "deleted",
        )
    ).all()
    version_ids = [document.current_version_id for document in documents if document.current_version_id]
    matrix_source_version_ids = db.scalars(
        select(ComplianceItem.source_version_id)
        .where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .distinct()
    ).all()
    for version_id in matrix_source_version_ids:
        if version_id not in version_ids:
            version_ids.append(version_id)
    chunks = (
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_version_id.in_(version_ids))
            .order_by(DocumentChunk.document_version_id.asc(), DocumentChunk.chunk_index.asc())
        ).all()
        if version_ids
        else []
    )
    items = db.scalars(
        select(ComplianceItem)
        .where(
            ComplianceItem.tenant_id == ctx.tenant_id,
            ComplianceItem.project_id == project_id,
            ComplianceItem.section_id == section_id,
            ComplianceItem.deleted_at.is_(None),
        )
        .order_by(ComplianceItem.created_at.asc())
    ).all()
    item_reads = read_items(db, items)

    duplicate_groups: list[MatrixReviewDuplicateGroupRead] = []
    by_group: dict[str, list[ComplianceItem]] = {}
    by_dedup: dict[str, list[ComplianceItem]] = {}
    for item in items:
        if item.duplicate_group_id and item.duplicate_group_status == "confirmed":
            by_group.setdefault(str(item.duplicate_group_id), []).append(item)
        elif item.dedup_key:
            by_dedup.setdefault(item.dedup_key, []).append(item)
    for group_id, group_items in by_group.items():
        if len(group_items) < 2:
            continue
        duplicate_groups.append(
            MatrixReviewDuplicateGroupRead(
                group_key=group_id,
                group_type="confirmed",
                status="confirmed",
                item_ids=[item.id for item in group_items],
                item_count=len(group_items),
                representative_text=group_items[0].requirement_text,
            )
        )
    for dedup_key, group_items in by_dedup.items():
        if len(group_items) < 2:
            continue
        duplicate_groups.append(
            MatrixReviewDuplicateGroupRead(
                group_key=dedup_key,
                group_type="candidate",
                status="candidate",
                item_ids=[item.id for item in group_items],
                item_count=len(group_items),
                representative_text=group_items[0].requirement_text,
            )
        )

    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    review_document_source = select_review_document(documents, items)
    review_version = (
        db.get(DocumentVersion, review_document_source.current_version_id)
        if review_document_source is not None and review_document_source.current_version_id is not None
        else None
    )
    review_chunks = [
        chunk
        for chunk in chunks
        if review_document_source is not None
        and review_version is not None
        and chunk.document_id == review_document_source.id
        and chunk.document_version_id == review_version.id
    ]
    fallback_review_chunks = review_chunks or chunks
    chunk_id_aliases = review_chunk_aliases(items, chunks_by_id, review_chunks)
    item_chunk_ids = {
        chunk_id_aliases.get(item.source_chunk_id, item.source_chunk_id)
        for item in items
        if item.source_chunk_id is not None
    }
    uncovered_chunks = [
        MatrixReviewUncoveredChunkRead(
            chunk=DocumentChunkRead.model_validate(chunk),
            reason="该原文片段包含强制/资格/截止/评分/响应等关键词，但当前没有矩阵项覆盖。",
        )
        for chunk in chunks
        if chunk.id not in item_chunk_ids and chunk_has_review_signals(chunk)
    ]
    if review_document_source is not None and review_version is not None and review_document_source.file_ext == "pdf":
        try:
            review_document = build_pdf_review_document(
                review_document_source,
                review_version,
                review_chunks,
            )
        except WordReviewError as exc:
            review_document = build_chunk_fallback_review_document(
                review_document_source,
                review_version,
                fallback_review_chunks,
                reason=str(exc),
            )
    elif review_document_source is not None and review_version is not None and review_document_source.file_ext != "docx":
        review_document = build_chunk_fallback_review_document(
            review_document_source,
            review_version,
            fallback_review_chunks,
            reason="当前原文不是 .docx，已使用解析文本连续展示。",
        )
    elif review_document_source is not None and review_version is not None:
        try:
            data = get_object_bytes(bucket=review_document_source.bucket, object_key=review_version.object_key)
            review_document = build_word_review_document(
                review_document_source,
                review_version,
                review_chunks,
                data,
            )
        except WordReviewError as exc:
            review_document = build_chunk_fallback_review_document(
                review_document_source,
                review_version,
                fallback_review_chunks,
                reason=str(exc),
            )
        except Exception:
            review_document = build_chunk_fallback_review_document(
                review_document_source,
                review_version,
                fallback_review_chunks,
                reason="原文审阅视图读取文件失败，已降级为解析文本。",
            )
    else:
        review_document = build_chunk_fallback_review_document(
            None,
            None,
            chunks,
            reason="未找到可用招标文件，已降级为解析文本。",
        )

    high_items = [item for item in items if item.risk_level == "high"]
    stats = MatrixReviewStats(
        total_items=len(items),
        confirmed_items=sum(1 for item in items if item.status == "confirmed"),
        high_risk_total=len(high_items),
        high_risk_confirmed=sum(1 for item in high_items if item.status == "confirmed"),
        uncovered_chunk_count=len(uncovered_chunks),
        duplicate_candidate_group_count=sum(1 for group in duplicate_groups if group.group_type == "candidate"),
        duplicate_confirmed_group_count=sum(1 for group in duplicate_groups if group.group_type == "confirmed"),
    )
    return MatrixReviewRead(
        chunks=[DocumentChunkRead.model_validate(chunk) for chunk in chunks],
        items=item_reads,
        stats=stats,
        uncovered_chunks=uncovered_chunks,
        duplicate_groups=duplicate_groups,
        review_document=review_document,
        highlights=matrix_review_highlights(items, chunks_by_id, chunk_id_aliases),
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/from-source",
    response_model=ComplianceItemFromSourceResult,
    status_code=status.HTTP_201_CREATED,
)
def create_compliance_item_from_source(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ComplianceItemFromSourceRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceItemFromSourceResult:
    get_section_or_404(db, ctx, project_id, section_id)
    chunk = db.scalar(
        select(DocumentChunk).where(
            DocumentChunk.id == payload.source_chunk_id,
            DocumentChunk.section_id == section_id,
        )
    )
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source chunk not found")
    document = db.get(Document, chunk.document_id)
    if document is None or document.tenant_id != ctx.tenant_id or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source document not found")
    selected_text = payload.selected_text.strip()
    if selected_text not in chunk.content_text and payload.selection_start_offset is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected text must come from the source chunk or include explicit offsets",
        )
    if payload.selection_start_offset is not None and payload.selection_end_offset is not None:
        if payload.selection_end_offset <= payload.selection_start_offset:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="selection_end_offset must be greater than selection_start_offset",
            )
        if payload.selection_end_offset > len(chunk.content_text):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="selection offsets exceed source chunk length",
            )
    dedup_key = normalize_requirement_key(selected_text)
    now = datetime.now(UTC)
    is_batch_confirm_allowed = payload.risk_level != "high" and not payload.is_mandatory
    item = ComplianceItem(
        tenant_id=ctx.tenant_id,
        project_id=project_id,
        section_id=section_id,
        source_document_id=document.id,
        source_version_id=chunk.document_version_id,
        source_chunk_id=chunk.id,
        source_page_no=chunk.page_no,
        item_type=payload.item_type,
        requirement_text=selected_text,
        normalized_requirement=f"manual:{dedup_key}",
        dedup_key=dedup_key,
        response_suggestion=payload.response_suggestion.strip() if payload.response_suggestion else None,
        evidence_text=selected_text,
        explanation_json={
            "rule_code": "MANUAL-SOURCE-CREATE",
            "rule_reason": "审核人从招标文件原文手动新增。",
            "source_quote": selected_text,
            "needs_human_review": True,
        },
        selected_text=selected_text,
        selection_start_offset=payload.selection_start_offset,
        selection_end_offset=payload.selection_end_offset,
        source_create_method="manual_selection",
        status="pending_confirm",
        risk_level=payload.risk_level,
        is_mandatory=payload.is_mandatory,
        is_batch_confirm_allowed=is_batch_confirm_allowed,
        owner_user_id=ctx.user_id,
        confidence_score=Decimal("1.0000"),
        created_by=ctx.user_id,
        modified_by=ctx.user_id,
        modified_at=now,
        modify_reason=payload.reason.strip(),
    )
    db.add(item)
    db.flush()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.item_created_from_source",
        object_type="compliance_item",
        object_id=item.id,
        before_json=None,
        after_json=compliance_item_snapshot(item),
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    similar_candidates = build_similar_candidates(db, ctx, base_item=item)
    return ComplianceItemFromSourceResult(
        item=compliance_item_read_from_item(db, item),
        similar_candidates=similar_candidates,
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/similar-candidates",
    response_model=list[SimilarCandidateRead],
)
def get_similar_candidates(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[SimilarCandidateRead]:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    return build_similar_candidates(db, ctx, base_item=item)


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/similar-candidates/apply",
    response_model=DuplicateGroupActionResult,
)
def apply_similar_candidates(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: SimilarCandidateApplyRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DuplicateGroupActionResult:
    base_item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    now = datetime.now(UTC)
    affected_items: list[ComplianceItem] = [base_item]
    if any(candidate.action == "join_group" for candidate in payload.candidates):
        ensure_duplicate_group([base_item], ctx=ctx, now=now)

    created_items: list[ComplianceItem] = []
    skipped: list[dict[str, object]] = []
    for candidate in payload.candidates:
        if candidate.action == "skip":
            skipped.append({"candidate_key": candidate.candidate_key, "source_chunk_id": str(candidate.source_chunk_id)})
            continue
        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.id == candidate.source_chunk_id,
                DocumentChunk.section_id == section_id,
            )
        )
        if chunk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Similar source chunk not found")
        duplicate = db.scalar(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == ctx.tenant_id,
                ComplianceItem.project_id == project_id,
                ComplianceItem.section_id == section_id,
                ComplianceItem.source_chunk_id == chunk.id,
                ComplianceItem.dedup_key == base_item.dedup_key,
                ComplianceItem.deleted_at.is_(None),
            )
        )
        if duplicate is not None:
            affected_items.append(duplicate)
            if candidate.action == "join_group":
                ensure_duplicate_group([base_item, duplicate], ctx=ctx, now=now)
            continue
        selected_text = candidate.selected_text.strip()
        status_value = base_item.status if candidate.action == "join_group" and base_item.status == "confirmed" else "pending_confirm"
        new_item = ComplianceItem(
            tenant_id=ctx.tenant_id,
            project_id=project_id,
            section_id=section_id,
            source_document_id=base_item.source_document_id,
            source_version_id=chunk.document_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type=base_item.item_type,
            requirement_text=selected_text,
            normalized_requirement=f"similar:{normalize_requirement_key(selected_text)}:{uuid.uuid4().hex[:8]}",
            dedup_key=base_item.dedup_key or normalize_requirement_key(selected_text),
            duplicate_group_id=base_item.duplicate_group_id if candidate.action == "join_group" else None,
            duplicate_group_status="confirmed" if candidate.action == "join_group" else None,
            duplicate_group_confirmed_at=now if candidate.action == "join_group" else None,
            duplicate_group_confirmed_by=ctx.user_id if candidate.action == "join_group" else None,
            response_suggestion=base_item.response_suggestion,
            evidence_text=selected_text,
            explanation_json={
                "rule_code": "MANUAL-SIMILAR-APPLY",
                "rule_reason": "审核人确认相似片段后补入矩阵。",
                "source_quote": selected_text,
                "base_item_id": str(base_item.id),
                "similar_candidate_key": candidate.candidate_key,
                "needs_human_review": candidate.action != "join_group",
            },
            selected_text=selected_text,
            selection_start_offset=candidate.selection_start_offset,
            selection_end_offset=candidate.selection_end_offset,
            source_create_method="similar_candidate",
            status=status_value,
            risk_level=base_item.risk_level,
            is_mandatory=base_item.is_mandatory,
            is_batch_confirm_allowed=base_item.risk_level != "high" and not base_item.is_mandatory,
            owner_user_id=base_item.owner_user_id or ctx.user_id,
            confidence_score=base_item.confidence_score,
            confirmed_by=ctx.user_id if status_value == "confirmed" else None,
            confirmed_at=now if status_value == "confirmed" else None,
            created_by=ctx.user_id,
            modified_by=ctx.user_id,
            modified_at=now,
            modify_reason=payload.reason.strip(),
        )
        db.add(new_item)
        db.flush()
        if candidate.action == "join_group":
            ensure_duplicate_group([base_item, new_item], ctx=ctx, now=now)
        created_items.append(new_item)
        affected_items.append(new_item)

    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.similar_candidate_applied",
        object_type="compliance_item",
        object_id=base_item.id,
        before_json={"base_item": item_summary(base_item)},
        after_json={
            "created_items": [item_summary(item) for item in created_items],
            "affected_items": [item_summary(item) for item in affected_items],
            "skipped": skipped,
        },
        reason=payload.reason.strip(),
    )
    db.commit()
    return DuplicateGroupActionResult(
        duplicate_group_id=base_item.duplicate_group_id,
        affected_item_count=len({item.id for item in affected_items}),
        items=read_items(db, affected_items),
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/duplicate-group/confirm",
    response_model=DuplicateGroupActionResult,
)
def confirm_duplicate_group(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DuplicateGroupActionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DuplicateGroupActionResult:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    if payload.item_ids:
        unique_ids = list(dict.fromkeys(payload.item_ids))
        items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == ctx.tenant_id,
                ComplianceItem.project_id == project_id,
                ComplianceItem.section_id == section_id,
                ComplianceItem.id.in_(unique_ids),
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
        if len(items) != len(unique_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Some group items were not found")
        if item.id not in {group_item.id for group_item in items}:
            items.append(item)
    elif item.dedup_key:
        items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == ctx.tenant_id,
                ComplianceItem.project_id == project_id,
                ComplianceItem.section_id == section_id,
                ComplianceItem.dedup_key == item.dedup_key,
                ComplianceItem.duplicate_group_status.is_distinct_from("unlinked"),
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
    else:
        items = [item]
    if len(items) < 2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least two items are required to confirm a duplicate group")

    before_items = [compliance_item_snapshot(group_item) for group_item in items]
    group_id = ensure_duplicate_group(items, ctx=ctx, now=datetime.now(UTC))
    after_items = [compliance_item_snapshot(group_item) for group_item in items]
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.duplicate_group_confirmed",
        object_type="compliance_item_duplicate_group",
        object_id=group_id,
        before_json={"items": before_items},
        after_json={"items": after_items, "duplicate_group_id": str(group_id)},
        reason=payload.reason.strip(),
    )
    db.commit()
    return DuplicateGroupActionResult(
        duplicate_group_id=group_id,
        affected_item_count=len(items),
        items=read_items(db, items),
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/duplicate-group/unlink",
    response_model=DuplicateGroupActionResult,
)
def unlink_duplicate_group_item(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DuplicateGroupActionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DuplicateGroupActionResult:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    before = compliance_item_snapshot(item)
    previous_group_id = item.duplicate_group_id
    item.duplicate_group_id = None
    item.duplicate_group_status = "unlinked"
    item.duplicate_group_confirmed_at = None
    item.duplicate_group_confirmed_by = None
    item.modified_by = ctx.user_id
    item.modified_at = datetime.now(UTC)
    item.modify_reason = payload.reason.strip()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.duplicate_group_unlinked",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json={**compliance_item_snapshot(item), "previous_duplicate_group_id": str(previous_group_id) if previous_group_id else None},
        reason=payload.reason.strip(),
    )
    db.commit()
    return DuplicateGroupActionResult(
        duplicate_group_id=None,
        affected_item_count=1,
        items=[compliance_item_read_from_item(db, item)],
    )


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/duplicate-group/split",
    response_model=DuplicateGroupActionResult,
)
def split_duplicate_group_item(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DuplicateGroupActionRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> DuplicateGroupActionResult:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    before = compliance_item_snapshot(item)
    now = datetime.now(UTC)
    new_group_id = uuid.uuid4()
    item.duplicate_group_id = new_group_id
    item.duplicate_group_status = "confirmed"
    item.duplicate_group_confirmed_at = now
    item.duplicate_group_confirmed_by = ctx.user_id
    item.modified_by = ctx.user_id
    item.modified_at = now
    item.modify_reason = payload.reason.strip()
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.duplicate_group_split",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json=compliance_item_snapshot(item),
        reason=payload.reason.strip(),
    )
    db.commit()
    return DuplicateGroupActionResult(
        duplicate_group_id=new_group_id,
        affected_item_count=1,
        items=[compliance_item_read_from_item(db, item)],
    )


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
    cascade_items: list[ComplianceItem] = [item]
    if payload.cascade and item.duplicate_group_id is not None and item.duplicate_group_status == "confirmed":
        cascade_items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == ctx.tenant_id,
                ComplianceItem.project_id == project_id,
                ComplianceItem.section_id == section_id,
                ComplianceItem.duplicate_group_id == item.duplicate_group_id,
                ComplianceItem.duplicate_group_status == "confirmed",
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
    if any(confirmation_requires_source_verified(group_item) for group_item in cascade_items) and not payload.source_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="High-risk, mandatory, or qualification items require source verification before confirmation",
        )

    before_items = [compliance_item_snapshot(group_item) for group_item in cascade_items]
    now = datetime.now(UTC)
    for group_item in cascade_items:
        group_item.status = "confirmed"
        group_item.confirmed_by = ctx.user_id
        group_item.confirmed_at = now
        group_item.modified_by = ctx.user_id
        group_item.modified_at = now
        group_item.modify_reason = payload.reason.strip()
        refresh_batch_confirm_guard(group_item)
    after_items = [compliance_item_snapshot(group_item) for group_item in cascade_items]
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.item_confirmed",
        object_type="compliance_item",
        object_id=item.id,
        before_json={"items": before_items},
        after_json={
            "items": after_items,
            "source_verified": payload.source_verified,
            "cascade": payload.cascade,
        },
        reason=payload.reason.strip(),
    )
    if len(cascade_items) > 1:
        add_matrix_audit_log(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
            action="matrix.cascade_confirmed",
            object_type="compliance_item_duplicate_group",
            object_id=item.duplicate_group_id,
            before_json={"items": before_items},
            after_json={
                "items": after_items,
                "trigger_item_id": str(item.id),
                "affected_item_count": len(cascade_items),
            },
            reason=payload.reason.strip(),
        )
    db.commit()
    db.refresh(item)
    document = db.get(Document, item.source_document_id)
    version = db.get(DocumentVersion, item.source_version_id)
    source_chunk = db.get(DocumentChunk, item.source_chunk_id) if item.source_chunk_id else None
    owner_name = db.scalar(select(User.name).where(User.id == item.owner_user_id)) if item.owner_user_id else None
    evidence_count, evidence_summary = enterprise_evidence_summary_for_item(db, item.tenant_id, item.id)
    return compliance_item_read_payload(
        item=item,
        source_document_title=document.title if document else None,
        source_version_label=version.version_label if version else None,
        owner_name=owner_name,
        source_chunk=source_chunk,
        evidence_count=evidence_count,
        evidence_summary=evidence_summary,
        duplicate_group_count=duplicate_group_count_for_item(db, item),
        cascade_affected_count=max(0, len(cascade_items) - 1),
        cascade_affected_items=[item_summary(group_item) for group_item in cascade_items if group_item.id != item.id],
    )


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
    return [evidence_binding_read_from_binding(binding) for binding in dedupe_evidence_bindings(list(bindings))]


@router.post(
    "/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-not-required",
    response_model=ComplianceItemRead,
)
def waive_compliance_evidence_requirement(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ComplianceEvidenceWaiveRequest,
    db: Annotated[Session, Depends(get_db)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> ComplianceItemRead:
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
    before = compliance_item_snapshot(item)
    now = datetime.now(UTC)
    reason = payload.reason.strip()
    explanation = dict(item.explanation_json or {})
    explanation["enterprise_evidence_not_required"] = True
    explanation["enterprise_evidence_not_required_reason"] = reason
    explanation["enterprise_evidence_not_required_at"] = now.isoformat()
    explanation["enterprise_evidence_not_required_by"] = str(ctx.user_id)
    item.explanation_json = explanation
    if item.status == "needs_material":
        item.status = "pending_confirm"
    item.modified_by = ctx.user_id
    item.modified_at = now
    item.modify_reason = reason
    refresh_batch_confirm_guard(item)
    qualification_refresh = None
    if item.item_type == "qualification":
        db.flush()
        qualification_refresh = refresh_qualification_after_evidence_change(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
        )
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.evidence_not_required",
        object_type="compliance_item",
        object_id=item.id,
        before_json=before,
        after_json={
            "item": compliance_item_snapshot(item),
            "qualification_refresh": qualification_refresh,
        },
        reason=reason,
    )
    db.commit()
    db.refresh(item)
    return compliance_item_read_from_item(db, item)


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

    active_bindings = list(
        db.scalars(
            select(ComplianceEvidenceBinding).where(
                ComplianceEvidenceBinding.tenant_id == ctx.tenant_id,
                ComplianceEvidenceBinding.compliance_item_id == item_id,
                ComplianceEvidenceBinding.status == "active",
            )
        ).all()
    )
    material_key = enterprise_material_identity_key(material)
    duplicate = next(
        (
            binding
            for binding in active_bindings
            if binding.enterprise_material_id == payload.enterprise_material_id
            or material_snapshot_identity_key(binding.material_snapshot) == material_key
        ),
        None,
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Equivalent material already bound")

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

    if enterprise_evidence_not_required(item):
        explanation = dict(item.explanation_json or {})
        explanation["enterprise_evidence_not_required"] = False
        explanation["enterprise_evidence_not_required_cleared_at"] = datetime.now(UTC).isoformat()
        explanation["enterprise_evidence_not_required_cleared_by"] = str(ctx.user_id)
        item.explanation_json = explanation

    if item.status == "needs_material":
        now = datetime.now(UTC)
        item.status = "pending_confirm"
        item.modified_by = ctx.user_id
        item.modified_at = now
        item.modify_reason = payload.reason.strip()
        refresh_batch_confirm_guard(item)

    db.flush()
    qualification_refresh = None
    if item.item_type == "qualification":
        qualification_refresh = refresh_qualification_after_evidence_change(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
        )
    after = {
        "item": compliance_item_snapshot(item),
        "binding": evidence_binding_snapshot(binding),
        "material": enterprise_material_snapshot(material),
        "qualification_refresh": qualification_refresh,
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
    item = get_compliance_item_or_404(db, ctx, project_id, section_id, item_id)
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
    qualification_refresh = None
    if item.item_type == "qualification":
        qualification_refresh = refresh_qualification_after_evidence_change(
            db,
            ctx,
            project_id=project_id,
            section_id=section_id,
        )
    add_matrix_audit_log(
        db,
        ctx,
        project_id=project_id,
        section_id=section_id,
        action="matrix.evidence_unbound",
        object_type="compliance_evidence_binding",
        object_id=binding.id,
        before_json=before,
        after_json={
            "binding": evidence_binding_snapshot(binding),
            "qualification_refresh": qualification_refresh,
        },
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
