from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.document import DocumentChunkRead


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    purchaser: str | None
    agency: str | None
    budget_amount: Decimal | None
    region_code: str | None
    industry_code: str | None
    status: str
    bid_deadline_at: datetime | None
    section_count: int
    compliance_item_count: int
    high_risk_count: int
    pending_confirm_count: int


class ProjectDetail(ProjectSummary):
    notice_url: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    purchaser: str | None = Field(default=None, max_length=300)
    agency: str | None = Field(default=None, max_length=300)
    budget_amount: Decimal | None = None
    region_code: str | None = Field(default=None, max_length=64)
    industry_code: str | None = Field(default=None, max_length=64)
    notice_url: str | None = None
    bid_deadline_at: datetime | None = None
    section_code: str | None = Field(default=None, max_length=64)
    section_name: str | None = Field(default=None, max_length=300)
    section_budget_amount: Decimal | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    purchaser: str | None = Field(default=None, max_length=300)
    agency: str | None = Field(default=None, max_length=300)
    budget_amount: Decimal | None = None
    region_code: str | None = Field(default=None, max_length=64)
    industry_code: str | None = Field(default=None, max_length=64)
    notice_url: str | None = None
    bid_deadline_at: datetime | None = None
    reason: str = Field(default="更新项目关键信息", min_length=2, max_length=1000)


class ProjectImportProjectDraft(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    purchaser: str | None = Field(default=None, max_length=300)
    agency: str | None = Field(default=None, max_length=300)
    budget_amount: Decimal | None = None
    region_code: str | None = Field(default=None, max_length=64)
    industry_code: str | None = Field(default=None, max_length=64)
    notice_url: str | None = None
    bid_deadline_at: datetime | None = None


class ProjectImportSectionDraft(BaseModel):
    code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=300)
    budget_amount: Decimal | None = None
    bid_deadline_at: datetime | None = None


class ProjectImportSourceRead(BaseModel):
    draft_id: uuid.UUID
    source_type: str
    source_site: str | None
    source_url: str | None
    original_filename: str
    content_type: str | None
    file_ext: str | None
    file_size: int
    sha256: str
    staged_object_key: str
    acquired_at: datetime


class ProjectImportDraftRead(BaseModel):
    source: ProjectImportSourceRead
    project: ProjectImportProjectDraft
    sections: list[ProjectImportSectionDraft]
    confidence: dict[str, float]
    warnings: list[str]
    preview_text: str


class ProjectImportUrlRequest(BaseModel):
    source_url: str = Field(min_length=1, max_length=4000)
    source_site: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)


class ProjectImportConfirmRequest(BaseModel):
    source: ProjectImportSourceRead
    project: ProjectImportProjectDraft
    sections: list[ProjectImportSectionDraft] = Field(min_length=1, max_length=20)
    auto_parse: bool = True
    auto_generate_matrix: bool = True
    async_processing: bool = False


class ProjectImportConfirmRead(BaseModel):
    project: ProjectDetail
    section_id: uuid.UUID
    document_id: uuid.UUID
    parse_task_id: uuid.UUID | None
    matrix_task_id: uuid.UUID | None


class SectionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    code: str | None
    name: str
    budget_amount: Decimal | None
    status: str
    bid_deadline_at: datetime | None
    document_count: int
    compliance_item_count: int
    high_risk_count: int
    pending_confirm_count: int
    created_at: datetime
    updated_at: datetime


class SectionCreateRequest(BaseModel):
    code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=300)
    budget_amount: Decimal | None = None
    bid_deadline_at: datetime | None = None


class SectionUpdateRequest(BaseModel):
    code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    budget_amount: Decimal | None = None
    bid_deadline_at: datetime | None = None
    reason: str = Field(default="更新标段关键信息", min_length=2, max_length=1000)


class ComplianceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    source_document_id: uuid.UUID
    source_document_title: str | None
    source_version_id: uuid.UUID
    source_version_label: str | None
    source_chunk_id: uuid.UUID | None
    source_page_no: int | None
    source_heading_path: str | None = None
    source_chunk_index: int | None = None
    source_content_text: str | None = None
    source_bbox_json: dict[str, Any] | None = None
    source_table_json: dict[str, Any] | None = None
    item_type: str
    requirement_text: str
    normalized_requirement: str | None
    response_suggestion: str | None
    evidence_text: str | None
    rule_explanation: dict[str, Any] | None = None
    dedup_key: str | None = None
    duplicate_group_id: uuid.UUID | None = None
    duplicate_group_status: str | None = None
    duplicate_group_confirmed_at: datetime | None = None
    duplicate_group_confirmed_by: uuid.UUID | None = None
    duplicate_group_count: int = 0
    selected_text: str | None = None
    selection_start_offset: int | None = None
    selection_end_offset: int | None = None
    source_create_method: str | None = None
    review_hint: str | None = None
    classification_reason: str | None = None
    split_reason: str | None = None
    source_quote: str | None = None
    needs_human_review: bool = False
    enterprise_evidence_count: int = 0
    enterprise_evidence_summary: str | None = None
    enterprise_evidence_not_required: bool = False
    enterprise_evidence_not_required_reason: str | None = None
    priority_rank: int = 3
    priority_label: str = "P3-一般响应"
    priority_reason: str = "普通响应项，按常规流程处理"
    status: str
    risk_level: str
    is_mandatory: bool
    is_batch_confirm_allowed: bool
    owner_user_id: uuid.UUID | None
    owner_name: str | None
    confidence_score: Decimal | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    modified_by: uuid.UUID | None
    modified_at: datetime | None
    modify_reason: str | None
    cascade_affected_count: int = 0
    cascade_affected_items: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ComplianceMatrixGenerateRequest(BaseModel):
    document_id: uuid.UUID | None = None
    document_version_id: uuid.UUID | None = None
    force: bool = False
    async_processing: bool = False


class ComplianceMatrixAutoResolveRequest(BaseModel):
    document_id: uuid.UUID | None = None
    document_version_id: uuid.UUID | None = None
    async_processing: bool = True


class AgentAssistRunRequest(BaseModel):
    async_processing: bool = False
    force: bool = True


class AgentAssistSummaryRead(BaseModel):
    project_id: uuid.UUID
    section_id: uuid.UUID
    task_id: uuid.UUID | None = None
    run_key: str
    total_count: int = 0
    open_count: int = 0
    auto_passed_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    matrix_review_count: int = 0
    evidence_binding_count: int = 0
    qualification_technical_count: int = 0
    missing_evidence_count: int = 0
    qualification_decision_count: int = 0
    technical_review_count: int = 0
    llm_advice_count: int = 0
    suggested_actions: list[str] = Field(default_factory=list)


class AgentReviewItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    async_task_id: uuid.UUID | None
    run_key: str
    step: str
    action: str
    status: str
    severity: str
    title: str
    detail: str | None
    object_type: str
    object_id: uuid.UUID | None
    compliance_item_id: uuid.UUID | None
    enterprise_material_id: uuid.UUID | None
    qualification_evaluation_id: uuid.UUID | None
    qualification_decision_id: uuid.UUID | None
    draft_block_id: uuid.UUID | None
    confidence_score: Decimal | None
    requires_human: bool
    escalation_reasons: list[str] | None
    recommendation_json: dict[str, Any] | None
    source_ref_json: dict[str, Any] | None
    triggered_by: uuid.UUID | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime


class AgentReviewItemDecisionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)
    source_verified: bool = False


class PreflightCheckItem(BaseModel):
    code: str
    title: str
    status: str
    count: int = 0
    message: str
    action_label: str | None = None
    target: str | None = None


