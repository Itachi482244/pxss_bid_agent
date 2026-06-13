import { apiClient } from "./client";

export type ProjectSummary = {
  id: string;
  name: string;
  purchaser: string | null;
  agency: string | null;
  budget_amount: string | null;
  region_code: string | null;
  industry_code: string | null;
  status: string;
  bid_deadline_at: string | null;
  section_count: number;
  compliance_item_count: number;
  high_risk_count: number;
  pending_confirm_count: number;
};

export type ProjectDetail = ProjectSummary & {
  notice_url: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ProjectCreatePayload = {
  name: string;
  purchaser?: string | null;
  agency?: string | null;
  budget_amount?: string | null;
  region_code?: string | null;
  industry_code?: string | null;
  notice_url?: string | null;
  bid_deadline_at?: string | null;
  section_code?: string | null;
  section_name?: string | null;
  section_budget_amount?: string | null;
};

export type ProjectUpdatePayload = {
  name?: string | null;
  purchaser?: string | null;
  agency?: string | null;
  budget_amount?: string | null;
  region_code?: string | null;
  industry_code?: string | null;
  notice_url?: string | null;
  bid_deadline_at?: string | null;
  reason: string;
};

export type ProjectImportProjectDraft = {
  name: string;
  purchaser: string | null;
  agency: string | null;
  budget_amount: string | null;
  region_code: string | null;
  industry_code: string | null;
  notice_url: string | null;
  bid_deadline_at: string | null;
};

export type ProjectImportSectionDraft = {
  code: string | null;
  name: string;
  budget_amount: string | null;
  bid_deadline_at: string | null;
};

export type ProjectImportSource = {
  draft_id: string;
  source_type: string;
  source_site: string | null;
  source_url: string | null;
  original_filename: string;
  content_type: string | null;
  file_ext: string | null;
  file_size: number;
  sha256: string;
  staged_object_key: string;
  acquired_at: string;
};

export type ProjectImportDraft = {
  source: ProjectImportSource;
  project: ProjectImportProjectDraft;
  sections: ProjectImportSectionDraft[];
  confidence: Record<string, number>;
  warnings: string[];
  preview_text: string;
};

export type ProjectImportConfirmPayload = {
  source: ProjectImportSource;
  project: ProjectImportProjectDraft;
  sections: ProjectImportSectionDraft[];
  auto_parse?: boolean;
  auto_generate_matrix?: boolean;
  async_processing?: boolean;
};

export type ProjectImportConfirmResult = {
  project: ProjectDetail;
  section_id: string;
  document_id: string;
  parse_task_id: string | null;
  matrix_task_id: string | null;
};

export type SectionSummary = {
  id: string;
  project_id: string;
  code: string | null;
  name: string;
  budget_amount: string | null;
  status: string;
  bid_deadline_at: string | null;
  document_count: number;
  compliance_item_count: number;
  high_risk_count: number;
  pending_confirm_count: number;
  created_at: string;
  updated_at: string;
};

export type SectionUpdatePayload = {
  code?: string | null;
  name?: string | null;
  budget_amount?: string | null;
  bid_deadline_at?: string | null;
  reason: string;
};

export type DocumentVersion = {
  id: string;
  document_id: string;
  version_no: number;
  version_label: string;
  sha256: string;
  parse_status: string;
  parser_name: string | null;
  parser_version: string | null;
  frozen_at: string | null;
  change_reason: string | null;
  created_at: string;
};

export type ProjectDocument = {
  id: string;
  project_id: string;
  section_id: string | null;
  doc_type: string;
  title: string;
  source_type: string;
  source_site: string | null;
  source_url: string | null;
  original_filename: string;
  content_type: string | null;
  file_ext: string | null;
  file_size: number;
  sha256: string;
  status: string;
  current_version_id: string | null;
  acquired_at: string;
  created_at: string;
  updated_at: string;
  current_version: DocumentVersion | null;
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  document_version_id: string;
  section_id: string | null;
  chunk_index: number;
  page_no: number | null;
  heading_path: string | null;
  content_text: string;
  content_hash: string;
  bbox_json: Record<string, unknown> | null;
  table_json: Record<string, unknown> | null;
  created_at: string;
};

export type QualityIssue = {
  severity: "low" | "medium" | "high" | string;
  code: string;
  message: string;
  section_id?: string | null;
  section_index?: number | null;
  section_title?: string | null;
  page_no?: number | null;
  source_chunk_index?: number | null;
  suggested_requirement?: string | null;
  [key: string]: unknown;
};

export type DocumentSemanticSection = {
  id: string;
  document_id: string;
  document_version_id: string;
  section_id: string | null;
  section_index: number;
  title: string;
  section_type: string;
  start_page: number;
  end_page: number;
  confidence_score: number | null;
  evidence: string | null;
  status: string;
  model_invocation_log_id: string | null;
  raw_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type DocumentExtractionQualityReport = {
  id: string;
  task_id: string | null;
  document_id: string;
  document_version_id: string;
  section_id: string | null;
  status: "passed" | "blocked" | string;
  issues_json: QualityIssue[];
  summary_json: Record<string, unknown>;
  created_at: string;
};

export type DocumentManualRevisionPayload = {
  reason: string;
  chunks: Array<{
    chunk_index: number;
    page_no?: number | null;
    heading_path?: string | null;
    content_text: string;
    bbox_json?: Record<string, unknown> | null;
    table_json?: Record<string, unknown> | null;
  }>;
};

export type DocumentManualRevisionResult = {
  document: ProjectDocument;
  source_version: DocumentVersion;
  new_version: DocumentVersion;
  chunks: DocumentChunk[];
};

export type ComplianceItem = {
  id: string;
  project_id: string;
  section_id: string;
  source_document_id: string;
  source_document_title: string | null;
  source_version_id: string;
  source_version_label: string | null;
  source_chunk_id: string | null;
  source_page_no: number | null;
  source_heading_path: string | null;
  source_chunk_index: number | null;
  source_content_text: string | null;
  source_bbox_json: Record<string, unknown> | null;
  source_table_json: Record<string, unknown> | null;
  item_type: string;
  requirement_text: string;
  normalized_requirement: string | null;
  response_suggestion: string | null;
  evidence_text: string | null;
  rule_explanation: Record<string, unknown> | null;
  dedup_key: string | null;
  duplicate_group_id: string | null;
  duplicate_group_status: string | null;
  duplicate_group_confirmed_at: string | null;
  duplicate_group_confirmed_by: string | null;
  duplicate_group_count: number;
  selected_text: string | null;
  selection_start_offset: number | null;
  selection_end_offset: number | null;
  source_create_method: string | null;
  review_hint: string | null;
  classification_reason: string | null;
  split_reason: string | null;
  source_quote: string | null;
  needs_human_review: boolean;
  enterprise_evidence_count: number;
  enterprise_evidence_summary: string | null;
  enterprise_evidence_not_required: boolean;
  enterprise_evidence_not_required_reason: string | null;
  priority_rank: number;
  priority_label: string;
  priority_reason: string;
  status: string;
  risk_level: string;
  is_mandatory: boolean;
  is_batch_confirm_allowed: boolean;
  owner_user_id: string | null;
  owner_name: string | null;
  confidence_score: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  modified_by: string | null;
  modified_at: string | null;
  modify_reason: string | null;
  cascade_affected_count: number;
  cascade_affected_items: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
};

export type TextDiffSegment = {
  operation: "equal" | "delete" | "insert" | "replace";
  base_text: string | null;
  candidate_text: string | null;
};

export type SimilarCandidate = {
  candidate_key: string;
  source_chunk_id: string;
  source_chunk_index: number;
  page_no: number | null;
  heading_path: string | null;
  selected_text: string;
  selection_start_offset: number | null;
  selection_end_offset: number | null;
  similarity: number;
  match_type: string;
  diff_segments: TextDiffSegment[];
  existing_item_id: string | null;
};

export type MatrixReviewUncoveredChunk = {
  chunk: DocumentChunk;
  reason: string;
};

export type MatrixReviewDuplicateGroup = {
  group_key: string;
  group_type: "candidate" | "confirmed";
  status: string;
  item_ids: string[];
  item_count: number;
  representative_text: string;
};

export type ReviewDocumentPageMargins = {
  top: number | null;
  right: number | null;
  bottom: number | null;
  left: number | null;
};

export type ReviewDocumentPage = {
  page_no: number;
  width: number | null;
  height: number | null;
};

export type ReviewDocumentRunStyle = {
  font_family: string | null;
  font_size_pt: number | null;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  color: string | null;
};

export type ReviewDocumentParagraphStyle = {
  style_id: string | null;
  style_name: string | null;
  alignment: string | null;
  indent_left_pt: number | null;
  first_line_indent_pt: number | null;
  line_spacing: number | null;
};

export type ReviewDocumentRun = {
  text: string;
  style: ReviewDocumentRunStyle;
};

export type ReviewDocumentParagraph = {
  text: string;
  runs: ReviewDocumentRun[];
  style: ReviewDocumentParagraphStyle;
};

export type ReviewDocumentTableCell = {
  paragraphs: ReviewDocumentParagraph[];
};

export type ReviewDocumentTableRow = {
  cells: ReviewDocumentTableCell[];
};

export type ReviewDocumentBlock = {
  id: string;
  type: "paragraph" | "heading" | "table" | string;
  chunk_id: string | null;
  chunk_index: number | null;
  page_no: number | null;
  bbox_json: Record<string, unknown> | null;
  text: string;
  paragraph: ReviewDocumentParagraph | null;
  rows: ReviewDocumentTableRow[];
};

export type MatrixReviewHighlight = {
  item_id: string;
  chunk_id: string;
  start_offset: number;
  end_offset: number;
  risk_level: string;
  status: string;
  item_type: string;
  match_source: string;
  text: string;
};

export type MatrixReviewDocument = {
  mode: "word_xml" | "chunk_fallback" | string;
  document_id: string | null;
  title: string | null;
  original_filename: string | null;
  version_id: string | null;
  version_label: string | null;
  reason: string | null;
  page_margins: ReviewDocumentPageMargins | null;
  pages: ReviewDocumentPage[];
  headers: string[];
  footers: string[];
  blocks: ReviewDocumentBlock[];
};

export type MatrixReview = {
  chunks: DocumentChunk[];
  items: ComplianceItem[];
  stats: {
    total_items: number;
    confirmed_items: number;
    high_risk_total: number;
    high_risk_confirmed: number;
    uncovered_chunk_count: number;
    duplicate_candidate_group_count: number;
    duplicate_confirmed_group_count: number;
  };
  uncovered_chunks: MatrixReviewUncoveredChunk[];
  duplicate_groups: MatrixReviewDuplicateGroup[];
  review_document: MatrixReviewDocument | null;
  highlights: MatrixReviewHighlight[];
};

export type ComplianceItemFromSourceResult = {
  item: ComplianceItem;
  similar_candidates: SimilarCandidate[];
};

export type DuplicateGroupActionResult = {
  duplicate_group_id: string | null;
  affected_item_count: number;
  items: ComplianceItem[];
};

export type AuditLog = {
  id: string;
  project_id: string | null;
  section_id: string | null;
  actor_user_id: string | null;
  actor_name: string | null;
  actor_type: string;
  action: string;
  object_type: string;
  object_id: string | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  reason: string | null;
  severity: string;
  created_at: string;
};

export type ModelInvocationLog = {
  id: string;
  project_id: string | null;
  section_id: string | null;
  actor_user_id: string | null;
  actor_type: string;
  task_type: string;
  provider: string;
  model_name: string;
  complexity: string;
  prompt_version: string;
  input_summary: string;
  output_summary: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  duration_ms: number | null;
  status: string;
  error_code: string | null;
  error_message: string | null;
  evidence_refs_json: Record<string, unknown> | null;
  created_at: string;
};

export type AsyncTask = {
  id: string;
  project_id: string | null;
  section_id: string | null;
  task_type: string;
  status: string;
  idempotency_key: string;
  progress: number;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ParseTask = {
  id: string;
  task: AsyncTask;
  document_id: string;
  document_version_id: string;
  parser_type: string;
  parser_name: string;
  parser_version: string | null;
  options_json: Record<string, unknown> | null;
  result_summary_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type FileAcquisitionTask = {
  id: string;
  task: AsyncTask;
  project_id: string;
  section_id: string | null;
  source_url: string;
  normalized_url: string | null;
  source_site: string | null;
  fetch_method: string;
  validation_status: string;
  blocked_reason: string | null;
  http_status: number | null;
  content_type: string | null;
  content_length: number | null;
  target_document_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ExportFile = {
  id: string;
  project_id: string;
  section_id: string | null;
  task_id: string | null;
  export_type: string;
  file_name: string;
  sha256: string;
  filter_json: Record<string, unknown> | null;
  source_snapshot_json: Record<string, unknown> | null;
  status: string;
  created_at: string;
};

export type EnterpriseProfile = {
  id: string;
  tenant_id: string;
  company_name: string;
  unified_social_credit_code: string | null;
  legal_representative: string | null;
  registered_address: string | null;
  business_scope: string | null;
  region_preferences: string[] | null;
  industry_preferences: string[] | null;
  forbidden_rules: string[] | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

export type EnterpriseProfilePayload = {
  company_name: string;
  unified_social_credit_code?: string | null;
  legal_representative?: string | null;
  registered_address?: string | null;
  business_scope?: string | null;
  region_preferences?: string[] | null;
  industry_preferences?: string[] | null;
  forbidden_rules?: string[] | null;
};

export type EnterpriseMaterial = {
  id: string;
  tenant_id: string;
  material_type: string;
  name: string;
  issuing_authority: string | null;
  certificate_no: string | null;
  holder_name: string | null;
  project_name: string | null;
  amount: string | null;
  valid_from: string | null;
  valid_until: string | null;
  data_level: string;
  verification_status: string;
  structured_fields: Record<string, unknown> | null;
  evidence_text: string | null;
  file_name: string | null;
  content_type: string | null;
  file_size: number | null;
  sha256: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

export type EnterpriseMaterialHistoryExtractResult = {
  materials: EnterpriseMaterial[];
  source_file_name: string;
  source_file_size: number;
  source_sha256: string;
  parser_summary: Record<string, unknown>;
  extraction_method: string;
  warning_messages: string[];
  draft_count: number;
  text_block_count: number;
};

export type EnterpriseMaterialSearchResult = EnterpriseMaterial & {
  snippet: string | null;
  confidence_score: number;
  base_score: number | null;
  rerank_score: number | null;
  rerank_provider: string | null;
  rerank_model: string | null;
  rerank_used: boolean;
  rerank_fallback_used: boolean;
  rerank_error: string | null;
  chunk_id: string | null;
  data_level_allowed: boolean;
  recommend_reason: string | null;
  matched_terms: string[];
  material_status_hint: string | null;
};

export type EnterpriseMaterialIndexHealth = {
  status: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  fallback_chunk_count: number;
  rerank_provider: string;
  rerank_model: string;
  total_material_count: number;
  confirmed_material_count: number;
  indexed_material_count: number;
  unindexed_material_count: number;
  stale_material_count: number;
  chunk_count: number;
  coverage_rate: number;
  last_indexed_at: string | null;
  unindexed_materials: Record<string, unknown>[];
  stale_materials: Record<string, unknown>[];
};

export type EnterpriseMaterialIndexRebuildResult = {
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  rebuilt_material_count: number;
  rebuilt_chunk_count: number;
  removed_chunk_count: number;
  skipped_material_count: number;
  health: EnterpriseMaterialIndexHealth;
};

export type PreflightCheckItem = {
  code: string;
  title: string;
  status: "pass" | "warn" | "block";
  count: number;
  message: string;
  action_label: string | null;
  target: string | null;
};

export type PreflightCheck = {
  project_id: string;
  section_id: string;
  status: "pass" | "warn" | "block";
  summary: string;
  latest_document_version_id: string | null;
  latest_document_version_label: string | null;
  matrix_version_ids: string[];
  matrix_version_labels: string[];
  matrix_outdated: boolean;
  outdated_item_count: number;
  pending_qualification_count: number;
  high_risk_unconfirmed_count: number;
  mandatory_missing_evidence_count: number;
  technical_pending_count: number;
  missing_evidence_count: number;
  unverified_fact_count: number;
  failed_fact_count: number;
  pending_fact_check_chapter_count: number;
  pending_approval_count: number;
  rejected_approval_count: number;
  missing_bid_deadline: boolean;
  missing_deadline_item: boolean;
  checks: PreflightCheckItem[];
  suggested_actions: string[];
};

export type ComplianceEvidenceBinding = {
  id: string;
  project_id: string;
  section_id: string;
  compliance_item_id: string;
  enterprise_material_id: string;
  material_name: string | null;
  material_type: string | null;
  material_verification_status: string | null;
  evidence_text: string;
  confidence_score: string | null;
  bind_reason: string;
  status: string;
  created_by: string;
  created_at: string;
  deleted_by: string | null;
  deleted_at: string | null;
};

export type QualificationEvaluation = {
  id: string;
  project_id: string;
  section_id: string;
  compliance_item_id: string;
  requirement_text: string;
  requirement_type: string;
  extracted_requirement: Record<string, unknown> | null;
  evaluation_status: string;
  risk_level: string;
  is_blocking: boolean;
  matched_material_id: string | null;
  matched_material_name: string | null;
  matched_rule_code: string;
  rule_version: string;
  reason: string;
  evidence_text: string | null;
  missing_materials: string[] | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  confirm_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type DraftFactCheck = {
  id: string;
  chapter_id: string;
  fact_type: string;
  fact_text: string;
  check_status: string;
  risk_level: string;
  evidence_text: string | null;
  detail: string;
  created_at: string;
};

export type BusinessDraftEvidenceRef = {
  id: string;
  chapter_id: string;
  compliance_item_id: string | null;
  evidence_binding_id: string | null;
  enterprise_material_id: string | null;
  source_type: string;
  source_snapshot: Record<string, unknown>;
  quote_text: string | null;
  created_at: string;
};

export type BusinessDraftChapter = {
  id: string;
  project_id: string;
  section_id: string;
  chapter_type: string;
  title: string;
  sort_order: number;
  content_text: string;
  outline_json: Record<string, unknown> | null;
  evidence_summary_json: Record<string, unknown> | null;
  fact_check_status: string;
  status: string;
  version_no: number;
  generated_from_json: Record<string, unknown> | null;
  edit_reason: string | null;
  created_at: string;
  updated_at: string;
  evidence_refs: BusinessDraftEvidenceRef[];
  fact_checks: DraftFactCheck[];
};

export type BusinessDraftContextPackPreview = {
  profile_id: string;
  profile_version: string;
  schema_version: string;
  readiness_status: string;
  context_json: Record<string, unknown>;
  readiness_json: Record<string, unknown>;
  outline_plan_json: Record<string, unknown>;
};

export type DraftSectionContextPack = {
  id: string;
  project_id: string;
  section_id: string;
  context_pack_id: string;
  section_type: string;
  title: string;
  sort_order: number;
  generation_mode: string;
  status: string;
  context_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type DraftBlock = {
  id: string;
  project_id: string;
  section_id: string;
  chapter_id: string | null;
  section_context_pack_id: string | null;
  block_type: string;
  content_text: string;
  sort_order: number;
  links_json: Record<string, unknown>;
  fact_claims_json: Record<string, unknown>[] | null;
  missing_fact_placeholders_json: Record<string, unknown>[] | null;
  risk_flags_json: Record<string, unknown>[] | null;
  review_status: string;
  created_at: string;
  updated_at: string;
};

export type DraftCoverageReview = {
  id: string;
  project_id: string;
  section_id: string;
  context_pack_id: string | null;
  status: string;
  summary_json: Record<string, unknown>;
  issues_json: Record<string, unknown>[];
  created_at: string;
};

export type BusinessDraftContextPack = {
  id: string;
  project_id: string;
  section_id: string;
  profile_id: string;
  profile_version: string;
  schema_version: string;
  status: string;
  readiness_status: string;
  context_json: Record<string, unknown>;
  readiness_json: Record<string, unknown>;
  outline_plan_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  section_context_packs: DraftSectionContextPack[];
};

export type OutlineChapterInput = {
  section_type: string;
  title?: string | null;
  custom?: boolean;
};

export type AuthorDirectiveType = "style" | "emphasis" | "mandatory_text";

export type AuthorDirectiveInput = {
  scope: string;
  directive_type: AuthorDirectiveType;
  text: string;
};

export type AuthorDirective = AuthorDirectiveInput & {
  id?: string;
  author_user_id?: string;
  created_at?: string;
};

export type BusinessDraftContextPackPayload = {
  profile_id?: string;
  section_types?: string[] | null;
  outline?: OutlineChapterInput[] | null;
  directives?: AuthorDirectiveInput[] | null;
};

export type BusinessDraftContextPackGenerateResult = {
  context_pack: BusinessDraftContextPack;
  chapters: BusinessDraftChapter[];
  blocks: DraftBlock[];
  coverage_review: DraftCoverageReview;
};

export type QualificationDecision = {
  id: string;
  project_id: string;
  section_id: string;
  recommendation: string;
  status: string;
  summary: string;
  satisfied_count: number;
  blocking_count: number;
  missing_count: number;
  pending_count: number;
  reasons_json: Record<string, unknown> | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  confirm_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type ApprovalTask = {
  id: string;
  project_id: string;
  section_id: string | null;
  task_type: string;
  title: string;
  description: string | null;
  status: string;
  related_object_type: string | null;
  related_object_id: string | null;
  assignee_user_id: string | null;
  evidence_snapshot_json: Record<string, unknown> | null;
  decision_reason: string | null;
  decided_by: string | null;
  decided_at: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EnterpriseMaterialPayload = {
  material_type: string;
  name: string;
  issuing_authority?: string | null;
  certificate_no?: string | null;
  holder_name?: string | null;
  project_name?: string | null;
  amount?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  data_level?: string;
  verification_status?: string;
  structured_fields?: Record<string, unknown> | null;
  evidence_text?: string | null;
};

export type EnterpriseMaterialUpdatePayload = Partial<EnterpriseMaterialPayload> & {
  reason: string;
};

export type ChatModelConfig = {
  id: string | null;
  capability: string;
  provider: string;
  base_url: string | null;
  simple_model: string | null;
  complex_model: string | null;
  timeout_seconds: number;
  enabled: boolean;
  api_key_masked: string | null;
  has_api_key: boolean;
  source: string;
  last_test_status: string | null;
  last_test_message: string | null;
  last_tested_at: string | null;
  updated_at: string | null;
};

export type ChatModelConfigPayload = {
  provider: string;
  base_url?: string | null;
  simple_model?: string | null;
  complex_model?: string | null;
  timeout_seconds: number;
  enabled: boolean;
  api_key?: string | null;
  clear_api_key?: boolean;
};

export type ChatModelConfigTestPayload = Partial<ChatModelConfigPayload>;

export type ChatModelConfigTestResult = {
  status: "success" | "failed";
  message: string;
  provider: string;
  model_name: string | null;
  duration_ms: number | null;
  source: string;
};

export async function getChatModelConfig() {
  const response = await apiClient.get<ChatModelConfig>("/system/model-configs/chat");
  return response.data;
}

export async function saveChatModelConfig(payload: ChatModelConfigPayload) {
  const response = await apiClient.put<ChatModelConfig>("/system/model-configs/chat", payload);
  return response.data;
}

export async function testChatModelConfig(payload?: ChatModelConfigTestPayload) {
  const response = await apiClient.post<ChatModelConfigTestResult>(
    "/system/model-configs/chat/test",
    payload ?? {}
  );
  return response.data;
}

export async function createProject(payload: ProjectCreatePayload) {
  const response = await apiClient.post<ProjectDetail>("/projects", payload);
  return response.data;
}

export async function updateProject(projectId: string, payload: ProjectUpdatePayload) {
  const response = await apiClient.patch<ProjectDetail>(`/projects/${projectId}`, payload);
  return response.data;
}

export async function updateSection(projectId: string, sectionId: string, payload: SectionUpdatePayload) {
  const response = await apiClient.patch<SectionSummary>(
    `/projects/${projectId}/sections/${sectionId}`,
    payload
  );
  return response.data;
}

export async function getEnterpriseProfile() {
  const response = await apiClient.get<EnterpriseProfile | null>("/enterprise/profile");
  return response.data;
}

export async function upsertEnterpriseProfile(payload: EnterpriseProfilePayload) {
  const response = await apiClient.put<EnterpriseProfile>("/enterprise/profile", payload);
  return response.data;
}

export async function listEnterpriseMaterials(params?: {
  material_type?: string;
  data_level?: string;
  verification_status?: string;
  limit?: number;
  offset?: number;
}) {
  const response = await apiClient.get<EnterpriseMaterial[]>("/enterprise/materials", { params });
  return response.data;
}

export async function searchEnterpriseMaterials(params: {
  query?: string;
  material_type?: string;
  verification_status?: string;
  data_level?: string;
  include_restricted?: boolean;
  limit?: number;
}) {
  const response = await apiClient.get<EnterpriseMaterialSearchResult[]>(
    "/enterprise/materials/search",
    { params }
  );
  return response.data;
}

export async function getEnterpriseMaterialIndexHealth() {
  const response = await apiClient.get<EnterpriseMaterialIndexHealth>(
    "/enterprise/materials/index-health"
  );
  return response.data;
}

export async function rebuildEnterpriseMaterialIndex() {
  const response = await apiClient.post<EnterpriseMaterialIndexRebuildResult>(
    "/enterprise/materials/index/rebuild"
  );
  return response.data;
}

export async function createEnterpriseMaterial(payload: EnterpriseMaterialPayload) {
  const response = await apiClient.post<EnterpriseMaterial>("/enterprise/materials", payload);
  return response.data;
}

export async function updateEnterpriseMaterial(materialId: string, payload: EnterpriseMaterialUpdatePayload) {
  const response = await apiClient.patch<EnterpriseMaterial>(`/enterprise/materials/${materialId}`, payload);
  return response.data;
}

export async function createEnterpriseMaterialsHistoryExtractTask(payload: {
  file: File;
  dataLevel?: string;
}) {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("data_level", payload.dataLevel ?? "internal");
  const response = await apiClient.post<AsyncTask>(
    "/enterprise/materials/history-extract-tasks",
    form,
    {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 1500000
    }
  );
  return response.data;
}

export async function uploadEnterpriseMaterialFile(
  materialId: string,
  payload: {
    file: File;
    reason?: string;
  }
) {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("reason", payload.reason ?? "上传企业资料原始文件");
  const response = await apiClient.post<EnterpriseMaterial>(
    `/enterprise/materials/${materialId}/file`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function createProjectImportDraftFromFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const response = await apiClient.post<ProjectImportDraft>("/projects/import-drafts/upload", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return response.data;
}

export async function createProjectImportDraftFromUrl(payload: {
  source_url: string;
  source_site?: string | null;
  title?: string | null;
}) {
  const response = await apiClient.post<ProjectImportDraft>(
    "/projects/import-drafts/public-url",
    payload
  );
  return response.data;
}

export async function confirmProjectImportDraft(payload: ProjectImportConfirmPayload) {
  const response = await apiClient.post<ProjectImportConfirmResult>(
    "/projects/import-drafts/confirm",
    payload
  );
  return response.data;
}

export async function listProjects(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const pageSize = 200;
  if (params?.limit !== undefined || params?.offset !== undefined) {
    const response = await apiClient.get<ProjectSummary[]>("/projects", {
      params: { limit: pageSize, ...params }
    });
    return response.data;
  }

  const projects: ProjectSummary[] = [];
  let offset = 0;
  while (true) {
    const response = await apiClient.get<ProjectSummary[]>("/projects", {
      params: { ...params, limit: pageSize, offset }
    });
    projects.push(...response.data);
    if (response.data.length < pageSize) break;
    offset += pageSize;
  }
  return projects;
}

export async function getProject(projectId: string) {
  const response = await apiClient.get<ProjectDetail>(`/projects/${projectId}`);
  return response.data;
}

export async function deleteProject(projectId: string) {
  await apiClient.delete(`/projects/${projectId}`);
}

export async function listSections(projectId: string) {
  const response = await apiClient.get<SectionSummary[]>(`/projects/${projectId}/sections`);
  return response.data;
}

export async function listDocuments(projectId: string, sectionId: string) {
  const response = await apiClient.get<ProjectDocument[]>(
    `/projects/${projectId}/sections/${sectionId}/documents`
  );
  return response.data;
}

export async function uploadDocument(
  projectId: string,
  sectionId: string,
  payload: {
    file: File;
    doc_type?: string;
    title?: string;
  }
) {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("doc_type", payload.doc_type ?? "tender");
  if (payload.title) form.append("title", payload.title);
  const response = await apiClient.post<ProjectDocument>(
    `/projects/${projectId}/sections/${sectionId}/documents/upload`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function requestPublicUrlAcquisition(
  projectId: string,
  sectionId: string,
  payload: {
    source_url: string;
    source_site?: string | null;
    title?: string | null;
    doc_type?: string;
  }
) {
  const response = await apiClient.post<FileAcquisitionTask>(
    `/projects/${projectId}/sections/${sectionId}/documents/public-url`,
    payload
  );
  return response.data;
}

export async function createParseTask(
  projectId: string,
  sectionId: string,
  documentId: string,
  payload?: {
    parser_type?: string;
    parser_name?: string;
    parser_version?: string;
  }
) {
  const response = await apiClient.post<ParseTask>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/parse-tasks`,
    payload ?? {}
  );
  return response.data;
}

export async function listDocumentChunks(
  projectId: string,
  sectionId: string,
  documentId: string,
  versionId: string
) {
  const response = await apiClient.get<DocumentChunk[]>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/versions/${versionId}/chunks`
  );
  return response.data;
}

export async function listDocumentSemanticSections(
  projectId: string,
  sectionId: string,
  documentId: string,
  versionId: string
) {
  const response = await apiClient.get<DocumentSemanticSection[]>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/versions/${versionId}/semantic-sections`
  );
  return response.data;
}

export async function replanDocumentSemanticSections(
  projectId: string,
  sectionId: string,
  documentId: string,
  versionId: string
) {
  const response = await apiClient.post<DocumentSemanticSection[]>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/versions/${versionId}/semantic-sections/replan`,
    undefined,
    { timeout: 600000 }
  );
  return response.data;
}

export async function extractDocumentSemanticSectionCompliance(
  projectId: string,
  sectionId: string,
  semanticSectionId: string
) {
  const response = await apiClient.post<AsyncTask>(
    `/projects/${projectId}/sections/${sectionId}/document-semantic-sections/${semanticSectionId}/extract-compliance`,
    undefined,
    { timeout: 600000 }
  );
  return response.data;
}

export async function getDocumentExtractionQualityReport(
  projectId: string,
  sectionId: string,
  documentId: string,
  versionId: string
) {
  const response = await apiClient.get<DocumentExtractionQualityReport | null>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/versions/${versionId}/extraction-quality-report`
  );
  return response.data;
}

export async function publishDocumentManualRevision(
  projectId: string,
  sectionId: string,
  documentId: string,
  versionId: string,
  payload: DocumentManualRevisionPayload
) {
  const response = await apiClient.post<DocumentManualRevisionResult>(
    `/projects/${projectId}/sections/${sectionId}/documents/${documentId}/versions/${versionId}/manual-revisions`,
    payload
  );
  return response.data;
}

export async function getTask(taskId: string) {
  const response = await apiClient.get<AsyncTask>(`/tasks/${taskId}`);
  return response.data;
}

export async function listTasks(params?: {
  project_id?: string;
  section_id?: string;
  task_type?: string;
  active?: boolean;
  limit?: number;
}) {
  const response = await apiClient.get<AsyncTask[]>("/tasks", { params });
  return response.data;
}

export async function listComplianceItems(
  projectId: string,
  sectionId: string,
  params?: {
    status?: string;
    risk_level?: string;
    owner_user_id?: string;
    item_type?: string;
    limit?: number;
    offset?: number;
  }
) {
  const response = await apiClient.get<ComplianceItem[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items`,
    { params }
  );
  return response.data;
}

export async function getPreflightCheck(projectId: string, sectionId: string) {
  const response = await apiClient.get<PreflightCheck>(
    `/projects/${projectId}/sections/${sectionId}/preflight-check`
  );
  return response.data;
}

export async function getMatrixReview(projectId: string, sectionId: string) {
  const response = await apiClient.get<MatrixReview>(
    `/projects/${projectId}/sections/${sectionId}/matrix-review`
  );
  return response.data;
}

export async function listQualificationEvaluations(projectId: string, sectionId: string) {
  const response = await apiClient.get<QualificationEvaluation[]>(
    `/projects/${projectId}/sections/${sectionId}/qualification-evaluations`
  );
  return response.data;
}

export async function getQualificationDecision(projectId: string, sectionId: string) {
  const response = await apiClient.get<QualificationDecision | null>(
    `/projects/${projectId}/sections/${sectionId}/qualification-decision`
  );
  return response.data;
}

export async function generateQualificationDecision(projectId: string, sectionId: string) {
  const response = await apiClient.post<QualificationDecision>(
    `/projects/${projectId}/sections/${sectionId}/qualification-decision/generate`
  );
  return response.data;
}

export async function confirmQualificationDecision(
  projectId: string,
  sectionId: string,
  decisionId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.post<QualificationDecision>(
    `/projects/${projectId}/sections/${sectionId}/qualification-decision/${decisionId}/confirm`,
    payload
  );
  return response.data;
}

export async function listBusinessDraftChapters(projectId: string, sectionId: string) {
  const response = await apiClient.get<BusinessDraftChapter[]>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/chapters`
  );
  return response.data;
}

export async function previewBusinessDraftContextPack(
  projectId: string,
  sectionId: string,
  payload: BusinessDraftContextPackPayload = {}
) {
  const response = await apiClient.post<BusinessDraftContextPackPreview>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack/preview`,
    payload
  );
  return response.data;
}

export async function listBusinessDraftContextPacks(projectId: string, sectionId: string) {
  const response = await apiClient.get<BusinessDraftContextPack[]>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack`
  );
  return response.data;
}

export async function createBusinessDraftContextPack(
  projectId: string,
  sectionId: string,
  payload: BusinessDraftContextPackPayload = {}
) {
  const response = await apiClient.post<BusinessDraftContextPack>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack`,
    payload
  );
  return response.data;
}

export async function updateBusinessDraftContextPackDirectives(
  projectId: string,
  sectionId: string,
  contextPackId: string,
  directives: AuthorDirectiveInput[]
) {
  const response = await apiClient.put<BusinessDraftContextPack>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack/${contextPackId}/directives`,
    { directives }
  );
  return response.data;
}

export async function generateBusinessDraftFromContextPack(
  projectId: string,
  sectionId: string,
  contextPackId: string,
  payload: {
    allow_blocked_internal_draft?: boolean;
  } = {}
) {
  const response = await apiClient.post<BusinessDraftContextPackGenerateResult>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack/${contextPackId}/generate`,
    payload
  );
  return response.data;
}

export async function generateBusinessDraftFromContextPackAsync(
  projectId: string,
  sectionId: string,
  contextPackId: string,
  payload: {
    allow_blocked_internal_draft?: boolean;
  } = {}
) {
  const response = await apiClient.post<AsyncTask>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack/${contextPackId}/generate-async`,
    payload
  );
  return response.data;
}

export async function runBusinessDraftContextPackCoverageReview(
  projectId: string,
  sectionId: string,
  contextPackId: string
) {
  const response = await apiClient.post<DraftCoverageReview>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/context-pack/${contextPackId}/coverage-review`
  );
  return response.data;
}

export async function listBusinessDraftBlocks(projectId: string, sectionId: string) {
  const response = await apiClient.get<DraftBlock[]>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/blocks`
  );
  return response.data;
}

export async function updateBusinessDraftBlock(
  projectId: string,
  sectionId: string,
  blockId: string,
  payload: {
    review_status: string;
    content_text?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.patch<DraftBlock>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/blocks/${blockId}`,
    payload
  );
  return response.data;
}

export async function generateBusinessDraftChapters(projectId: string, sectionId: string) {
  const response = await apiClient.post<BusinessDraftChapter[]>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/chapters/generate`,
    { force: true }
  );
  return response.data;
}

export async function updateBusinessDraftChapter(
  projectId: string,
  sectionId: string,
  chapterId: string,
  payload: {
    content_text: string;
    reason: string;
  }
) {
  const response = await apiClient.patch<BusinessDraftChapter>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/chapters/${chapterId}`,
    payload
  );
  return response.data;
}

export async function runBusinessDraftFactChecks(projectId: string, sectionId: string, chapterId: string) {
  const response = await apiClient.post<BusinessDraftChapter>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/chapters/${chapterId}/fact-checks/run`
  );
  return response.data;
}

export async function exportBusinessDraftWord(
  projectId: string,
  sectionId: string,
  payload?: {
    risk_acceptance_reason?: string | null;
  }
) {
  const response = await apiClient.post<ExportFile>(
    `/projects/${projectId}/sections/${sectionId}/business-draft/export-word`,
    payload ?? {}
  );
  return response.data;
}

export async function listApprovalTasks(
  projectId: string,
  sectionId: string,
  params?: {
    status?: string;
  }
) {
  const response = await apiClient.get<ApprovalTask[]>(
    `/projects/${projectId}/sections/${sectionId}/approval-tasks`,
    { params }
  );
  return response.data;
}

export async function createApprovalTask(
  projectId: string,
  sectionId: string,
  payload: {
    task_type: string;
    title: string;
    description?: string | null;
    related_object_type?: string | null;
    related_object_id?: string | null;
    assignee_user_id?: string | null;
    due_at?: string | null;
    risk_acceptance_reason?: string | null;
  }
) {
  const response = await apiClient.post<ApprovalTask>(
    `/projects/${projectId}/sections/${sectionId}/approval-tasks`,
    payload
  );
  return response.data;
}

export async function decideApprovalTask(
  projectId: string,
  sectionId: string,
  taskId: string,
  payload: {
    action: "approve" | "reject";
    reason: string;
  }
) {
  const response = await apiClient.post<ApprovalTask>(
    `/projects/${projectId}/sections/${sectionId}/approval-tasks/${taskId}/decision`,
    payload
  );
  return response.data;
}

export async function listComplianceEvidenceBindings(
  projectId: string,
  sectionId: string,
  itemId: string
) {
  const response = await apiClient.get<ComplianceEvidenceBinding[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/evidence-bindings`
  );
  return response.data;
}

export async function listComplianceEvidenceCandidates(
  projectId: string,
  sectionId: string,
  itemId: string,
  params?: {
    material_type?: string;
    include_restricted?: boolean;
    include_unconfirmed?: boolean;
    limit?: number;
  }
) {
  const response = await apiClient.get<EnterpriseMaterialSearchResult[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/evidence-candidates`,
    { params }
  );
  return response.data;
}

export async function bindComplianceEvidence(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    enterprise_material_id: string;
    evidence_text?: string | null;
    confidence_score?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceEvidenceBinding>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/evidence-bindings`,
    payload
  );
  return response.data;
}

export async function waiveComplianceEvidenceRequirement(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceItem>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/evidence-not-required`,
    payload
  );
  return response.data;
}

export async function unbindComplianceEvidence(
  projectId: string,
  sectionId: string,
  itemId: string,
  bindingId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.delete<ComplianceEvidenceBinding>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/evidence-bindings/${bindingId}`,
    { data: payload }
  );
  return response.data;
}

export async function runQualificationEvaluation(projectId: string, sectionId: string) {
  const response = await apiClient.post<QualificationEvaluation[]>(
    `/projects/${projectId}/sections/${sectionId}/qualification-evaluations/run`
  );
  return response.data;
}

export async function confirmQualificationEvaluation(
  projectId: string,
  sectionId: string,
  evaluationId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.post<QualificationEvaluation>(
    `/projects/${projectId}/sections/${sectionId}/qualification-evaluations/${evaluationId}/confirm`,
    payload
  );
  return response.data;
}

export async function generateComplianceMatrix(
  projectId: string,
  sectionId: string,
  payload?: {
    document_id?: string;
    document_version_id?: string;
    force?: boolean;
    async_processing?: boolean;
  }
) {
  const response = await apiClient.post<AsyncTask>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/generate`,
    payload ?? {},
    { timeout: 1500000 }
  );
  return response.data;
}

export async function exportComplianceMatrixExcel(
  projectId: string,
  sectionId: string,
  payload?: {
    status?: string;
    risk_level?: string;
    owner_user_id?: string;
    item_type?: string;
  }
) {
  const response = await apiClient.post<AsyncTask>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/export-excel`,
    payload ?? {}
  );
  return response.data;
}

export async function listExportFiles(projectId: string, sectionId: string) {
  const response = await apiClient.get<ExportFile[]>(
    `/projects/${projectId}/sections/${sectionId}/export-files`
  );
  return response.data;
}

export async function updateComplianceItem(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    requirement_text?: string;
    response_suggestion?: string | null;
    status?: string;
    risk_level?: string;
    is_mandatory?: boolean;
    owner_user_id?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.patch<ComplianceItem>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}`,
    payload
  );
  return response.data;
}

export async function confirmComplianceItem(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    reason: string;
    source_verified?: boolean;
    cascade?: boolean;
  }
) {
  const response = await apiClient.post<ComplianceItem>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/confirm`,
    payload
  );
  return response.data;
}

export async function createComplianceItemFromSource(
  projectId: string,
  sectionId: string,
  payload: {
    source_chunk_id: string;
    selected_text: string;
    selection_start_offset?: number | null;
    selection_end_offset?: number | null;
    item_type: string;
    risk_level: string;
    is_mandatory: boolean;
    response_suggestion?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceItemFromSourceResult>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/from-source`,
    payload
  );
  return response.data;
}

export async function listSimilarCandidates(projectId: string, sectionId: string, itemId: string) {
  const response = await apiClient.post<SimilarCandidate[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/similar-candidates`
  );
  return response.data;
}

export async function applySimilarCandidates(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    candidates: Array<{
      candidate_key: string;
      source_chunk_id: string;
      selected_text: string;
      selection_start_offset?: number | null;
      selection_end_offset?: number | null;
      action: "join_group" | "create_independent" | "skip";
    }>;
    reason: string;
  }
) {
  const response = await apiClient.post<DuplicateGroupActionResult>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/similar-candidates/apply`,
    payload
  );
  return response.data;
}

export async function confirmDuplicateGroup(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    item_ids?: string[] | null;
    reason: string;
  }
) {
  const response = await apiClient.post<DuplicateGroupActionResult>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/duplicate-group/confirm`,
    payload
  );
  return response.data;
}

