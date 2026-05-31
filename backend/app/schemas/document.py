from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_no: int
    version_label: str
    sha256: str
    parse_status: str
    parser_name: str | None
    parser_version: str | None
    frozen_at: datetime | None
    change_reason: str | None
    created_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID | None
    doc_type: str
    title: str
    source_type: str
    source_site: str | None
    source_url: str | None
    original_filename: str
    content_type: str | None
    file_ext: str | None
    file_size: int
    sha256: str
    status: str
    current_version_id: uuid.UUID | None
    acquired_at: datetime
    created_at: datetime
    updated_at: datetime
    current_version: DocumentVersionRead | None = None


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    section_id: uuid.UUID | None
    chunk_index: int
    page_no: int | None
    heading_path: str | None
    content_text: str
    content_hash: str
    bbox_json: dict[str, Any] | None
    table_json: dict[str, Any] | None
    created_at: datetime


class QualityIssueRead(BaseModel):
    severity: str = "medium"
    code: str
    message: str
    section_id: uuid.UUID | None = None
    section_index: int | None = None
    page_no: int | None = None
    source_chunk_index: int | None = None


class DocumentSemanticSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    section_id: uuid.UUID | None
    section_index: int
    title: str
    section_type: str
    start_page: int
    end_page: int
    confidence_score: float | None
    evidence: str | None
    status: str
    model_invocation_log_id: uuid.UUID | None
    raw_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class DocumentExtractionQualityReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID | None
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    section_id: uuid.UUID | None
    status: str
    issues_json: list[dict[str, Any]]
    summary_json: dict[str, Any]
    created_at: datetime


class DocumentManualRevisionChunk(BaseModel):
    chunk_index: int = Field(ge=1)
    page_no: int | None = Field(default=None, ge=1)
    heading_path: str | None = None
    content_text: str = Field(min_length=1)
    bbox_json: dict[str, Any] | None = None
    table_json: dict[str, Any] | None = None


class DocumentManualRevisionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)
    chunks: list[DocumentManualRevisionChunk] = Field(min_length=1)


class DocumentManualRevisionResult(BaseModel):
    document: DocumentRead
    source_version: DocumentVersionRead
    new_version: DocumentVersionRead
    chunks: list[DocumentChunkRead]


class AsyncTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    section_id: uuid.UUID | None
    task_type: str
    status: str
    idempotency_key: str
    progress: int
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    max_retries: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FileAcquisitionRequest(BaseModel):
    source_url: str = Field(min_length=1, max_length=4000)
    source_site: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    doc_type: str = "tender"


class FileAcquisitionTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task: AsyncTaskRead
    project_id: uuid.UUID
    section_id: uuid.UUID | None
    source_url: str
    normalized_url: str | None
    source_site: str | None
    fetch_method: str
    validation_status: str
    blocked_reason: str | None
    http_status: int | None
    content_type: str | None
    content_length: int | None
    target_document_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ParseTaskRequest(BaseModel):
    parser_type: str | None = None
    parser_name: str = "mvp-parser"
    parser_version: str | None = "0.1.0"
    options_json: dict[str, Any] | None = None


class ParseTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task: AsyncTaskRead
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    parser_type: str
    parser_name: str
    parser_version: str | None
    options_json: dict[str, Any] | None
    result_summary_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class ExportFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    section_id: uuid.UUID | None
    task_id: uuid.UUID | None
    export_type: str
    file_name: str
    sha256: str
    filter_json: dict[str, Any] | None
    source_snapshot_json: dict[str, Any] | None
    status: str
    created_at: datetime


class ComplianceMatrixExportRequest(BaseModel):
    status: str | None = None
    risk_level: str | None = None
    owner_user_id: uuid.UUID | None = None
    item_type: str | None = None