class PreflightCheckRead(BaseModel):
    project_id: uuid.UUID
    section_id: uuid.UUID
    status: str
    summary: str
    latest_document_version_id: uuid.UUID | None = None
    latest_document_version_label: str | None = None
    matrix_version_ids: list[uuid.UUID] = Field(default_factory=list)
    matrix_version_labels: list[str] = Field(default_factory=list)
    matrix_outdated: bool = False
    outdated_item_count: int = 0
    pending_qualification_count: int = 0
    high_risk_unconfirmed_count: int = 0
    mandatory_missing_evidence_count: int = 0
    technical_pending_count: int = 0
    missing_evidence_count: int = 0
    unverified_fact_count: int = 0
    failed_fact_count: int = 0
    pending_fact_check_chapter_count: int = 0
    pending_approval_count: int = 0
    rejected_approval_count: int = 0
    missing_bid_deadline: bool = False
    missing_deadline_item: bool = False
    checks: list[PreflightCheckItem] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class ComplianceItemUpdateRequest(BaseModel):
    requirement_text: str | None = Field(default=None, min_length=1)
    response_suggestion: str | None = None
    status: str | None = None
    risk_level: str | None = None
    is_mandatory: bool | None = None
    owner_user_id: uuid.UUID | None = None
    reason: str = Field(min_length=2, max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"draft", "pending_confirm", "needs_material", "rejected", "superseded"}
        if value not in allowed:
            raise ValueError("状态只能通过编辑设置为草稿、待确认、缺材料、不适用或已替代")
        return value

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"low", "medium", "high"}
        if value not in allowed:
            raise ValueError("风险等级必须是 low、medium 或 high")
        return value


class ComplianceItemConfirmRequest(BaseModel):
    reason: str = Field(default="人工逐条确认合规矩阵项", min_length=2, max_length=1000)
    source_verified: bool = False
    cascade: bool = True


class ComplianceItemFromSourceRequest(BaseModel):
    source_chunk_id: uuid.UUID
    selected_text: str = Field(min_length=2, max_length=8000)
    selection_start_offset: int | None = Field(default=None, ge=0)
    selection_end_offset: int | None = Field(default=None, ge=0)
    item_type: str = "mandatory_response"
    risk_level: str = "medium"
    is_mandatory: bool = True
    response_suggestion: str | None = Field(default=None, max_length=4000)
    reason: str = Field(default="人工从原文新增合规矩阵项", min_length=2, max_length=1000)

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value: str) -> str:
        allowed = {
            "qualification",
            "mandatory_response",
            "format",
            "deadline",
            "scoring",
            "reference_info",
            "technical_response",
            "other",
        }
        if value not in allowed:
            raise ValueError("不支持的合规项类型")
        return value

    @field_validator("risk_level")
    @classmethod
    def validate_source_risk_level(cls, value: str) -> str:
        if value not in {"low", "medium", "high"}:
            raise ValueError("风险等级必须是 low、medium 或 high")
        return value


class TextDiffSegment(BaseModel):
    operation: str
    base_text: str | None = None
    candidate_text: str | None = None


class SimilarCandidateRead(BaseModel):
    candidate_key: str
    source_chunk_id: uuid.UUID
    source_chunk_index: int
    page_no: int | None = None
    heading_path: str | None = None
    selected_text: str
    selection_start_offset: int | None = None
    selection_end_offset: int | None = None
    similarity: float
    match_type: str
    diff_segments: list[TextDiffSegment] = Field(default_factory=list)
    existing_item_id: uuid.UUID | None = None


class ComplianceItemFromSourceResult(BaseModel):
    item: ComplianceItemRead
    similar_candidates: list[SimilarCandidateRead] = Field(default_factory=list)


class SimilarCandidateApplyItem(BaseModel):
    candidate_key: str
    source_chunk_id: uuid.UUID
    selected_text: str = Field(min_length=2, max_length=8000)
    selection_start_offset: int | None = Field(default=None, ge=0)
    selection_end_offset: int | None = Field(default=None, ge=0)
    action: str

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value not in {"join_group", "create_independent", "skip"}:
            raise ValueError("action 必须是 join_group、create_independent 或 skip")
        return value