export async function unlinkDuplicateGroupItem(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.post<DuplicateGroupActionResult>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/duplicate-group/unlink`,
    payload
  );
  return response.data;
}

export async function splitDuplicateGroupItem(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    reason: string;
  }
) {
  const response = await apiClient.post<DuplicateGroupActionResult>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/duplicate-group/split`,
    payload
  );
  return response.data;
}

export async function assignComplianceItem(
  projectId: string,
  sectionId: string,
  itemId: string,
  payload: {
    owner_user_id?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceItem>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/${itemId}/assign`,
    payload
  );
  return response.data;
}

export async function bulkAssignComplianceItems(
  projectId: string,
  sectionId: string,
  payload: {
    item_ids: string[];
    owner_user_id?: string | null;
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceItem[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/bulk-assign`,
    payload
  );
  return response.data;
}

export async function bulkConfirmComplianceItems(
  projectId: string,
  sectionId: string,
  payload: {
    item_ids: string[];
    reason: string;
  }
) {
  const response = await apiClient.post<ComplianceItem[]>(
    `/projects/${projectId}/sections/${sectionId}/compliance-items/bulk-confirm`,
    payload
  );
  return response.data;
}

export async function listAuditLogs(
  projectId: string,
  params?: {
    section_id?: string;
    action?: string;
    object_type?: string;
    limit?: number;
    offset?: number;
  }
) {
  const response = await apiClient.get<AuditLog[]>(`/projects/${projectId}/audit-logs`, {
    params
  });
  return response.data;
}

export async function listModelInvocationLogs(
  projectId: string,
  params?: {
    section_id?: string;
    task_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }
) {
  const response = await apiClient.get<ModelInvocationLog[]>(
    `/projects/${projectId}/model-invocation-logs`,
    { params }
  );
  return response.data;
}