class SimilarCandidateApplyRequest(BaseModel):
    candidates: list[SimilarCandidateApplyItem] = Field(min_length=1, max_length=50)
    reason: str = Field(default="人工确认相似片段补票", min_length=2, max_length=1000)


class DuplicateGroupActionRequest(BaseModel):
    item_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    reason: str = Field(default="人工确认重复要求关联组", min_length=2, max_length=1000)


class DuplicateGroupActionResult(BaseModel):
    duplicate_group_id: uuid.UUID | None = None
    affected_item_count: int
    items: list[ComplianceItemRead] = Field(default_factory=list)


class MatrixReviewStats(BaseModel):
    total_items: int
    confirmed_items: int
    high_risk_total: int
    high_risk_confirmed: int
    uncovered_chunk_count: int
    duplicate_candidate_group_count: int
    duplicate_confirmed_group_count: int


class MatrixReviewUncoveredChunkRead(BaseModel):
    chunk: DocumentChunkRead
    reason: str


class MatrixReviewDuplicateGroupRead(BaseModel):
    group_key: str
    group_type: str
    status: str
    item_ids: list[uuid.UUID]
    item_count: int
    representative_text: str


class ReviewDocumentPageMargins(BaseModel):
    top: float | None = None
    right: float | None = None
    bottom: float | None = None
    left: float | None = None


class ReviewDocumentPage(BaseModel):
    page_no: int
    width: float | None = None
    height: float | None = None


class ReviewDocumentRunStyle(BaseModel):
    font_family: str | None = None
    font_size_pt: float | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = None


class ReviewDocumentParagraphStyle(BaseModel):
    style_id: str | None = None
    style_name: str | None = None
    alignment: str | None = None
    indent_left_pt: float | None = None
    first_line_indent_pt: float | None = None
    line_spacing: float | None = None


class ReviewDocumentRun(BaseModel):
    text: str
    style: ReviewDocumentRunStyle = Field(default_factory=ReviewDocumentRunStyle)


class ReviewDocumentParagraph(BaseModel):
    text: str
    runs: list[ReviewDocumentRun] = Field(default_factory=list)
    style: ReviewDocumentParagraphStyle = Field(default_factory=ReviewDocumentParagraphStyle)


class ReviewDocumentTableCell(BaseModel):
    paragraphs: list[ReviewDocumentParagraph] = Field(default_factory=list)


class ReviewDocumentTableRow(BaseModel):
    cells: list[ReviewDocumentTableCell] = Field(default_factory=list)


class ReviewDocumentBlock(BaseModel):
    id: str
    type: str
    chunk_id: uuid.UUID | None = None
    chunk_index: int | None = None
    page_no: int | None = None
    bbox_json: dict[str, Any] | None = None
    text: str = ""
    paragraph: ReviewDocumentParagraph | None = None
    rows: list[ReviewDocumentTableRow] = Field(default_factory=list)


class MatrixReviewHighlightRead(BaseModel):
    item_id: uuid.UUID
    chunk_id: uuid.UUID
    start_offset: int
    end_offset: int
    risk_level: str
    status: str
    item_type: str
    match_source: str
    text: str


class MatrixReviewDocumentRead(BaseModel):
    mode: str
    document_id: uuid.UUID | None = None
    title: str | None = None
    original_filename: str | None = None
    version_id: uuid.UUID | None = None
    version_label: str | None = None
    reason: str | None = None
    page_margins: ReviewDocumentPageMargins | None = None
    pages: list[ReviewDocumentPage] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    footers: list[str] = Field(default_factory=list)
    blocks: list[ReviewDocumentBlock] = Field(default_factory=list)


class MatrixReviewRead(BaseModel):
    chunks: list[DocumentChunkRead] = Field(default_factory=list)
    items: list[ComplianceItemRead] = Field(default_factory=list)
    stats: MatrixReviewStats
    uncovered_chunks: list[MatrixReviewUncoveredChunkRead] = Field(default_factory=list)
    duplicate_groups: list[MatrixReviewDuplicateGroupRead] = Field(default_factory=list)
    review_document: MatrixReviewDocumentRead | None = None
    highlights: list[MatrixReviewHighlightRead] = Field(default_factory=list)


class ComplianceItemAssignRequest(BaseModel):
    owner_user_id: uuid.UUID | None = None
    reason: str = Field(default="指派责任人", min_length=2, max_length=1000)


class ComplianceItemsBulkAssignRequest(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    owner_user_id: uuid.UUID | None = None
    reason: str = Field(default="批量指派责任人", min_length=2, max_length=1000)


class ComplianceItemsBulkConfirmRequest(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    reason: str = Field(default="批量确认低风险合规矩阵项", min_length=2, max_length=1000)


class ComplianceEvidenceBindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    compliance_item_id: uuid.UUID
    enterprise_material_id: uuid.UUID
    material_name: str | None
    material_type: str | None
    material_verification_status: str | None
    evidence_text: str
    confidence_score: Decimal | None
    bind_reason: str
    status: str
    created_by: uuid.UUID
    created_at: datetime
    deleted_by: uuid.UUID | None
    deleted_at: datetime | None


class ComplianceEvidenceBindRequest(BaseModel):
    enterprise_material_id: uuid.UUID
    evidence_text: str | None = Field(default=None, max_length=4000)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1)
    reason: str = Field(default="绑定企业资料作为响应证据", min_length=2, max_length=1000)


class ComplianceEvidenceCandidateRejectRequest(BaseModel):
    reason: str = Field(default="候选证据与当前条款不匹配", min_length=2, max_length=1000)


class ComplianceEvidenceCandidateRejectRead(BaseModel):
    audit_log_id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    compliance_item_id: uuid.UUID
    enterprise_material_id: uuid.UUID
    reason: str
    created_at: datetime


class ComplianceEvidenceWaiveRequest(BaseModel):
    reason: str = Field(default="人工判定该条款无需绑定企业资料证据", min_length=2, max_length=1000)


class ComplianceEvidenceUnbindRequest(BaseModel):
    reason: str = Field(default="解除企业资料证据绑定", min_length=2, max_length=1000)


class BusinessDraftEvidenceRefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chapter_id: uuid.UUID
    compliance_item_id: uuid.UUID | None
    evidence_binding_id: uuid.UUID | None
    enterprise_material_id: uuid.UUID | None
    source_type: str
    source_snapshot: dict[str, Any]
    quote_text: str | None
    created_at: datetime


class DraftFactCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chapter_id: uuid.UUID
    fact_type: str
    fact_text: str
    check_status: str
    risk_level: str
    evidence_text: str | None
    detail: str
    created_at: datetime


class BusinessDraftChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    chapter_type: str
    title: str
    sort_order: int
    content_text: str
    outline_json: dict[str, Any] | None
    evidence_summary_json: dict[str, Any] | None
    fact_check_status: str
    status: str
    version_no: int
    generated_from_json: dict[str, Any] | None
    edit_reason: str | None
    created_at: datetime
    updated_at: datetime
    evidence_refs: list[BusinessDraftEvidenceRefRead] = Field(default_factory=list)
    fact_checks: list[DraftFactCheckRead] = Field(default_factory=list)


class BusinessDraftGenerateRequest(BaseModel):
    force: bool = True


class OutlineChapterInput(BaseModel):
    """One chapter in a manually edited outline plan (MVP1.3 enhancement).

    The ordered list fully determines the chapter plan when provided: list
    position is the sort order, ``title`` renames the chapter, omitting a
    profile chapter removes it, and ``custom`` marks a user-added chapter that
    carries no compliance items (placeholder content the author fills in).
    """

    section_type: str = Field(min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=300)
    custom: bool = False

    @field_validator("section_type")
    @classmethod
    def strip_section_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("section_type 不能为空")
        return normalized

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AuthorDirectiveInput(BaseModel):
    """One author instruction-layer directive (MVP1.3 instruction layer).

    Directives steer *generation* without mutating the immutable fact layer.
    ``scope`` is ``"pack"`` (applies to every chapter) or a concrete
    ``section_type``. Three types are allowed: ``style`` (pure wording),
    ``emphasis`` (content emphasis) and ``mandatory_text`` (forced phrasing that
    is emitted verbatim as a confirmable block and still fact-checked).
    """

    scope: str = Field(default="pack", min_length=1, max_length=128)
    directive_type: str = Field(pattern="^(style|emphasis|mandatory_text)$")
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("scope")
    @classmethod
    def strip_scope(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("scope 不能为空")
        return normalized

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("指令内容不能为空")
        return normalized


class BusinessDraftDirectivesRequest(BaseModel):
    """Replace the instruction layer of a confirmed ContextPack.

    The full directive list is sent each time (declarative replace, not patch).
    Applying it triggers a *lightweight rebuild*: the prior fact snapshot is
    reused verbatim (no upstream re-query) and only the directives change, so a
    new immutable pack version is produced while facts stay frozen.
    """

    directives: list[AuthorDirectiveInput] = Field(default_factory=list, max_length=200)


class BusinessDraftContextPackRequest(BaseModel):
    profile_id: str = Field(default="engineering_construction_business_v1", max_length=128)
    section_types: list[str] | None = Field(default=None, max_length=50)
    outline: list[OutlineChapterInput] | None = Field(default=None, max_length=80)
    directives: list[AuthorDirectiveInput] | None = Field(default=None, max_length=200)

    @field_validator("section_types")
    @classmethod
    def normalize_section_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [item.strip() for item in value if item.strip()]
        return normalized or None

    @field_validator("outline")
    @classmethod
    def validate_outline(
        cls, value: list[OutlineChapterInput] | None
    ) -> list[OutlineChapterInput] | None:
        if not value:
            return None
        seen: set[str] = set()
        for chapter in value:
            if chapter.section_type in seen:
                raise ValueError(f"章节类型重复：{chapter.section_type}")
            seen.add(chapter.section_type)
            if chapter.custom and not chapter.title:
                raise ValueError(f"自定义章节需提供标题：{chapter.section_type}")
        return value


class BusinessDraftContextPackPreviewRead(BaseModel):
    profile_id: str
    profile_version: str
    schema_version: str
    readiness_status: str
    context_json: dict[str, Any]
    readiness_json: dict[str, Any]
    outline_plan_json: dict[str, Any]


class TenderDirectoryChapterRead(BaseModel):
    """招标文件推导出的单个目录章节（可直接转 OutlineChapterInput）。"""

    section_type: str
    title: str
    custom: bool = False
    mapped_from: str = "custom"
    attachments: list[str] = Field(default_factory=list)


class BusinessDraftDirectoryDeriveRead(BaseModel):
    """从招标文件推导建议目录的结果（L2 骨架 + L1 采购信号）。"""

    available: bool
    reason: str | None = None
    procurement_method: str | None = None
    document_term: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    chapters: list[TenderDirectoryChapterRead] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)


class SectionQualityCheckRead(BaseModel):
    code: str
    title: str
    status: str
    message: str
    category: str
    count: int = 0
    action_label: str | None = None
    target: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)


class SectionQualityMaterialRead(BaseModel):
    material_id: str
    material_name: str
    material_type: str | None = None
    verification_status: str | None = None
    data_level: str | None = None
    certificate_no: str | None = None
    evidence_text: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    selected_for_export: bool = False
    embeddable: bool = False
    embed_status: str | None = None
    embed_reason: str | None = None


class SectionQualitySummaryRead(BaseModel):
    project_id: uuid.UUID
    section_id: uuid.UUID
    status: str
    status_label: str
    summary: str
    generated_at: datetime
    checks: list[SectionQualityCheckRead] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    pricing_summary: dict[str, Any] = Field(default_factory=dict)
    material_summary: dict[str, Any] = Field(default_factory=dict)
    export_preview: dict[str, Any] = Field(default_factory=dict)
    context_pack_status: dict[str, Any] | None = None
    draft_summary: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)


class TenderFormatDocxExportRequest(BaseModel):
    """导出按招标文件格式装配的 docx。

    review：审阅版，包含合规自检清单和附件状态；
    submission：正式版，不输出内部自检/风险/待办状态。
    """

    export_mode: str = Field(default="review", pattern="^(review|submission)$")
    profile_id: str | None = None


class DraftSectionContextPackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    context_pack_id: uuid.UUID
    section_type: str
    title: str
    sort_order: int
    generation_mode: str
    status: str
    context_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DraftBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    chapter_id: uuid.UUID | None
    section_context_pack_id: uuid.UUID | None
    block_type: str
    content_text: str
    sort_order: int
    links_json: dict[str, Any]
    fact_claims_json: list[dict[str, Any]] | None
    missing_fact_placeholders_json: list[dict[str, Any]] | None
    risk_flags_json: list[dict[str, Any]] | None
    review_status: str
    created_at: datetime
    updated_at: datetime


class DraftBlockUpdateRequest(BaseModel):
    review_status: str = Field(
        pattern="^(pending|covered|needs_evidence|needs_fact|needs_confirm|approved|rejected)$"
    )
    content_text: str | None = Field(default=None, min_length=1)
    reason: str = Field(default="更新结构化草稿 block 审阅状态", min_length=2, max_length=1000)


class DraftCoverageReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    context_pack_id: uuid.UUID | None
    status: str
    summary_json: dict[str, Any]
    issues_json: list[dict[str, Any]]
    created_at: datetime


class BusinessDraftContextPackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    profile_id: str
    profile_version: str
    schema_version: str
    status: str
    readiness_status: str
    context_json: dict[str, Any]
    readiness_json: dict[str, Any]
    outline_plan_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    section_context_packs: list[DraftSectionContextPackRead] = Field(default_factory=list)


class BusinessDraftContextPackGenerateRequest(BaseModel):
    allow_blocked_internal_draft: bool = False


class BusinessDraftContextPackGenerateResult(BaseModel):
    context_pack: BusinessDraftContextPackRead
    chapters: list[BusinessDraftChapterRead]
    blocks: list[DraftBlockRead]
    coverage_review: DraftCoverageReviewRead


class BusinessDraftExportRequest(BaseModel):
    risk_acceptance_reason: str | None = Field(default=None, max_length=1000)


class BusinessDraftChapterUpdateRequest(BaseModel):
    content_text: str = Field(min_length=1)
    reason: str = Field(min_length=2, max_length=1000)


class QualificationDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    recommendation: str
    status: str
    summary: str
    satisfied_count: int
    blocking_count: int
    missing_count: int
    pending_count: int
    reasons_json: dict[str, Any] | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    confirm_reason: str | None
    created_at: datetime
    updated_at: datetime


class QualificationDecisionConfirmRequest(BaseModel):
    reason: str = Field(default="人工确认参标建议", min_length=2, max_length=1000)


class ApprovalTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID | None
    task_type: str
    title: str
    description: str | None
    status: str
    related_object_type: str | None
    related_object_id: uuid.UUID | None
    assignee_user_id: uuid.UUID | None
    evidence_snapshot_json: dict[str, Any] | None
    decision_reason: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApprovalTaskCreateRequest(BaseModel):
    task_type: str = Field(max_length=64)
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    related_object_type: str | None = Field(default=None, max_length=100)
    related_object_id: uuid.UUID | None = None
    assignee_user_id: uuid.UUID | None = None
    due_at: datetime | None = None
    risk_acceptance_reason: str | None = Field(default=None, max_length=1000)


class ApprovalTaskDecisionRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=2, max_length=1000)


class QualificationEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID
    compliance_item_id: uuid.UUID
    requirement_text: str
    requirement_type: str
    extracted_requirement: dict[str, Any] | None
    evaluation_status: str
    risk_level: str
    is_blocking: bool
    matched_material_id: uuid.UUID | None
    matched_material_name: str | None
    matched_rule_code: str
    rule_version: str
    reason: str
    evidence_text: str | None
    missing_materials: list[str] | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    confirm_reason: str | None
    created_at: datetime
    updated_at: datetime


class QualificationEvaluationConfirmRequest(BaseModel):
    reason: str = Field(default="人工确认资格预评估结果", min_length=2, max_length=1000)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    section_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_name: str | None
    actor_type: str
    action: str
    object_type: str
    object_id: uuid.UUID | None
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    reason: str | None
    severity: str
    created_at: datetime


class ComplianceEvidenceFeedbackActionStats(BaseModel):
    action: str
    count: int
    latest_at: datetime | None


class ComplianceEvidenceFeedbackMaterialStats(BaseModel):
    enterprise_material_id: uuid.UUID
    material_name: str | None
    material_type: str | None
    bound_count: int
    rejected_count: int
    unbound_count: int
    latest_reason: str | None
    latest_action: str | None
    latest_at: datetime | None


class ComplianceEvidenceFeedbackItemStats(BaseModel):
    compliance_item_id: uuid.UUID
    requirement_text: str | None
    bound_count: int
    rejected_count: int
    unbound_count: int
    not_required_count: int
    replacement_count: int
    latest_reason: str | None
    latest_action: str | None
    latest_at: datetime | None


class ComplianceEvidenceFeedbackReportRead(BaseModel):
    project_id: uuid.UUID
    section_id: uuid.UUID
    total_feedback_count: int
    bound_count: int
    rejected_count: int
    unbound_count: int
    not_required_count: int
    replacement_count: int
    binding_acceptance_rate: float | None
    actions: list[ComplianceEvidenceFeedbackActionStats]
    materials_with_feedback: list[ComplianceEvidenceFeedbackMaterialStats]
    top_rejected_materials: list[ComplianceEvidenceFeedbackMaterialStats]
    items_with_feedback: list[ComplianceEvidenceFeedbackItemStats]
    generated_at: datetime


class ComplianceEvidenceEvaluationSampleRead(BaseModel):
    compliance_item_id: uuid.UUID
    requirement_text: str
    expected_material_ids: list[uuid.UUID]
    rejected_material_ids: list[uuid.UUID]
    candidate_material_ids: list[uuid.UUID]
    hit_at_k: bool
    recall_at_k: float
    precision_at_k: float
    false_positive_material_ids: list[uuid.UUID]
    missed_material_ids: list[uuid.UUID]
    misrecommendation_types: list[str]


class ComplianceEvidenceRetrievalEvaluationRead(BaseModel):
    project_id: uuid.UUID
    section_id: uuid.UUID
    top_k: int
    sample_count: int
    labeled_positive_count: int
    rejected_label_count: int
    recall_at_k: float | None
    precision_at_k: float | None
    topk_hit_rate: float | None
    binding_acceptance_rate: float | None
    false_positive_count: int
    missed_positive_count: int
    misrecommendation_counts: dict[str, int]
    samples: list[ComplianceEvidenceEvaluationSampleRead]
    generated_at: datetime


class ModelInvocationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    section_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_type: str
    task_type: str
    provider: str
    model_name: str
    complexity: str
    prompt_version: str
    input_summary: str
    output_summary: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    duration_ms: int | None
    status: str
    error_code: str | None
    error_message: str | None
    evidence_refs_json: dict[str, Any] | None
    created_at: datetime
