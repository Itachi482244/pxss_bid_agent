import {
  AuditOutlined,
  BellOutlined,
  CheckCircleOutlined,
  BranchesOutlined,
  HighlightOutlined,
  CloudUploadOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CommentOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  LinkOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  SendOutlined,
  SettingOutlined,
  TeamOutlined,
  WarningOutlined
} from "@ant-design/icons";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Checkbox,
  DatePicker,
  Drawer,
  Empty,
  Input,
  Layout,
  Modal,
  Pagination,
  Popover,
  Progress,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Tree,
  Typography,
  Upload
} from "antd";
import type { UploadProps } from "antd";
import dayjs from "dayjs";
import type { CSSProperties, Key, MouseEvent as ReactMouseEvent } from "react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  assignComplianceItem,
  applySimilarCandidates,
  bindComplianceEvidence,
  bulkAssignComplianceItems,
  bulkConfirmComplianceItems,
  confirmComplianceItem,
  confirmDuplicateGroup,
  confirmQualificationDecision,
  confirmQualificationEvaluation,
  confirmProjectImportDraft,
  createApprovalTask,
  createBusinessDraftContextPack,
  createComplianceItemFromSource,
  createParseTask,
  createProjectImportDraftFromFile,
  createProjectImportDraftFromUrl,
  createEnterpriseMaterial,
  createProject,
  deleteProject,
  decideApprovalTask,
  extractDocumentSemanticSectionCompliance,
  listDocumentChunks,
  listDocumentSemanticSections,
  exportBusinessDraftWord,
  exportComplianceMatrixExcel,
  generateBusinessDraftFromContextPackAsync,
  generateBusinessDraftChapters,
  generateComplianceMatrix,
  getDocumentExtractionQualityReport,
  getPreflightCheck,
  getMatrixReview,
  generateQualificationDecision,
  getEnterpriseProfile,
  getProject,
  getQualificationDecision,
  getTask,
  listApprovalTasks,
  listBusinessDraftBlocks,
  listBusinessDraftChapters,
  listBusinessDraftContextPacks,
  listTasks,
  listEnterpriseMaterials,
  listComplianceEvidenceBindings,
  listDocuments,
  listExportFiles,
  listAuditLogs,
  listComplianceItems,
  listSimilarCandidates,
  listQualificationEvaluations,
  listProjects,
  listSections,
  replanDocumentSemanticSections,
  requestPublicUrlAcquisition,
  runBusinessDraftFactChecks,
  runBusinessDraftContextPackCoverageReview,
  runQualificationEvaluation,
  searchEnterpriseMaterials,
  publishDocumentManualRevision,
  previewBusinessDraftContextPack,
  getChatModelConfig,
  uploadEnterpriseMaterialFile,
  unbindComplianceEvidence,
  unlinkDuplicateGroupItem,
  updateProject,
  updateSection,
  saveChatModelConfig,
  testChatModelConfig,
  upsertEnterpriseProfile,
  uploadDocument,
  waiveComplianceEvidenceRequirement,
  splitDuplicateGroupItem,
  updateBusinessDraftBlock,
  updateBusinessDraftChapter,
  updateComplianceItem
} from "../api/bid";
import type {
  AuditLog,
  ApprovalTask,
  BusinessDraftChapter,
  BusinessDraftContextPack,
  BusinessDraftContextPackPreview,
  ChatModelConfig,
  ChatModelConfigPayload,
  ChatModelConfigTestResult,
  ComplianceEvidenceBinding,
  ComplianceItemFromSourceResult,
  ComplianceItem,
  DocumentChunk,
  DocumentExtractionQualityReport,
  DocumentSemanticSection,
  DraftBlock,
  DraftCoverageReview,
  EnterpriseMaterial,
  EnterpriseMaterialSearchResult,
  EnterpriseProfile,
  ExportFile,
  ProjectImportDraft,
  ProjectDocument,
  ProjectDetail,
  PreflightCheck,
  ProjectSummary,
  QualityIssue,
  QualificationDecision,
  QualificationEvaluation,
  SectionSummary,
  SimilarCandidate,
  MatrixReviewDuplicateGroup,
  MatrixReviewDocument,
  MatrixReviewHighlight,
  ReviewDocumentBlock,
  ReviewDocumentParagraph,
  ReviewDocumentRun,
  MatrixReviewUncoveredChunk,
  TextDiffSegment,
  AsyncTask
} from "../api/bid";
import { ContextPackPreviewDrawer } from "../components/ContextPackPreviewDrawer";
import "./app.css";

const { Header, Content } = Layout;
const { Text, Title } = Typography;
const { TextArea } = Input;

type MatrixRow = {
  key: string;
  requirement: string;
  source: string;
  chapter: string;
  mandatory: boolean;
  owner: string;
  ownerUserId: string | null;
  status: string;
  statusCode: string;
  risk: string;
  riskCode: string;
  evidence: string;
  enterpriseEvidenceCount: number;
  enterpriseEvidenceSummary: string | null;
  enterpriseEvidenceNotRequired: boolean;
  enterpriseEvidenceNotRequiredReason: string | null;
  raw: ComplianceItem;
};

type HomeTodoRow = {
  key: string;
  task: string;
  project: string;
  owner: string;
  due: string;
  priority: string;
};

type EditMatrixDraft = {
  row: MatrixRow;
  status: string;
  riskLevel: string;
  isMandatory: boolean;
  responseSuggestion: string;
  reason: string;
};

type NewProjectDraft = {
  name: string;
  purchaser: string;
  agency: string;
  budgetAmount: string;
  regionCode: string;
  industryCode: string;
  noticeUrl: string;
  bidDeadlineAt: string | null;
  sectionName: string;
};

type KeyInfoDraft = {
  projectName: string;
  purchaser: string;
  agency: string;
  budgetAmount: string;
  regionCode: string;
  industryCode: string;
  noticeUrl: string;
  bidDeadlineAt: string | null;
  sectionCode: string;
  sectionName: string;
  sectionBudgetAmount: string;
  sectionBidDeadlineAt: string | null;
  reason: string;
};

type ProjectCreateMode = "manual" | "file" | "url";
type WorkflowStepKey =
  | "documents"
  | "tasks"
  | "quality"
  | "matrix"
  | "review"
  | "technical"
  | "evidence"
  | "qualification"
  | "chapter"
  | "approval";
type WorkflowStepStatus = "not_started" | "todo" | "risk" | "done";
type ContextPackActionTarget = WorkflowStepKey | "project_info" | "enterprise";
const contextPackProjectFields = new Set([
  "project_name",
  "tenderer_name",
  "agency_name",
  "bid_section_name",
  "tender_project_no",
  "bid_deadline",
  "bid_price_amount",
  "region_code",
  "industry_code"
]);
type MatrixReviewFilter = "all" | "unconfirmed" | "high" | "mandatory" | "missing_evidence";

const workflowStepKeys = new Set<WorkflowStepKey>([
  "documents",
  "tasks",
  "quality",
  "matrix",
  "review",
  "technical",
  "evidence",
  "qualification",
  "chapter",
  "approval"
]);

const preflightWorkflowTargets: Record<string, WorkflowStepKey> = {
  matrix_version: "matrix",
  high_risk: "review",
  mandatory_evidence: "evidence",
  draft_facts: "chapter",
  qualification: "qualification",
  technical: "technical",
  deadline: "documents",
  approvals: "approval",
  draft_exists: "chapter"
};
const MVP13_DRAFT_WORKFLOW_AVAILABLE = true;
const mvp13PreflightCodes = new Set(["draft_facts", "approvals", "draft_exists"]);

function isWorkflowStepKey(value: string | null | undefined): value is WorkflowStepKey {
  return Boolean(value && workflowStepKeys.has(value as WorkflowStepKey));
}

function workflowStepForPreflightCheck(item: PreflightCheck["checks"][number]) {
  if (isWorkflowStepKey(item.target)) return item.target;
  const mappedTarget = preflightWorkflowTargets[item.code];
  if (mappedTarget) return mappedTarget;
  return null;
}

function preflightActionText(item: PreflightCheck["checks"][number]) {
  if (item.code === "high_risk") return "打开审阅台";
  return item.action_label ?? "去处理";
}

function workflowStepForContextPackCheck(check: Record<string, unknown>): ContextPackActionTarget {
  const code = String(check.code ?? "");
  if (code.startsWith("qualification.")) return "qualification";
  if (code.startsWith("evidence.")) return "evidence";
  if (code.startsWith("project_fields.")) {
    const fields = Array.isArray(check.sample_fields) ? check.sample_fields.map(String) : [];
    return fields.some((field) => !contextPackProjectFields.has(field))
      ? "enterprise"
      : "project_info";
  }
  if (code === "matrix.empty") return "matrix";
  if (code.startsWith("matrix.")) return "review";
  if (code.startsWith("source_document.")) return "documents";
  return "chapter";
}

function contextPackCheckActionText(check: Record<string, unknown>): string {
  const code = String(check.code ?? "");
  if (code === "qualification.no_go_confirmed") return "查看风险结论";
  if (code === "qualification.conditional_go_confirmed") return "复核资格结论";
  const target = workflowStepForContextPackCheck(check);
  if (target === "project_info") return "补项目信息";
  if (target === "enterprise") return "完善企业资料";
  if (target === "qualification") return "去资格预评估";
  if (target === "evidence") return "绑定企业资料";
  if (target === "review") return "打开审阅台";
  if (target === "matrix") return "生成合规矩阵";
  if (target === "documents") return "检查招标文件";
  return "查看上下文";
}

type ReviewChunk = Pick<
  DocumentChunk,
  "id" | "chunk_index" | "page_no" | "heading_path" | "content_text" | "document_version_id"
>;

type SourceSelectionDraft = {
  chunk: ReviewChunk;
  selectedText: string;
  selectionStartOffset: number | null;
  selectionEndOffset: number | null;
  itemType: string;
  riskLevel: string;
  isMandatory: boolean;
  responseSuggestion: string;
  reason: string;
};

type SimilarAction = "join_group" | "create_independent" | "skip";

type WorkflowStep = {
  key: WorkflowStepKey;
  title: string;
  description: string;
  status: WorkflowStepStatus;
  statusText: string;
  actionText: string;
  reason: string;
  disabled: boolean;
  disabledReason: string | null;
};

type SimpleWorkflowStep = {
  key: string;
  title: string;
  targetKey: WorkflowStepKey;
  activeKeys: WorkflowStepKey[];
  status: WorkflowStepStatus;
  statusText: string;
  reason: string;
  disabled: boolean;
  disabledReason: string | null;
};

type NewMaterialDraft = {
  materialType: string;
  name: string;
  issuingAuthority: string;
  certificateNo: string;
  holderName: string;
  projectName: string;
  amount: string;
  validUntil: string | null;
  dataLevel: string;
  verificationStatus: string;
  evidenceText: string;
};

type ModelConfigDraft = {
  provider: string;
  baseUrl: string;
  apiKey: string;
  simpleModel: string;
  complexModel: string;
  timeoutSeconds: number;
  enabled: boolean;
  clearApiKey: boolean;
};

type ImportProcessingState = {
  projectId: string;
  sectionId: string | null;
  parseTaskId: string | null;
  matrixTaskId: string | null;
  parseTask: AsyncTask | null;
  matrixTask: AsyncTask | null;
};

const IMPORT_PROCESSING_STORAGE_KEY = "pxss_bid_agent_import_processing";
const ASYNC_TASK_STALE_AFTER_MS = 60 * 60 * 1000;
const COMPLIANCE_ITEM_FETCH_LIMIT = 500;
const LARGE_TABLE_PAGINATION = {
  defaultPageSize: 25,
  pageSizeOptions: ["25", "50", "100"],
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
};

function loadImportProcessingState() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(IMPORT_PROCESSING_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<ImportProcessingState>;
    if (typeof value.projectId !== "string") return null;
    const parseTaskId = typeof value.parseTaskId === "string" ? value.parseTaskId : null;
    const matrixTaskId = typeof value.matrixTaskId === "string" ? value.matrixTaskId : null;
    if (!parseTaskId && !matrixTaskId) return null;
    return {
      projectId: value.projectId,
      sectionId: typeof value.sectionId === "string" ? value.sectionId : null,
      parseTaskId,
      matrixTaskId,
      parseTask: null,
      matrixTask: null
    };
  } catch {
    window.localStorage.removeItem(IMPORT_PROCESSING_STORAGE_KEY);
    return null;
  }
}

function saveImportProcessingState(value: ImportProcessingState | null) {
  if (typeof window === "undefined") return;
  if (!value || (!value.parseTaskId && !value.matrixTaskId)) {
    window.localStorage.removeItem(IMPORT_PROCESSING_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(
    IMPORT_PROCESSING_STORAGE_KEY,
    JSON.stringify({
      projectId: value.projectId,
      sectionId: value.sectionId,
      parseTaskId: value.parseTaskId,
      matrixTaskId: value.matrixTaskId
    })
  );
}

const quickPrompts = ["解释当前条款", "查看技术响应", "检查缺项", "整理审批意见"];

const statusLabels: Record<string, string> = {
  draft: "草稿",
  pending_confirm: "待确认",
  confirmed: "已确认",
  needs_material: "缺材料",
  rejected: "不适用",
  superseded: "已替代"
};

const projectStatusLabels: Record<string, string> = {
  draft: "草稿",
  pending_files: "待上传",
  parsing: "解析中",
  pending_confirm: "待确认",
  need_materials: "待补充",
  confirmed: "已确认",
  exported: "已导出",
  archived: "已归档"
};

const asyncTaskStatusLabels: Record<string, string> = {
  pending: "排队中",
  running: "处理中",
  retrying: "重试中",
  succeeded: "已完成",
  failed: "失败",
  canceled: "已取消"
};

const asyncTaskStatusColors: Record<string, string> = {
  pending: "default",
  running: "processing",
  retrying: "gold",
  succeeded: "green",
  failed: "red",
  canceled: "default"
};

const qualityGateTaskErrorCodes = new Set([
  "QUALITY_GATE_BLOCKED",
  "SOURCE_CHUNK_NOT_FOUND",
  "SOURCE_QUOTE_NOT_FOUND",
  "COVERAGE_REVIEW_ISSUE",
  "SECTION_HAS_NO_CHUNKS",
  "NO_COMPLIANCE_CANDIDATES"
]);

const riskLabels: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低"
};

const itemTypeLabels: Record<string, string> = {
  qualification: "资格要求",
  mandatory_response: "强制响应",
  format: "格式要求",
  deadline: "截止时间",
  scoring: "评分办法",
  reference_info: "参考信息",
  technical_response: "技术响应",
  other: "其他"
};

const materialTypeLabels: Record<string, string> = {
  license: "营业执照",
  qualification: "资质证照",
  personnel: "人员材料",
  performance: "业绩案例",
  business_template: "商务模板",
  commitment: "承诺材料",
  product_catalog: "产品资料",
  test_report: "检测报告",
  product_image: "产品图片",
  technical_proposal: "历史方案",
  other: "其他资料"
};

const dataLevelLabels: Record<string, string> = {
  public: "公共",
  internal: "内部",
  restricted: "受限",
  confidential: "机密"
};

const verificationStatusLabels: Record<string, string> = {
  draft: "草稿",
  pending_confirm: "待确认",
  confirmed: "已确认",
  conflict: "有冲突",
  expired: "已过期",
  missing_evidence: "缺证据"
};

const qualificationStatusLabels: Record<string, string> = {
  satisfied: "满足",
  not_satisfied: "不满足",
  needs_material: "缺材料",
  pending_confirm: "待确认",
  not_applicable: "不适用"
};

const qualificationTypeLabels: Record<string, string> = {
  business_license: "营业执照",
  enterprise_qualification: "企业资质",
  safety_production_license: "安全许可",
  personnel_certificate: "人员证书",
  performance: "类似业绩",
  manual_check: "人工确认"
};

const decisionLabels: Record<string, string> = {
  go: "建议参标",
  conditional_go: "有条件参标",
  no_go: "暂不参标"
};

const decisionColors: Record<string, string> = {
  go: "green",
  conditional_go: "orange",
  no_go: "red"
};

const chapterStatusLabels: Record<string, string> = {
  draft: "草稿",
  pending_review: "待复核",
  approved: "已确认",
  rejected: "已退回",
  superseded: "已替代"
};

const factCheckLabels: Record<string, string> = {
  verified: "已核验",
  warning: "需关注",
  unverified: "无法核验"
};

const draftBlockStatusLabels: Record<string, string> = {
  pending: "待审阅",
  covered: "已覆盖",
  needs_evidence: "缺证据",
  needs_fact: "待补事实",
  approved: "已通过",
  rejected: "已退回"
};

const draftBlockStatusColors: Record<string, string> = {
  pending: "gold",
  covered: "blue",
  needs_evidence: "red",
  needs_fact: "orange",
  approved: "green",
  rejected: "red"
};

const approvalTaskTypeLabels: Record<string, string> = {
  qualification_decision: "资格确认",
  draft_chapter: "章节确认",
  submit_confirmation: "提交确认"
};

const approvalStatusLabels: Record<string, string> = {
  pending: "待处理",
  approved: "已通过",
  rejected: "已退回",
  transferred: "已转交",
  canceled: "已取消"
};

function riskColor(value: string) {
  if (value === "高" || value === "high") return "red";
  if (value === "中" || value === "medium") return "orange";
  return "green";
}

function statusColor(value: string) {
  if (value === "缺材料" || value === "needs_material") return "red";
  if (value === "不满足" || value === "not_satisfied") return "red";
  if (value === "待确认" || value === "pending_confirm") return "gold";
  if (value === "满足" || value === "satisfied") return "green";
  if (value === "不适用" || value === "not_applicable") return "default";
  if (value === "已确认" || value === "confirmed") return "green";
  return "blue";
}

function workflowStatusColor(value: WorkflowStepStatus) {
  if (value === "done") return "green";
  if (value === "risk") return "red";
  if (value === "todo") return "gold";
  return "default";
}

function preflightColor(value: string) {
  if (value === "block") return "red";
  if (value === "warn") return "gold";
  return "green";
}

function preflightLabel(value: string) {
  if (value === "block") return "存在阻塞";
  if (value === "warn") return "需复核";
  return "已通过";
}

function qualityIssueSeverityColor(value: string) {
  if (value === "high") return "red";
  if (value === "medium") return "gold";
  return "blue";
}

function qualityIssueActionText(issue: QualityIssue) {
  if (issue.code === "SOURCE_QUOTE_NOT_FOUND") {
    return "模型摘录和解析文本没有精确回链；优先重抽该语义段，仍失败时重新解析或人工修正原文。";
  }
  if (issue.code === "COVERAGE_REVIEW_ISSUE") {
    return "覆盖复核认为该段有关键条款漏抽；请打开对应页核对，重抽该段或重新生成全量矩阵。";
  }
  if (issue.code.includes("SECTION")) {
    return "章节计划可能不完整；请先重新规划章节，再重新生成矩阵。";
  }
  return "请核对对应章节和页码，处理后重新生成矩阵。";
}

function qualityIssueSearchTerms(issue: QualityIssue) {
  const message = issue.message || "";
  const terms = new Set<string>();
  const sourceQuote = typeof issue.source_quote === "string" ? issue.source_quote.trim() : "";
  if (sourceQuote.length >= 2) terms.add(sourceQuote);

  for (const match of message.matchAll(/[（(]([^（）()]{2,80})[）)]/g)) {
    match[1]
      .split(/[，,、；;。]|\s+|如/)
      .map((term) => term.trim())
      .filter((term) => term.length >= 2)
      .forEach((term) => terms.add(term));
  }
  if (message.includes("单价合同")) {
    terms.add("单价合同");
    terms.add("合同价格形式");
  }
  if (message.includes("质量保证金")) {
    terms.add("质量保证金");
  }
  if (message.includes("1.5%")) {
    terms.add("1.5%");
  }
  if (message.includes("履约保证金")) {
    terms.add("履约保证金");
  }
  return Array.from(terms).sort((left, right) => right.length - left.length);
}

function qualityIssueSourceChunk(
  issue: QualityIssue,
  semanticSection: DocumentSemanticSection | undefined,
  chunks: ReviewChunk[]
) {
  if (typeof issue.source_chunk_index === "number") {
    const exactChunk = chunks.find((chunk) => chunk.chunk_index === issue.source_chunk_index);
    if (exactChunk) return exactChunk;
  }
  const terms = qualityIssueSearchTerms(issue);
  const sectionChunks = semanticSection
    ? chunks.filter((chunk) => {
        const pageNo = chunk.page_no ?? 0;
        return pageNo >= semanticSection.start_page && pageNo <= semanticSection.end_page;
      })
    : chunks;
  return (
    sectionChunks.find((chunk) => terms.some((term) => chunk.content_text.includes(term))) ??
    sectionChunks[0] ??
    null
  );
}

function qualityIssueSourceExcerpt(chunk: ReviewChunk | null, terms: string[], maxChars = 360) {
  if (!chunk) return "";
  const text = chunk.content_text.replace(/\s+/g, " ").trim();
  if (!text) return "";
  const matchIndex = terms.map((term) => text.indexOf(term)).find((index) => index >= 0) ?? 0;
  const start = Math.max(0, matchIndex - 90);
  const excerpt = text.slice(start, start + maxChars);
  return `${start > 0 ? "..." : ""}${excerpt}${start + maxChars < text.length ? "..." : ""}`;
}

function isAsyncTaskActive(task: AsyncTask | null, taskId: string | null) {
  if (!taskId) return false;
  if (!task) return true;
  return ["pending", "running", "retrying"].includes(task.status);
}

function isAsyncTaskTerminal(task: AsyncTask | null, taskId: string | null) {
  if (!taskId) return true;
  return Boolean(task && ["succeeded", "failed", "canceled"].includes(task.status));
}

function isAsyncTaskTerminalStatus(status: string | null | undefined) {
  return status === "succeeded" || status === "failed" || status === "canceled";
}

function isAsyncTaskStale(task: AsyncTask | null) {
  if (!task || isAsyncTaskTerminalStatus(task.status)) return false;
  const updatedAt = dayjs(task.updated_at || task.created_at);
  return updatedAt.isValid() && dayjs().diff(updatedAt) >= ASYNC_TASK_STALE_AFTER_MS;
}

function isUsableParseStatus(value: string | null | undefined) {
  return value === "succeeded" || value === "frozen";
}

function asyncTaskProgress(task: AsyncTask | null, taskId: string | null) {
  if (!taskId) return 0;
  if (!task) return 5;
  const progress = Math.max(0, Math.min(100, Math.round(task.progress || 0)));
  if (task.status === "pending") return Math.max(progress, 8);
  if (isAsyncTaskActive(task, taskId)) return Math.min(progress || 8, 99);
  return progress;
}

function formatDateTime(value: string | null) {
  if (!value) return "未设置";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

function formatShortTime(value: string | null) {
  if (!value) return "待定";
  const date = dayjs(value);
  if (date.isSame(dayjs(), "day")) return `今天 ${date.format("HH:mm")}`;
  if (date.isSame(dayjs().add(1, "day"), "day")) return `明天 ${date.format("HH:mm")}`;
  return date.format("MM-DD HH:mm");
}

function truncateText(value: string, length = 24) {
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function summaryNumber(source: Record<string, unknown> | null, key: string) {
  const value = source?.[key];
  return typeof value === "number" ? value : Number(value ?? 0) || 0;
}

function taskOutputText(task: AsyncTask | null, key: string) {
  const value = task?.output_json?.[key];
  return typeof value === "string" && value.trim() ? value : "";
}

function asyncTaskStatusText(task: AsyncTask | null, taskId: string | null) {
  if (!taskId) return "";
  if (!task) return "排队中";
  return asyncTaskStatusLabels[task.status] ?? "处理中";
}

function isQualityGateTaskError(code: string | null | undefined) {
  if (!code) return false;
  return qualityGateTaskErrorCodes.has(code) || code.startsWith("SECTION_PLAN_");
}

function matrixTaskStageTitle(task: AsyncTask | null) {
  if (!task) return "合规矩阵排队中";
  if (task.status === "succeeded") return "合规矩阵已生成";
  if (task.status === "failed") return "合规矩阵生成失败";
  const output = task.output_json ?? null;
  const stage = taskOutputText(task, "progress_stage");
  const sectionPosition = summaryNumber(output, "section_position");
  const sectionCount = summaryNumber(output, "section_count");
  const retryIndex = summaryNumber(output, "retry_index");
  const retryCount = summaryNumber(output, "retry_count");
  const stageLabel =
    stage === "section_plan_done"
      ? "章节规划完成"
      : stage === "section_fork_join"
        ? "并发抽取条款"
      : stage === "section_extract"
        ? "准备抽取章节"
        : stage === "section_llm_extract"
          ? "模型抽取条款"
          : stage === "section_llm_extract_retry"
            ? "模型拆分重试"
            : stage === "section_coverage_review"
              ? "覆盖率复核"
              : stage === "section_review"
                ? "章节复核完成"
                : "合规矩阵生成中";
  const sectionText = sectionPosition && sectionCount ? `第 ${sectionPosition}/${sectionCount} 段` : "";
  const retryText = retryIndex && retryCount ? `子段 ${retryIndex}/${retryCount}` : "";
  return [stageLabel, sectionText, retryText].filter(Boolean).join(" · ");
}

function taskProgressMessage(task: AsyncTask | null, activeFallback: string, doneFallback: string) {
  if (task?.error_message) return task.error_message;
  const progressMessage = taskOutputText(task, "progress_message");
  if (progressMessage) return progressMessage;
  if (task?.status === "succeeded") return doneFallback;
  return activeFallback;
}

function importProcessingProgress(processing: ImportProcessingState | null) {
  if (!processing) return 0;
  const parseProgress = asyncTaskProgress(processing.parseTask, processing.parseTaskId);
  const matrixProgress = asyncTaskProgress(processing.matrixTask, processing.matrixTaskId);
  if (processing.parseTaskId && processing.matrixTaskId) {
    return Math.round(parseProgress * 0.25 + matrixProgress * 0.75);
  }
  return processing.matrixTaskId ? matrixProgress : parseProgress;
}

function taskShortId(value: string | null | undefined) {
  return value ? value.slice(0, 8) : "";
}

function taskTimeRange(task: AsyncTask | null) {
  if (!task) return "尚未开始";
  const start = task.started_at ? formatDateTime(task.started_at) : "排队中";
  const end = task.finished_at ? formatDateTime(task.finished_at) : "处理中";
  return `${start} / ${end}`;
}

function blockingSummary(source: Record<string, unknown> | null) {
  const value = source?.blocking_summary;
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
}

function explanationText(source: Record<string, unknown> | null | undefined, key: string, fallback = "暂无记录") {
  const value = source?.[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

function explanationKeywords(source: Record<string, unknown> | null | undefined) {
  const value = source?.matched_keywords;
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function sourceMetaText(value: Record<string, unknown> | null) {
  if (!value || !Object.keys(value).length) return "暂无";
  return JSON.stringify(value);
}

function auditContentText(value: Record<string, unknown> | null) {
  const content = value?.content_text;
  return typeof content === "string" ? content : "";
}

function draftBlockLinkIds(block: DraftBlock, key: "compliance_item_ids" | "evidence_binding_ids" | "source_chunk_ids") {
  const value = block.links_json[key];
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item : item == null ? "" : String(item)))
    .filter(Boolean);
}

function isMatrixItemResolved(row: MatrixRow) {
  return ["confirmed", "rejected", "superseded"].includes(row.statusCode);
}

function isHttpNotFoundError(error: unknown) {
  return error instanceof Error && error.message.includes("404");
}

function buildMatrixTableRows(
  rows: MatrixRow[],
  filters: {
    status?: string;
    owner?: string;
    risk?: string;
    mandatory?: string;
    prioritySortEnabled: boolean;
  }
) {
  const filteredRows = rows.filter((row) => {
    if (filters.status && row.statusCode !== filters.status) return false;
    if (filters.owner && row.ownerUserId !== filters.owner) return false;
    if (filters.risk && row.riskCode !== filters.risk) return false;
    if (filters.mandatory === "mandatory" && !row.mandatory) return false;
    if (filters.mandatory === "normal" && row.mandatory) return false;
    return true;
  });
  if (!filters.prioritySortEnabled) return filteredRows;
  return [...filteredRows].sort((left, right) => {
    if (left.raw.priority_rank !== right.raw.priority_rank) {
      return left.raw.priority_rank - right.raw.priority_rank;
    }
    const riskOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return (riskOrder[left.riskCode] ?? 3) - (riskOrder[right.riskCode] ?? 3);
  });
}

function buildMatrixReviewRows(rows: MatrixRow[], filter: MatrixReviewFilter) {
  const reviewRows = [...rows].sort((left, right) => {
    const leftChunk = left.raw.source_chunk_index ?? 999999;
    const rightChunk = right.raw.source_chunk_index ?? 999999;
    if (leftChunk !== rightChunk) return leftChunk - rightChunk;
    if (left.raw.priority_rank !== right.raw.priority_rank) return left.raw.priority_rank - right.raw.priority_rank;
    const riskOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return (riskOrder[left.riskCode] ?? 3) - (riskOrder[right.riskCode] ?? 3);
  });
  return reviewRows.filter((row) => {
    if (filter === "unconfirmed") return !isMatrixItemResolved(row);
    if (filter === "high") return row.riskCode === "high";
    if (filter === "mandatory") return row.mandatory;
    if (filter === "missing_evidence") {
      return !row.enterpriseEvidenceNotRequired && (row.enterpriseEvidenceCount === 0 || row.statusCode === "needs_material");
    }
    return true;
  });
}

function findNextUnresolvedMatrixRow(queue: MatrixRow[], currentKey: string) {
  const currentIndex = queue.findIndex((row) => row.key === currentKey);
  const orderedRows =
    currentIndex >= 0 ? [...queue.slice(currentIndex + 1), ...queue.slice(0, currentIndex)] : queue;
  return orderedRows.find((row) => row.key !== currentKey && !isMatrixItemResolved(row)) ?? null;
}

function mapMatrixRow(item: ComplianceItem): MatrixRow {
  const sourceDocument = item.source_document_title ?? "招标文件";
  const page = item.source_page_no ? ` P${item.source_page_no}` : "";
  const version = item.source_version_label ? ` ${item.source_version_label}` : "";
  return {
    key: item.id,
    requirement: item.requirement_text,
    source: `${sourceDocument}${page}${version}`,
    chapter: itemTypeLabels[item.item_type] ?? item.item_type,
    mandatory: item.is_mandatory,
    owner: item.owner_name ?? "未指派",
    ownerUserId: item.owner_user_id,
    status: statusLabels[item.status] ?? item.status,
    statusCode: item.status,
    risk: riskLabels[item.risk_level] ?? item.risk_level,
    riskCode: item.risk_level,
    evidence: item.enterprise_evidence_summary ?? item.evidence_text ?? item.response_suggestion ?? "待补充证据",
    enterpriseEvidenceCount: item.enterprise_evidence_count,
    enterpriseEvidenceSummary: item.enterprise_evidence_summary,
    enterpriseEvidenceNotRequired: item.enterprise_evidence_not_required,
    enterpriseEvidenceNotRequiredReason: item.enterprise_evidence_not_required_reason,
    raw: item
  };
}

function auditActionText(log: AuditLog) {
  const labels: Record<string, string> = {
    "seed.dev_data_created": "初始化演示数据",
    "matrix.generated": "生成合规矩阵",
    "compliance.matrix_generated": "生成合规矩阵",
    "compliance.matrix_generate_requested": "请求生成合规矩阵",
    "matrix.item_updated": "修改矩阵项",
    "matrix.item_confirmed": "确认矩阵项",
    "matrix.item_assigned": "指派矩阵项",
    "matrix.items_assigned": "批量指派矩阵项",
    "matrix.items_batch_confirmed": "批量确认矩阵项",
    "matrix.evidence_bound": "绑定企业资料证据",
    "matrix.evidence_not_required": "标记无需绑定证据",
    "matrix.evidence_unbound": "解除企业资料证据",
    "matrix.item_created_from_source": "从原文新增矩阵项",
    "matrix.duplicate_group_confirmed": "确认重复关联组",
    "matrix.duplicate_group_unlinked": "解除重复联动",
    "matrix.duplicate_group_split": "拆分重复关联组",
    "matrix.similar_candidate_applied": "确认相似补票",
    "matrix.cascade_confirmed": "级联确认矩阵项",
    "document.uploaded": "上传文件",
    "document.public_url_downloaded": "获取公开文件",
    "export.excel_succeeded": "导出矩阵快照",
    "qualification.decision_generated": "生成参标建议",
    "qualification.decision_confirmed": "确认参标建议",
    "business_draft.generated": "生成商务标草稿",
    "business_draft.context_pack_created": "生成 ContextPack",
    "business_draft.context_pack_generated": "按 ContextPack 生成草稿",
    "business_draft.block_updated": "更新草稿 block",
    "business_draft.chapter_updated": "修改商务标草稿",
    "business_draft.fact_checked": "执行事实校验",
    "business_draft.word_exported": "导出商务标 Word",
    "model.invocation_succeeded": "模型调用成功",
    "model.invocation_failed": "模型调用失败",
    "model.invocation_skipped": "模型调用跳过",
    "model_config.updated": "更新模型配置",
    "model_config.tested": "测试模型连接",
    "approval.task_created": "创建审批任务",
    "approval.task_approved": "审批通过",
    "approval.task_rejected": "审批退回"
  };
  return labels[log.action] ?? log.action;
}

function paragraphCss(paragraph: ReviewDocumentParagraph | null): CSSProperties {
  const style = paragraph?.style;
  if (!style) return {};
  const css: CSSProperties = {};
  if (style.alignment) {
    css.textAlign = style.alignment === "both" ? "justify" : (style.alignment as CSSProperties["textAlign"]);
  }
  if (style.indent_left_pt != null) css.marginLeft = `${style.indent_left_pt}pt`;
  if (style.first_line_indent_pt != null) css.textIndent = `${style.first_line_indent_pt}pt`;
  if (style.line_spacing != null) css.lineHeight = style.line_spacing;
  return css;
}

function runCss(run: ReviewDocumentRun): CSSProperties {
  return {
    fontFamily: run.style.font_family ?? undefined,
    fontSize: run.style.font_size_pt ? `${run.style.font_size_pt}pt` : undefined,
    fontWeight: run.style.bold ? 700 : undefined,
    fontStyle: run.style.italic ? "italic" : undefined,
    textDecoration: run.style.underline ? "underline" : undefined,
    color: run.style.color ?? undefined
  };
}

function reviewBlockCss(block: ReviewDocumentBlock): CSSProperties {
  const bbox = block.bbox_json;
  if (!bbox || typeof bbox !== "object") return {};
  const x0 = Number(bbox.x0);
  const pageWidth = Number(bbox.page_width);
  if (!Number.isFinite(x0) || !Number.isFinite(pageWidth) || pageWidth <= 0) return {};
  return {
    marginLeft: `${Math.min(56, Math.max(0, (x0 / pageWidth) * 72))}px`
  };
}

function scrollElementIntoContainer(target: HTMLElement, container: HTMLElement) {
  const targetRect = target.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  const offset = targetRect.top - containerRect.top - container.clientHeight / 2 + targetRect.height / 2;
  container.scrollTo({
    top: container.scrollTop + offset,
    behavior: "smooth"
  });
}

export function App() {
  const [assistantCollapsed, setAssistantCollapsed] = useState(true);
  const [projectNavCollapsed, setProjectNavCollapsed] = useState(true);
  const [viewMode, setViewMode] = useState<"home" | "workspace" | "enterprise" | "settings">("home");
  const [selectedProjectId, setSelectedProjectId] = useState<string>();
  const [selectedSectionId, setSelectedSectionId] = useState<string>();
  const [selectedTreeKey, setSelectedTreeKey] = useState("");
  const [activeTab, setActiveTab] = useState("matrix");
  const [highlightedRowKey, setHighlightedRowKey] = useState("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [ownerFilter, setOwnerFilter] = useState<string | undefined>();
  const [riskFilter, setRiskFilter] = useState<string | undefined>();
  const [mandatoryFilter, setMandatoryFilter] = useState<string | undefined>();
  const [prioritySortEnabled, setPrioritySortEnabled] = useState(true);
  const [matrixReviewFilter, setMatrixReviewFilter] = useState<MatrixReviewFilter>("all");
  const [reviewQueuePage, setReviewQueuePage] = useState(1);
  const [reviewQueuePageSize, setReviewQueuePageSize] = useState(25);
  const [reviewChunks, setReviewChunks] = useState<ReviewChunk[]>([]);
  const [loadingReviewChunks, setLoadingReviewChunks] = useState(false);
  const [qualityChunks, setQualityChunks] = useState<ReviewChunk[]>([]);
  const [loadingQualityChunks, setLoadingQualityChunks] = useState(false);
  const [activeReviewItemId, setActiveReviewItemId] = useState("");
  const [locatingReviewItemId, setLocatingReviewItemId] = useState("");
  const [reviewOpenXmlDocument, setReviewOpenXmlDocument] = useState<MatrixReviewDocument | null>(null);
  const [reviewHighlights, setReviewHighlights] = useState<MatrixReviewHighlight[]>([]);
  const [reviewUncoveredChunks, setReviewUncoveredChunks] = useState<MatrixReviewUncoveredChunk[]>([]);
  const [reviewDuplicateGroups, setReviewDuplicateGroups] = useState<MatrixReviewDuplicateGroup[]>([]);
  const [sourceCreateMode, setSourceCreateMode] = useState(false);
  const [sourceSelectionDraft, setSourceSelectionDraft] = useState<SourceSelectionDraft | null>(null);
  const [savingSourceItem, setSavingSourceItem] = useState(false);
  const [similarBaseRow, setSimilarBaseRow] = useState<MatrixRow | null>(null);
  const [similarCandidates, setSimilarCandidates] = useState<SimilarCandidate[]>([]);
  const [similarActions, setSimilarActions] = useState<Record<string, SimilarAction>>({});
  const [similarDrawerOpen, setSimilarDrawerOpen] = useState(false);
  const [loadingSimilarCandidates, setLoadingSimilarCandidates] = useState(false);
  const [sourceDrawer, setSourceDrawer] = useState<MatrixRow | null>(null);
  const [evidenceDrawer, setEvidenceDrawer] = useState<MatrixRow | null>(null);
  const [evidenceBindings, setEvidenceBindings] = useState<ComplianceEvidenceBinding[]>([]);
  const [openingEvidenceItemId, setOpeningEvidenceItemId] = useState("");
  const [waivingEvidenceItemId, setWaivingEvidenceItemId] = useState("");
  const reviewSourcePaneRef = useRef<HTMLDivElement | null>(null);
  const reviewItemPaneRef = useRef<HTMLDivElement | null>(null);
  const locateReviewTimerRef = useRef<number | null>(null);
  const terminalTaskRefreshKeysRef = useRef<Set<string>>(new Set());
  const businessDraftTerminalTaskRef = useRef<Set<string>>(new Set());
  const [materialSearchQuery, setMaterialSearchQuery] = useState("");
  const [materialSearchResults, setMaterialSearchResults] = useState<EnterpriseMaterialSearchResult[]>([]);
  const [loadingMaterialSearch, setLoadingMaterialSearch] = useState(false);
  const [bindingMaterialId, setBindingMaterialId] = useState("");
  const [unbindingId, setUnbindingId] = useState("");
  const [editDraft, setEditDraft] = useState<EditMatrixDraft | null>(null);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [projectCreateMode, setProjectCreateMode] = useState<ProjectCreateMode>("manual");
  const [projectImportDraft, setProjectImportDraft] = useState<ProjectImportDraft | null>(null);
  const [importUrl, setImportUrl] = useState("");
  const [importUrlSite, setImportUrlSite] = useState("");
  const [importingProjectDraft, setImportingProjectDraft] = useState(false);
  const [newProjectDraft, setNewProjectDraft] = useState<NewProjectDraft>({
    name: "",
    purchaser: "",
    agency: "",
    budgetAmount: "",
    regionCode: "CN-4306",
    industryCode: "municipal-gas",
    noticeUrl: "",
    bidDeadlineAt: null,
    sectionName: "一标段"
  });
  const [keyInfoModalOpen, setKeyInfoModalOpen] = useState(false);
  const [keyInfoDraft, setKeyInfoDraft] = useState<KeyInfoDraft>({
    projectName: "",
    purchaser: "",
    agency: "",
    budgetAmount: "",
    regionCode: "",
    industryCode: "",
    noticeUrl: "",
    bidDeadlineAt: null,
    sectionCode: "",
    sectionName: "",
    sectionBudgetAmount: "",
    sectionBidDeadlineAt: null,
    reason: "人工确认项目和标段关键信息"
  });
  const [publicUrl, setPublicUrl] = useState("");
  const [publicUrlSite, setPublicUrlSite] = useState("");
  const [actionLogs, setActionLogs] = useState<string[]>([]);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectRowKeys, setSelectedProjectRowKeys] = useState<Key[]>([]);
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [sections, setSections] = useState<SectionSummary[]>([]);
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [exportFiles, setExportFiles] = useState<ExportFile[]>([]);
  const [complianceItems, setComplianceItems] = useState<ComplianceItem[]>([]);
  const [preflightCheck, setPreflightCheck] = useState<PreflightCheck | null>(null);
  const [preflightExpanded, setPreflightExpanded] = useState(false);
  const [qualificationEvaluations, setQualificationEvaluations] = useState<QualificationEvaluation[]>([]);
  const [qualificationDecision, setQualificationDecision] = useState<QualificationDecision | null>(null);
  const [businessDraftChapters, setBusinessDraftChapters] = useState<BusinessDraftChapter[]>([]);
  const [businessDraftContextPacks, setBusinessDraftContextPacks] = useState<BusinessDraftContextPack[]>([]);
  const [contextPackPreview, setContextPackPreview] = useState<BusinessDraftContextPackPreview | null>(null);
  const [contextPackPreviewOpen, setContextPackPreviewOpen] = useState(false);
  const [draftBlocks, setDraftBlocks] = useState<DraftBlock[]>([]);
  const [activeDraftBlockId, setActiveDraftBlockId] = useState("");
  const [coverageReview, setCoverageReview] = useState<DraftCoverageReview | null>(null);
  const [selectedDraftChapterId, setSelectedDraftChapterId] = useState("");
  const [draftEditorValue, setDraftEditorValue] = useState("");
  const [approvalTasks, setApprovalTasks] = useState<ApprovalTask[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [loadingMatrix, setLoadingMatrix] = useState(false);
  const [savingMatrixAction, setSavingMatrixAction] = useState(false);
  const [loadingBusinessDraft, setLoadingBusinessDraft] = useState(false);
  const [businessDraftGenerationTaskId, setBusinessDraftGenerationTaskId] = useState<string | null>(null);
  const [businessDraftGenerationTask, setBusinessDraftGenerationTask] = useState<AsyncTask | null>(null);
  const [loadingContextPack, setLoadingContextPack] = useState(false);
  const [savingBusinessDraft, setSavingBusinessDraft] = useState(false);
  const [exportingWord, setExportingWord] = useState(false);
  const [generatingDecision, setGeneratingDecision] = useState(false);
  const [approvalBusyId, setApprovalBusyId] = useState("");
  const [savingProject, setSavingProject] = useState(false);
  const [deletingProjects, setDeletingProjects] = useState(false);
  const [importProcessing, setImportProcessing] = useState<ImportProcessingState | null>(() => loadImportProcessingState());
  const [documentBusy, setDocumentBusy] = useState(false);
  const [semanticSections, setSemanticSections] = useState<DocumentSemanticSection[]>([]);
  const [extractionQualityReport, setExtractionQualityReport] = useState<DocumentExtractionQualityReport | null>(null);
  const [sectionPlanLoading, setSectionPlanLoading] = useState(false);
  const [sectionExtractingId, setSectionExtractingId] = useState("");
  const [revisionDrawerOpen, setRevisionDrawerOpen] = useState(false);
  const [revisionDocument, setRevisionDocument] = useState<ProjectDocument | null>(null);
  const [revisionChunks, setRevisionChunks] = useState<DocumentChunk[]>([]);
  const [revisionReason, setRevisionReason] = useState("");
  const [revisionSearch, setRevisionSearch] = useState("");
  const [loadingRevisionChunks, setLoadingRevisionChunks] = useState(false);
  const [publishingRevision, setPublishingRevision] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [evaluatingQualification, setEvaluatingQualification] = useState(false);
  const [apiError, setApiError] = useState("");
  const [enterpriseProfile, setEnterpriseProfile] = useState<EnterpriseProfile | null>(null);
  const [enterpriseMaterials, setEnterpriseMaterials] = useState<EnterpriseMaterial[]>([]);
  const [loadingEnterprise, setLoadingEnterprise] = useState(false);
  const [savingEnterprise, setSavingEnterprise] = useState(false);
  const [profileDraft, setProfileDraft] = useState({
    companyName: "",
    unifiedSocialCreditCode: "",
    legalRepresentative: "",
    registeredAddress: "",
    businessScope: "",
    regionPreferences: [] as string[],
    industryPreferences: [] as string[],
    forbiddenRulesText: ""
  });
  const [materialModalOpen, setMaterialModalOpen] = useState(false);
  const [newMaterialDraft, setNewMaterialDraft] = useState<NewMaterialDraft>({
    materialType: "qualification",
    name: "",
    issuingAuthority: "",
    certificateNo: "",
    holderName: "",
    projectName: "",
    amount: "",
    validUntil: null,
    dataLevel: "internal",
    verificationStatus: "pending_confirm",
    evidenceText: ""
  });
  const [chatModelConfig, setChatModelConfig] = useState<ChatModelConfig | null>(null);
  const [modelConfigDraft, setModelConfigDraft] = useState<ModelConfigDraft>({
    provider: "mock",
    baseUrl: "",
    apiKey: "",
    simpleModel: "deepseek-v4-flash",
    complexModel: "deepseek-v4-pro",
    timeoutSeconds: 30,
    enabled: true,
    clearApiKey: false
  });
  const [loadingModelConfig, setLoadingModelConfig] = useState(false);
  const [savingModelConfig, setSavingModelConfig] = useState(false);
  const [testingModelConfig, setTestingModelConfig] = useState(false);
  const [modelConfigTestResult, setModelConfigTestResult] = useState<ChatModelConfigTestResult | null>(null);

  const applyProjectList = useCallback((data: ProjectSummary[]) => {
    setProjects(data);
    setSelectedProjectRowKeys((keys) => keys.filter((key) => data.some((project) => project.id === key)));
    setSelectedProjectId((current) => (current && data.some((project) => project.id === current) ? current : data[0]?.id));
  }, []);

  const reloadProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const data = await listProjects();
      applyProjectList(data);
      return data;
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "项目列表加载失败");
      return [];
    } finally {
      setLoadingProjects(false);
    }
  }, [applyProjectList]);

  useEffect(() => {
    let active = true;
    setLoadingProjects(true);
    listProjects()
      .then((data) => {
        if (active) applyProjectList(data);
      })
      .catch((error: unknown) => {
        if (active) setApiError(error instanceof Error ? error.message : "项目列表加载失败");
      })
      .finally(() => {
        if (active) setLoadingProjects(false);
      });
    return () => {
      active = false;
    };
  }, [applyProjectList]);

  useEffect(() => {
    return () => {
      if (locateReviewTimerRef.current !== null) {
        window.clearTimeout(locateReviewTimerRef.current);
      }
    };
  }, []);

  const reloadEnterprise = useCallback(async () => {
    setLoadingEnterprise(true);
    try {
      const [profile, materials] = await Promise.all([
        getEnterpriseProfile(),
        listEnterpriseMaterials({ limit: 100 })
      ]);
      setEnterpriseProfile(profile);
      setEnterpriseMaterials(materials);
      if (profile) {
        setProfileDraft({
          companyName: profile.company_name,
          unifiedSocialCreditCode: profile.unified_social_credit_code ?? "",
          legalRepresentative: profile.legal_representative ?? "",
          registeredAddress: profile.registered_address ?? "",
          businessScope: profile.business_scope ?? "",
          regionPreferences: profile.region_preferences ?? [],
          industryPreferences: profile.industry_preferences ?? [],
          forbiddenRulesText: (profile.forbidden_rules ?? []).join("\n")
        });
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业资料加载失败");
    } finally {
      setLoadingEnterprise(false);
    }
  }, []);

  const applyChatModelConfig = useCallback((config: ChatModelConfig) => {
    setChatModelConfig(config);
    setModelConfigDraft((draft) => ({
      ...draft,
      provider: config.provider || "mock",
      baseUrl: config.base_url ?? "",
      apiKey: "",
      simpleModel: config.simple_model ?? "deepseek-v4-flash",
      complexModel: config.complex_model ?? "deepseek-v4-pro",
      timeoutSeconds: Number(config.timeout_seconds || 30),
      enabled: config.enabled,
      clearApiKey: false
    }));
  }, []);

  const reloadChatModelConfig = useCallback(async () => {
    setLoadingModelConfig(true);
    try {
      const config = await getChatModelConfig();
      applyChatModelConfig(config);
      return config;
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "模型配置加载失败");
      return null;
    } finally {
      setLoadingModelConfig(false);
    }
  }, [applyChatModelConfig]);

  useEffect(() => {
    if (viewMode !== "enterprise") return;
    void reloadEnterprise();
  }, [reloadEnterprise, viewMode]);

  useEffect(() => {
    if (viewMode !== "settings") return;
    void reloadChatModelConfig();
  }, [reloadChatModelConfig, viewMode]);

	  useEffect(() => {
	    if (!selectedProjectId) return;

	    let active = true;
	    setLoadingWorkspace(true);
	    setProjectDetail(null);
	    setSections([]);
	    setSelectedSectionId(undefined);
	    setComplianceItems([]);
	    setQualificationEvaluations([]);
	    setQualificationDecision(null);
	    setBusinessDraftChapters([]);
	    setBusinessDraftContextPacks([]);
	    setDraftBlocks([]);
	    setContextPackPreview(null);
	    setContextPackPreviewOpen(false);
	    setApprovalTasks([]);
	    setDocuments([]);
	    setExportFiles([]);
	    setPreflightCheck(null);
	    setCoverageReview(null);
	    setSelectedDraftChapterId("");
	    Promise.all([getProject(selectedProjectId), listSections(selectedProjectId)])
	      .then(([detail, sectionData]) => {
	        if (!active) return;
        setProjectDetail(detail);
        setSections(sectionData);
        setSelectedSectionId((current) => {
          if (current && sectionData.some((section) => section.id === current)) return current;
          return sectionData[0]?.id;
        });
      })
      .catch((error: unknown) => {
        if (!active) return;
        setApiError(error instanceof Error ? error.message : "项目工作台加载失败");
      })
      .finally(() => {
        if (active) setLoadingWorkspace(false);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId) return;
    let active = true;
    listAuditLogs(selectedProjectId)
      .then((data) => {
        if (active) setAuditLogs(data);
      })
      .catch(() => {
        if (active) setAuditLogs([]);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;

    let active = true;
    setLoadingMatrix(true);
    listComplianceItems(selectedProjectId, selectedSectionId, { limit: COMPLIANCE_ITEM_FETCH_LIMIT })
      .then((data) => {
        if (!active) return;
        setComplianceItems(data);
        setSelectedRowKeys([]);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setApiError(error instanceof Error ? error.message : "合规矩阵加载失败");
      })
      .finally(() => {
        if (active) setLoadingMatrix(false);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    let active = true;
    listQualificationEvaluations(selectedProjectId, selectedSectionId)
      .then((data) => {
        if (active) setQualificationEvaluations(data);
      })
      .catch(() => {
        if (active) setQualificationEvaluations([]);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId]);

	  useEffect(() => {
	    if (!selectedProjectId || !selectedSectionId) return;
	    let active = true;
	    Promise.allSettled([
	      getQualificationDecision(selectedProjectId, selectedSectionId),
	      listBusinessDraftChapters(selectedProjectId, selectedSectionId),
	      listApprovalTasks(selectedProjectId, selectedSectionId),
	      listBusinessDraftContextPacks(selectedProjectId, selectedSectionId),
	      listBusinessDraftBlocks(selectedProjectId, selectedSectionId)
	    ])
	      .then(([decisionResult, chaptersResult, tasksResult, contextPacksResult, blocksResult]) => {
	        if (!active) return;
	        const decision = decisionResult.status === "fulfilled" ? decisionResult.value : null;
	        const chapters = chaptersResult.status === "fulfilled" ? chaptersResult.value : [];
	        setQualificationDecision(decision);
	        setBusinessDraftChapters(chapters);
	        setApprovalTasks(tasksResult.status === "fulfilled" ? tasksResult.value : []);
	        setBusinessDraftContextPacks(contextPacksResult.status === "fulfilled" ? contextPacksResult.value : []);
	        setDraftBlocks(blocksResult.status === "fulfilled" ? blocksResult.value : []);
	        setCoverageReview(null);
	        setSelectedDraftChapterId((current) => {
	          if (current && chapters.some((chapter) => chapter.id === current)) return current;
	          return chapters[0]?.id ?? "";
	        });
	        if (decisionResult.status === "rejected") {
	          setApiError("资格结论加载失败，请刷新后重试。");
	        }
	      })
	      .catch(() => {
	        if (!active) return;
        setQualificationDecision(null);
        setBusinessDraftChapters([]);
        setApprovalTasks([]);
        setBusinessDraftContextPacks([]);
        setDraftBlocks([]);
        setCoverageReview(null);
        setSelectedDraftChapterId("");
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    let active = true;
    Promise.all([listDocuments(selectedProjectId, selectedSectionId), listExportFiles(selectedProjectId, selectedSectionId)])
      .then(([documentData, exportData]) => {
        if (!active) return;
        setDocuments(documentData);
        setExportFiles(exportData);
      })
      .catch(() => {
        if (!active) return;
        setDocuments([]);
        setExportFiles([]);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId]);

  const reviewDocument = useMemo(
    () =>
      documents.find((document) => document.doc_type === "tender" && isUsableParseStatus(document.current_version?.parse_status)) ??
      documents.find((document) => isUsableParseStatus(document.current_version?.parse_status)) ??
      null,
    [documents]
  );

  const reloadExtractionQuality = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId || !reviewDocument?.current_version_id) {
      setSemanticSections([]);
      setExtractionQualityReport(null);
      return;
    }
    const [sections, report] = await Promise.all([
      listDocumentSemanticSections(
        selectedProjectId,
        selectedSectionId,
        reviewDocument.id,
        reviewDocument.current_version_id
      ).catch(() => []),
      getDocumentExtractionQualityReport(
        selectedProjectId,
        selectedSectionId,
        reviewDocument.id,
        reviewDocument.current_version_id
      ).catch(() => null)
    ]);
    setSemanticSections(sections);
    setExtractionQualityReport(report);
  }, [reviewDocument?.current_version_id, reviewDocument?.id, selectedProjectId, selectedSectionId]);

  useEffect(() => {
    reloadExtractionQuality().catch(() => undefined);
  }, [reloadExtractionQuality, complianceItems.length]);

  useEffect(() => {
    if (activeTab !== "quality" || !selectedProjectId || !selectedSectionId || !reviewDocument?.current_version_id) {
      return;
    }
    let active = true;
    setLoadingQualityChunks(true);
    listDocumentChunks(
      selectedProjectId,
      selectedSectionId,
      reviewDocument.id,
      reviewDocument.current_version_id
    )
      .then((chunks) => {
        if (!active) return;
        setQualityChunks(
          chunks.map((chunk) => ({
            id: chunk.id,
            chunk_index: chunk.chunk_index,
            page_no: chunk.page_no,
            heading_path: chunk.heading_path,
            content_text: chunk.content_text,
            document_version_id: chunk.document_version_id
          }))
        );
      })
      .catch(() => {
        if (active) setQualityChunks([]);
      })
      .finally(() => {
        if (active) setLoadingQualityChunks(false);
      });
    return () => {
      active = false;
    };
  }, [activeTab, reviewDocument?.current_version_id, reviewDocument?.id, selectedProjectId, selectedSectionId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    let active = true;
    getPreflightCheck(selectedProjectId, selectedSectionId)
      .then((data) => {
        if (active) setPreflightCheck(data);
      })
      .catch(() => {
        if (active) setPreflightCheck(null);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId, complianceItems, businessDraftChapters, approvalTasks, documents]);

  useEffect(() => {
    if (activeTab !== "review" || !selectedProjectId || !selectedSectionId) {
      return;
    }
    let active = true;
    setLoadingReviewChunks(true);
    getMatrixReview(selectedProjectId, selectedSectionId)
      .then((review) => {
        if (!active) return;
        setReviewChunks(review.chunks);
        setReviewOpenXmlDocument(review.review_document);
        setReviewHighlights(review.highlights);
        setComplianceItems(review.items);
        setReviewUncoveredChunks(review.uncovered_chunks);
        setReviewDuplicateGroups(review.duplicate_groups);
      })
      .catch(() => {
        if (!active) return;
        setReviewChunks([]);
        setReviewOpenXmlDocument(null);
        setReviewHighlights([]);
        setReviewUncoveredChunks([]);
        setReviewDuplicateGroups([]);
      })
      .finally(() => {
        if (active) setLoadingReviewChunks(false);
      });
    return () => {
      active = false;
    };
  }, [activeTab, selectedProjectId, selectedSectionId]);

  useEffect(() => {
    if (selectedSectionId && !selectedTreeKey) {
      setSelectedTreeKey(`section:${selectedSectionId}`);
    }
  }, [selectedSectionId, selectedTreeKey]);

  const currentProject = projectDetail ?? projects.find((project) => project.id === selectedProjectId);
  const currentSection = sections.find((section) => section.id === selectedSectionId);
  const matrixRows = useMemo(() => complianceItems.map(mapMatrixRow), [complianceItems]);
  const technicalRows = useMemo(
    () =>
      matrixRows.filter(
        (row) =>
          row.raw.item_type === "technical_response" ||
          row.raw.item_type === "scoring" ||
          (row.raw.item_type === "other" && /技术|设备|参数|验收|净化|洁净/.test(row.requirement))
      ),
    [matrixRows]
  );
  const selectedDraftChapter = useMemo(
    () => businessDraftChapters.find((chapter) => chapter.id === selectedDraftChapterId) ?? null,
    [businessDraftChapters, selectedDraftChapterId]
  );
  const activeContextPack = businessDraftContextPacks[0] ?? null;
  const contextPackSource = contextPackPreview ?? activeContextPack;
  const contextPackChecks = useMemo(() => {
    const readiness = contextPackSource?.readiness_json as { checks?: Record<string, unknown>[] } | undefined;
    return readiness?.checks ?? [];
  }, [contextPackSource]);
  const contextPackPreviewChecks = useMemo(() => {
    const readiness = contextPackPreview?.readiness_json as { checks?: Record<string, unknown>[] } | undefined;
    return readiness?.checks ?? [];
  }, [contextPackPreview]);
  const contextPackOutlineSections = useMemo(() => {
    const outline = contextPackSource?.outline_plan_json as { sections?: Record<string, unknown>[] } | undefined;
    return outline?.sections ?? [];
  }, [contextPackSource]);
  const contextPackReadinessSummary = useMemo(() => {
    const context = contextPackSource?.context_json as
      | {
          matrix_summary?: Record<string, unknown>;
          missing_facts?: unknown[];
        }
      | undefined;
    return {
      missingEvidence: summaryNumber(context?.matrix_summary ?? null, "missing_evidence"),
      missingFacts: Array.isArray(context?.missing_facts) ? context.missing_facts.length : 0
    };
  }, [contextPackSource]);
  const unapprovedDraftBlockCount = useMemo(
    () => draftBlocks.filter((block) => block.review_status !== "approved").length,
    [draftBlocks]
  );
  const selectedChapterBlocks = useMemo(
    () =>
      draftBlocks
        .filter((block) => block.chapter_id === selectedDraftChapterId)
        .sort((a, b) => a.sort_order - b.sort_order),
    [draftBlocks, selectedDraftChapterId]
  );
  const selectedDraftDiff = useMemo(() => {
    if (!selectedDraftChapterId) return null;
    const blockIds = new Set(selectedChapterBlocks.map((block) => block.id));
    const log = auditLogs.find(
      (item) =>
        (item.action === "business_draft.chapter_updated" && item.object_id === selectedDraftChapterId) ||
        (item.action === "business_draft.block_updated" && item.object_id && blockIds.has(item.object_id))
    );
    if (!log) return null;
    const beforeText = auditContentText(log.before_json);
    const afterText = auditContentText(log.after_json);
    if (!beforeText && !afterText) return null;
    return {
      action: log.action,
      reason: log.reason,
      beforeText,
      afterText,
      createdAt: log.created_at,
      delta: afterText.length - beforeText.length,
    };
  }, [auditLogs, selectedChapterBlocks, selectedDraftChapterId]);
  const draftBlocksByComplianceItemId = useMemo(() => {
    const byItem = new Map<string, DraftBlock[]>();
    for (const block of draftBlocks) {
      for (const itemId of draftBlockLinkIds(block, "compliance_item_ids")) {
        const blocks = byItem.get(itemId) ?? [];
        blocks.push(block);
        byItem.set(itemId, blocks);
      }
    }
    return byItem;
  }, [draftBlocks]);
  const matrixRowsById = useMemo(() => {
    return new Map(matrixRows.map((row) => [row.key, row]));
  }, [matrixRows]);
  const missingKeyInfo = useMemo(() => {
    const missing: string[] = [];
    if (!currentProject?.purchaser) missing.push("招标人");
    if (!currentProject?.budget_amount && !currentSection?.budget_amount) missing.push("预算/限价");
    if (!currentProject?.bid_deadline_at && !currentSection?.bid_deadline_at) missing.push("投标截止时间");
    if (!currentSection?.name) missing.push("标段名称");
    return missing;
  }, [
    currentProject?.bid_deadline_at,
    currentProject?.budget_amount,
    currentProject?.purchaser,
    currentSection?.bid_deadline_at,
    currentSection?.budget_amount,
    currentSection?.name
  ]);
  const filteredRevisionChunks = useMemo(() => {
    const keyword = revisionSearch.trim().toLowerCase();
    if (!keyword) return revisionChunks;
    return revisionChunks.filter((chunk) =>
      [chunk.heading_path, chunk.content_text, chunk.page_no ? `p${chunk.page_no}` : ""]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    );
  }, [revisionChunks, revisionSearch]);

  useEffect(() => {
    setDraftEditorValue(selectedDraftChapter?.content_text ?? "");
  }, [selectedDraftChapter?.content_text, selectedDraftChapter?.id]);

  const projectTreeData = useMemo(() => {
    return projects.map((project) => ({
      title: project.name,
      key: `project:${project.id}`,
      icon: <FolderOpenOutlined />,
      children:
        project.id === selectedProjectId
          ? sections.map((section) => ({
              title: section.name,
              key: `section:${section.id}`,
              icon: <FileDoneOutlined />
            }))
          : []
    }));
  }, [projects, sections, selectedProjectId]);

  const contextTitle = useMemo(() => {
    if (activeTab === "chapter") return "商务标章节";
    if (activeTab === "qualification") return "资格预评估";
    if (activeTab === "approval") return "审批与审计";
    if (activeTab === "evidence") return "证据处理";
    if (activeTab === "technical") return "技术响应预览";
    if (activeTab === "review") return "矩阵审阅";
    if (activeTab === "quality") return "质量门禁";
    if (activeTab === "documents") return "文件解析视图";
    return "合规矩阵";
  }, [activeTab]);

  const displayedMatrixRows = useMemo(() => {
    return buildMatrixTableRows(matrixRows, {
      status: statusFilter,
      owner: ownerFilter,
      risk: riskFilter,
      mandatory: mandatoryFilter,
      prioritySortEnabled
    });
  }, [mandatoryFilter, matrixRows, ownerFilter, prioritySortEnabled, riskFilter, statusFilter]);
  const allMatrixReviewRows = useMemo(() => {
    return buildMatrixReviewRows(matrixRows, "all");
  }, [matrixRows]);
  const matrixReviewRows = useMemo(() => {
    return buildMatrixReviewRows(allMatrixReviewRows, matrixReviewFilter);
  }, [allMatrixReviewRows, matrixReviewFilter]);
  const pagedMatrixReviewRows = useMemo(() => {
    const start = (reviewQueuePage - 1) * reviewQueuePageSize;
    return matrixReviewRows.slice(start, start + reviewQueuePageSize);
  }, [matrixReviewRows, reviewQueuePage, reviewQueuePageSize]);
  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(matrixReviewRows.length / reviewQueuePageSize));
    if (reviewQueuePage > maxPage) setReviewQueuePage(maxPage);
  }, [matrixReviewRows.length, reviewQueuePage, reviewQueuePageSize]);
  const reviewFallbackChunks = useMemo<ReviewChunk[]>(() => {
    const pairs = matrixRows
      .filter((row) => row.raw.source_chunk_id && row.raw.source_content_text)
      .map((row) => [
        row.raw.source_chunk_id as string,
        {
          id: row.raw.source_chunk_id as string,
          chunk_index: row.raw.source_chunk_index ?? 0,
          page_no: row.raw.source_page_no,
          heading_path: row.raw.source_heading_path,
          content_text: row.raw.source_content_text ?? row.evidence,
          document_version_id: row.raw.source_version_id
        } satisfies ReviewChunk
      ] as const);
    return Array.from(new Map(pairs).values()).sort((left, right) => left.chunk_index - right.chunk_index);
  }, [matrixRows]);
  const reviewDisplayChunks = reviewChunks.length ? reviewChunks : reviewFallbackChunks;
  const qualityDisplayChunks = qualityChunks.length ? qualityChunks : reviewDisplayChunks;
  const reviewChunkById = useMemo(
    () => new Map(reviewDisplayChunks.map((chunk) => [chunk.id, chunk])),
    [reviewDisplayChunks]
  );
  const effectiveReviewHighlights = useMemo<MatrixReviewHighlight[]>(() => {
    const coveredItemIds = new Set(reviewHighlights.map((highlight) => highlight.item_id));
    const fallbackHighlights: MatrixReviewHighlight[] = [];

    matrixRows.forEach((row) => {
      if (coveredItemIds.has(row.key)) return;
      const chunkId = row.raw.source_chunk_id;
      const chunkText = row.raw.source_content_text;
      if (!chunkId || !chunkText) return;

      let startOffset: number | null = null;
      let endOffset: number | null = null;
      let matchSource = "frontend_fallback";
      const selectionStart = row.raw.selection_start_offset;
      const selectionEnd = row.raw.selection_end_offset;
      if (
        selectionStart != null &&
        selectionEnd != null &&
        selectionStart >= 0 &&
        selectionEnd > selectionStart &&
        selectionEnd <= chunkText.length
      ) {
        startOffset = selectionStart;
        endOffset = selectionEnd;
        matchSource = "selection_offset";
      } else {
        const candidates = [row.raw.selected_text, row.raw.source_quote, row.raw.requirement_text].filter(
          (candidate): candidate is string => Boolean(candidate?.trim())
        );
        for (const candidate of candidates) {
          const index = chunkText.indexOf(candidate.trim());
          if (index >= 0) {
            startOffset = index;
            endOffset = index + candidate.trim().length;
            matchSource = candidate === row.raw.selected_text ? "selected_text" : "text_match";
            break;
          }
        }
      }

      if (startOffset == null || endOffset == null) return;
      fallbackHighlights.push({
        item_id: row.key,
        chunk_id: chunkId,
        start_offset: startOffset,
        end_offset: endOffset,
        risk_level: row.riskCode,
        status: row.statusCode,
        item_type: row.raw.item_type,
        match_source: matchSource,
        text: chunkText.slice(startOffset, endOffset)
      });
    });

    return fallbackHighlights.length ? [...reviewHighlights, ...fallbackHighlights] : reviewHighlights;
  }, [matrixRows, reviewHighlights]);
  const uncoveredChunkMap = useMemo(() => {
    return new Map(reviewUncoveredChunks.map((item) => [item.chunk.id, item]));
  }, [reviewUncoveredChunks]);
  const duplicateGroupByItemId = useMemo(() => {
    const map = new Map<string, MatrixReviewDuplicateGroup[]>();
    reviewDuplicateGroups.forEach((group) => {
      group.item_ids.forEach((itemId) => {
        map.set(itemId, [...(map.get(itemId) ?? []), group]);
      });
    });
    return map;
  }, [reviewDuplicateGroups]);
  const reviewHighlightByChunkId = useMemo(() => {
    const map = new Map<string, MatrixReviewHighlight[]>();
    effectiveReviewHighlights.forEach((highlight) => {
      map.set(highlight.chunk_id, [...(map.get(highlight.chunk_id) ?? []), highlight]);
    });
    return map;
  }, [effectiveReviewHighlights]);
  const reviewProgress = useMemo(() => {
    const confirmed = matrixRows.filter((row) => row.statusCode === "confirmed").length;
    const highRows = matrixRows.filter((row) => row.riskCode === "high");
    const highConfirmed = highRows.filter((row) => row.statusCode === "confirmed").length;
    return {
      total: matrixRows.length,
      confirmed,
      pending: matrixRows.length - confirmed,
      highTotal: highRows.length,
      highConfirmed
    };
  }, [matrixRows]);
  useEffect(() => {
    setPreflightExpanded(false);
  }, [selectedProjectId, selectedSectionId, preflightCheck?.status]);

  const preflightChecksForDisplay = useMemo(() => {
    if (!preflightCheck) return [];
    const scopedChecks = MVP13_DRAFT_WORKFLOW_AVAILABLE
      ? preflightCheck.checks
      : preflightCheck.checks.filter((item) => !mvp13PreflightCodes.has(item.code));
    const problemChecks = scopedChecks.filter((item) => item.status !== "pass");
    return problemChecks.length ? problemChecks : scopedChecks;
  }, [preflightCheck]);

  const preflightStatusForDisplay = useMemo(() => {
    if (!preflightCheck) return "pass";
    if (preflightChecksForDisplay.some((item) => item.status === "block")) return "block";
    if (preflightChecksForDisplay.some((item) => item.status === "warn")) return "warn";
    return "pass";
  }, [preflightCheck, preflightChecksForDisplay]);

  const visiblePreflightChecks = useMemo(
    () => (preflightExpanded ? preflightChecksForDisplay : preflightChecksForDisplay.slice(0, 4)),
    [preflightChecksForDisplay, preflightExpanded]
  );
  const hiddenPreflightCheckCount = Math.max(0, preflightChecksForDisplay.length - visiblePreflightChecks.length);
  const primaryBlockingPreflightCheck =
    preflightChecksForDisplay.find((item) => item.status === "block" && workflowStepForPreflightCheck(item)) ?? null;
  const primaryBlockingPreflightTarget = primaryBlockingPreflightCheck
    ? workflowStepForPreflightCheck(primaryBlockingPreflightCheck)
    : null;

  const ownerOptions = useMemo(() => {
    const pairs = matrixRows
      .filter((row) => row.ownerUserId)
      .map((row) => ({ value: row.ownerUserId as string, label: row.owner }));
    return Array.from(new Map(pairs.map((item) => [item.value, item])).values());
  }, [matrixRows]);

  const qualificationNeedsMaterialByItemId = useMemo(() => {
    const map = new Map<string, QualificationEvaluation>();
    qualificationEvaluations
      .filter((item) => item.evaluation_status === "needs_material")
      .forEach((item) => map.set(item.compliance_item_id, item));
    return map;
  }, [qualificationEvaluations]);
  const evidenceRows = useMemo(() => {
    return matrixRows.filter(
      (row) =>
        qualificationNeedsMaterialByItemId.has(row.key) ||
        (!row.enterpriseEvidenceNotRequired &&
          (row.enterpriseEvidenceCount === 0 || row.statusCode === "needs_material"))
    );
  }, [matrixRows, qualificationNeedsMaterialByItemId]);
  const blockingQualificationEvaluations = useMemo(
    () => qualificationEvaluations.filter((item) => item.is_blocking),
    [qualificationEvaluations]
  );
  const missingQualificationEvaluations = useMemo(
    () => blockingQualificationEvaluations.filter((item) => item.evaluation_status === "needs_material"),
    [blockingQualificationEvaluations]
  );
  const notSatisfiedQualificationEvaluations = useMemo(
    () => blockingQualificationEvaluations.filter((item) => item.evaluation_status === "not_satisfied"),
    [blockingQualificationEvaluations]
  );

  const unresolvedMatrixRows = useMemo(
    () => matrixRows.filter((row) => !isMatrixItemResolved(row)),
    [matrixRows]
  );
  const unresolvedHighRiskRows = useMemo(
    () => unresolvedMatrixRows.filter((row) => row.riskCode === "high"),
    [unresolvedMatrixRows]
  );
  const isMatrixComplete = matrixRows.length > 0 && unresolvedMatrixRows.length === 0;
  const qualificationDecisionConfirmed = qualificationDecision?.status === "confirmed";
  const qualificationDecisionNeedsConfirmation = Boolean(qualificationDecision && !qualificationDecisionConfirmed);
  const qualificationDecisionIsNoGo = qualificationDecision?.recommendation === "no_go";
  const contextPackQualificationGate = !qualificationDecision
    ? {
        status: "block",
        message: "先运行资格预评估并生成参标建议。",
        action: "去资格预评估"
      }
    : qualificationDecisionNeedsConfirmation
      ? {
          status: "block",
          message: "参标建议尚未人工确认。",
          action: "确认参标建议"
        }
      : qualificationDecisionIsNoGo
        ? {
            status: "block",
            message: "已确认 No-Go；ContextPack 只能作为风险快照。",
            action: "查看资格结论"
          }
        : qualificationDecision?.recommendation === "conditional_go"
          ? {
              status: "warn",
              message: "有条件 Go，确认 ContextPack 前请复核待补事项。",
              action: "查看资格结论"
            }
          : {
              status: "pass",
              message: "资格结论已确认，可确认 ContextPack。",
              action: "查看资格结论"
            };
  const contextPackHardBlockers = contextPackPreviewChecks.filter(
    (check) =>
      String(check.status ?? "warn") === "block" &&
      String(check.code ?? "") !== "qualification.no_go_confirmed"
  );
  const contextPackConfirmDisabledReason = !qualificationDecisionConfirmed
    ? contextPackQualificationGate.message
    : !contextPackPreview
      ? "请先预览并核对完整 ContextPack。"
      : contextPackHardBlockers.length
        ? "仍有硬阻断项，请按预览中的处理入口完成后重新预览。"
        : "";
  const canConfirmContextPack = Boolean(
    selectedProjectId &&
      selectedSectionId &&
      qualificationDecisionConfirmed &&
      contextPackPreview &&
      !contextPackHardBlockers.length
  );
  const mvp13DraftWorkflowAvailable = MVP13_DRAFT_WORKFLOW_AVAILABLE;
  const contextPackDraftGenerationAvailable = MVP13_DRAFT_WORKFLOW_AVAILABLE;
  const contextPackDraftGenerationTip =
    "基于已确认 ContextPack 生成结构化商务/资格草稿；需先确认参标建议且 ContextPack 无硬阻塞项。";
  const canGenerateContextPackDraft =
    contextPackDraftGenerationAvailable && Boolean(activeContextPack && qualificationDecisionConfirmed);
  const businessDraftGenerationActive = isAsyncTaskActive(
    businessDraftGenerationTask,
    businessDraftGenerationTaskId
  );
  const businessDraftGenerationProgress = asyncTaskProgress(
    businessDraftGenerationTask,
    businessDraftGenerationTaskId
  );
  const businessDraftGenerationStatusText = asyncTaskStatusText(
    businessDraftGenerationTask,
    businessDraftGenerationTaskId
  );
  const blockingContextPackChecks = contextPackChecks.filter((check) => String(check.status ?? "warn") !== "pass");
  const rawParseTaskActive = isAsyncTaskActive(importProcessing?.parseTask ?? null, importProcessing?.parseTaskId ?? null);
  const rawMatrixTaskActive = isAsyncTaskActive(importProcessing?.matrixTask ?? null, importProcessing?.matrixTaskId ?? null);
  const importProcessingVisible = Boolean(
    importProcessing &&
      importProcessing.projectId === selectedProjectId &&
      (!importProcessing.sectionId || importProcessing.sectionId === selectedSectionId) &&
      (importProcessing.parseTaskId || importProcessing.matrixTaskId)
  );
  const currentImportProcessing = importProcessingVisible ? importProcessing : null;
  const parseTaskActive = Boolean(importProcessingVisible && rawParseTaskActive);
  const matrixTaskActive = Boolean(importProcessingVisible && rawMatrixTaskActive);
  const importProcessingHasActiveTask = Boolean(importProcessingVisible && (parseTaskActive || matrixTaskActive));
  const importProcessingDone = Boolean(
    importProcessingVisible &&
      importProcessing &&
      isAsyncTaskTerminal(importProcessing.parseTask, importProcessing.parseTaskId) &&
      isAsyncTaskTerminal(importProcessing.matrixTask, importProcessing.matrixTaskId)
  );
  const importProcessingFailed = Boolean(
    importProcessingVisible &&
      importProcessing &&
      [importProcessing.parseTask, importProcessing.matrixTask].some((task) => task?.status === "failed")
  );
  const importProcessingParseFailed = Boolean(importProcessingVisible && importProcessing?.parseTask?.status === "failed");
  const importProcessingMatrixFailed = Boolean(importProcessingVisible && importProcessing?.matrixTask?.status === "failed");
  const importProcessingOpenTask = Boolean(importProcessingVisible && importProcessing && !importProcessingDone && !importProcessingFailed);
  const importProcessingInProgress = importProcessingOpenTask;
  const extractionBlocked = extractionQualityReport?.status === "blocked";
  const extractionQualityIssues = extractionQualityReport?.issues_json ?? [];
  const extractionQualityIssueCount = extractionQualityIssues.length || (extractionBlocked ? 1 : 0);
  const extractionBlockReason =
    extractionQualityIssues[0]?.message || "章节规划或合规抽取质量门禁未通过。";
  const importProcessingQualityBlocked = Boolean(
    importProcessingFailed &&
      (extractionBlocked || isQualityGateTaskError(importProcessing?.matrixTask?.error_code))
  );
  const importProcessingPercent = importProcessingProgress(currentImportProcessing);
  const importProcessingStageTitle = importProcessingQualityBlocked
    ? "质量门禁需要处理"
    : importProcessingParseFailed
    ? "文件解析失败"
    : importProcessingMatrixFailed
    ? "矩阵生成失败"
    : importProcessingFailed
    ? "后台处理失败"
    : !currentImportProcessing
      ? "当前没有后台任务"
      : importProcessingDone
      ? "后台处理已完成"
      : parseTaskActive
        ? "正在解析招标文件"
        : matrixTaskActive
          ? matrixTaskStageTitle(importProcessing?.matrixTask ?? null)
          : "后台任务排队中";
  const importProcessingStageMessage = importProcessingQualityBlocked
    ? "本轮结果已暂停写入，请先进入质量门禁页处理阻断项。"
    : importProcessingParseFailed
    ? "文件解析失败，请回到文件解析页查看失败文件，可重新解析或重新上传。"
    : importProcessingMatrixFailed
    ? "合规矩阵生成失败，请查看任务错误后重新生成矩阵；若为质量门禁问题，请先处理质检阻断。"
    : importProcessingFailed
    ? "查看失败原因后重新解析或重新生成矩阵。"
    : !currentImportProcessing
      ? "当前项目没有正在运行的解析或矩阵生成任务。"
      : importProcessingDone
      ? "解析版本和合规矩阵已刷新，可以继续审阅和确认。"
      : parseTaskActive
        ? taskProgressMessage(importProcessing?.parseTask ?? null, "正在读取文件、识别页码并切分条款。", "解析版本已生成。")
        : matrixTaskActive
          ? taskProgressMessage(
              importProcessing?.matrixTask ?? null,
              "正在抽取资格项、强制响应项和风险点。",
              "矩阵已生成并刷新。"
            )
          : "任务已提交，正在等待后台 worker 接手。";
  const matrixTaskOutput = importProcessingVisible ? importProcessing?.matrixTask?.output_json ?? null : null;
  const matrixForkJoinTotal = summaryNumber(matrixTaskOutput, "fork_join_total") || summaryNumber(matrixTaskOutput, "section_count");
  const matrixForkJoinCompleted = summaryNumber(matrixTaskOutput, "fork_join_completed");
  const matrixForkJoinPending = summaryNumber(matrixTaskOutput, "fork_join_pending");
  const matrixForkJoinWorkers = summaryNumber(matrixTaskOutput, "fork_join_max_workers");
	  const matrixForkJoinPendingSections = Array.isArray(matrixTaskOutput?.fork_join_pending_sections)
	    ? matrixTaskOutput.fork_join_pending_sections
	        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
	        .slice(0, 4)
	    : [];
  const knownMatrixCount = matrixRows.length || currentSection?.compliance_item_count || 0;
  const knownPendingMatrixCount = matrixRows.length
    ? unresolvedMatrixRows.length
    : currentSection?.pending_confirm_count ?? 0;
  const knownHighRiskCount = currentSection?.high_risk_count ?? matrixRows.filter((row) => row.riskCode === "high").length;
  const knownUnresolvedHighRiskCount = matrixRows.length
    ? unresolvedHighRiskRows.length
    : Math.min(knownPendingMatrixCount, knownHighRiskCount);
  const knownConfirmedMatrixCount = Math.max(0, knownMatrixCount - knownPendingMatrixCount);

	  const workflowSteps = useMemo<WorkflowStep[]>(() => {
		    const parsedDocuments = documents.filter((document) => isUsableParseStatus(document.current_version?.parse_status));
		    const missingEvidenceCount = evidenceRows.length;
		    const unresolvedMatrixCount = knownPendingMatrixCount;
		    const unresolvedTechnicalCount = technicalRows.filter((row) => !isMatrixItemResolved(row)).length;
    const highRiskCount = knownHighRiskCount;
    const unresolvedHighRiskCount = knownUnresolvedHighRiskCount;
    const pendingApprovals = mvp13DraftWorkflowAvailable
      ? approvalTasks.filter((task) => task.status === "pending").length
      : 0;
	    const hasDecision = Boolean(qualificationDecision);
	    const hasDraft = mvp13DraftWorkflowAvailable && businessDraftChapters.length > 0;
	    const hasSelectedScope = Boolean(selectedProjectId && selectedSectionId);
		    const hasUsableSource = parsedDocuments.length > 0 || knownMatrixCount > 0;
		    const hasMatrixResult = knownMatrixCount > 0;
	    const canOpenDocuments = hasSelectedScope;
	    const canOpenTasks = hasSelectedScope;
	    const canOpenQuality = hasUsableSource || Boolean(extractionQualityReport);
	    const canOpenMatrix = hasUsableSource;
		    const canOpenMatrixDerived = knownMatrixCount > 0;
		    const canOpenReview = knownMatrixCount > 0;
	    const canOpenChapter = (qualificationDecisionConfirmed || hasDraft) && !extractionBlocked;
	    const canOpenApproval =
	      mvp13DraftWorkflowAvailable && (hasDraft || approvalTasks.length > 0 || exportFiles.length > 0) && !extractionBlocked;
	    const contextPackStatus: WorkflowStepStatus = activeContextPack
	      ? activeContextPack.readiness_status === "block"
	        ? "risk"
	        : activeContextPack.readiness_status === "warn"
	          ? "todo"
	          : "done"
	      : qualificationDecisionConfirmed
	        ? "todo"
	        : qualificationDecisionNeedsConfirmation
	          ? "todo"
	          : hasDecision
	            ? "todo"
	            : "not_started";

    return [
      {
	        key: "documents",
	        title: "文件解析",
	        description: "上传或获取招标文件，并确认解析版本可用。",
	        status: hasUsableSource ? "done" : documents.length || parseTaskActive ? "todo" : "not_started",
	        statusText: parseTaskActive ? "解析中" : hasUsableSource ? "已完成" : documents.length ? "待解析" : "未开始",
		        actionText: documents.length ? "查看文件解析" : "上传/获取文件",
		        reason: parseTaskActive
	            ? "文件解析正在后台处理，完成后会自动刷新解析版本。"
	            : hasUsableSource
		          ? parsedDocuments.length
		            ? `已有 ${parsedDocuments.length} 份文件解析成功。`
		            : "当前标段已有合规矩阵结果，可视为文件解析链路已完成。"
		          : documents.length
		            ? "已有文件，但还没有可用的解析版本。"
		            : "先上传 Word/PDF 或从公开链接获取招标文件。",
	        disabled: !canOpenDocuments,
	        disabledReason: canOpenDocuments ? null : "请先选择项目和标段。"
	      },
      {
        key: "tasks",
        title: "任务中心",
        description: "查看文件解析和矩阵生成的后台进度。",
        status: importProcessingFailed
          ? "risk"
          : importProcessingInProgress
	            ? "todo"
		            : importProcessingDone || parsedDocuments.length || knownMatrixCount
	              ? "done"
              : documents.length
                ? "todo"
                : "not_started",
	        statusText: importProcessingFailed
	          ? "需要处理"
	          : importProcessingInProgress
	            ? `${importProcessingPercent}%`
		            : importProcessingDone || knownMatrixCount
	              ? "已完成"
		              : documents.length || parsedDocuments.length || knownMatrixCount
	                ? "可查看"
	                : "未开始",
        actionText: "进入任务中心",
        reason: importProcessingInProgress
          ? importProcessingStageMessage
          : importProcessingFailed
            ? "后台任务失败，请查看原因后重试或处理质量门禁。"
            : "集中查看解析、并发抽取、质量门禁和下一步动作。",
        disabled: !canOpenTasks,
        disabledReason: canOpenTasks ? null : "请先选择项目和标段。"
      },
	      {
	        key: "quality",
	        title: "质量门禁",
	        description: "处理章节规划、来源回链和漏抽覆盖等生成阻断。",
	        status: matrixTaskActive
	          && !matrixRows.length
	          ? "todo"
	          : extractionBlocked
	          ? "risk"
	          : hasMatrixResult
	            ? "done"
	          : extractionQualityReport?.status === "passed"
	            ? "done"
	            : parsedDocuments.length
              ? "todo"
              : "not_started",
        statusText: matrixTaskActive
          && !matrixRows.length
          ? "生成中"
	          : extractionBlocked
	            ? `${extractionQualityIssueCount} 个阻断`
	            : hasMatrixResult
	              ? "已通过"
	            : extractionQualityReport?.status === "passed"
	              ? "已通过"
	              : parsedDocuments.length
                ? "待生成"
                : "未开始",
        actionText: extractionBlocked ? "处理质量门禁" : "查看质量门禁",
        reason: extractionBlocked
          ? `发现 ${extractionQualityIssueCount} 个关键条款漏抽。建议点击“按建议处理”重新生成矩阵；上一版矩阵会保留。`
	          : extractionQualityReport?.status === "passed"
	            ? "最近一次抽取质量门禁已通过。"
	            : hasMatrixResult
	              ? "已生成合规矩阵且没有质量门禁阻断。"
	            : parsedDocuments.length
	              ? "生成矩阵时会自动执行质量门禁；如被阻断，可在这里逐项处理。"
	              : "需要先完成文件解析。",
        disabled: !canOpenQuality,
        disabledReason: canOpenQuality ? null : "请先完成文件解析，形成可用解析版本。"
      },
      {
        key: "matrix",
        title: "合规矩阵",
        description: "从招标文件中抽取资格项、强制响应项和风险点。",
	        status: matrixTaskActive
	          ? "todo"
	          : knownMatrixCount
          ? unresolvedMatrixCount
            ? unresolvedHighRiskCount
              ? "risk"
              : "todo"
            : "done"
          : parsedDocuments.length
            ? "todo"
            : "not_started",
	        statusText: matrixTaskActive
	          ? "生成中"
	          : knownMatrixCount
          ? unresolvedMatrixCount
            ? unresolvedHighRiskCount
              ? `${unresolvedHighRiskCount} 高风险待确认`
              : `${unresolvedMatrixCount} 待确认`
            : highRiskCount
              ? `已完成 · ${highRiskCount} 高风险已确认`
              : "已完成"
          : "未生成",
        actionText: matrixTaskActive && !matrixRows.length
          ? "查看处理状态"
          : preflightCheck?.matrix_outdated
          ? "重新生成矩阵"
	              : knownMatrixCount
            ? "查看合规矩阵"
            : "生成合规矩阵",
	        reason: matrixTaskActive && !matrixRows.length
            ? "合规矩阵正在后台生成，完成后会自动刷新矩阵和提交前核验。"
            : preflightCheck?.matrix_outdated
              ? "当前矩阵落后于最新解析版本，建议重新生成后再审阅。"
	              : knownMatrixCount
	          ? unresolvedMatrixCount
		            ? `当前有 ${knownMatrixCount} 条矩阵项，${unresolvedMatrixCount} 条仍需确认或补材料。${extractionBlocked ? " 质量门禁问题请到专门页面处理。" : ""}`
	            : "合规矩阵已全部人工确认，可以进入证据绑定和资格预评估。"
              : parsedDocuments.length
	            ? "文件已解析，可以生成合规矩阵。"
	            : "需要先完成文件解析。",
	        disabled: !canOpenMatrix,
	        disabledReason: canOpenMatrix ? null : "请先完成文件解析，形成可用解析版本。"
	      },
      {
        key: "review",
        title: "矩阵审阅",
        description: "左右对照原文和矩阵项，逐条核对来源、风险和确认状态。",
	        status: knownMatrixCount
          ? unresolvedMatrixCount
            ? unresolvedHighRiskCount
              ? "risk"
              : "todo"
            : "done"
          : "not_started",
	        statusText: knownMatrixCount
          ? unresolvedMatrixCount
            ? `${unresolvedMatrixCount} 待核对`
            : "已核对"
          : "未开始",
        actionText: "打开审阅台",
	        reason: knownMatrixCount
	          ? `已生成 ${knownMatrixCount} 条矩阵项，可在原文对照视图中核验来源。`
          : "需要先生成合规矩阵。",
        disabled: !canOpenReview,
        disabledReason: canOpenReview ? null : "请先生成合规矩阵。"
      },
      {
        key: "evidence",
        title: "证据绑定",
        description: "把企业资料绑定到矩阵项，补齐响应证据。",
	        status: knownMatrixCount
          ? missingEvidenceCount
            ? "todo"
            : "done"
          : "not_started",
	        statusText: knownMatrixCount ? (missingEvidenceCount ? `${missingEvidenceCount} 待处理` : "已完成") : "未开始",
        actionText: missingEvidenceCount ? "处理证据绑定" : "查看证据",
		        reason: knownMatrixCount
	          ? missingEvidenceCount
	            ? `还有 ${missingEvidenceCount} 条矩阵项缺少企业资料证据。`
	            : "矩阵项已绑定企业资料证据。"
	          : "需要先生成合规矩阵。",
	        disabled: !canOpenMatrixDerived,
	        disabledReason: canOpenMatrixDerived ? null : extractionBlocked ? extractionBlockReason : "请先生成合规矩阵。"
	      },
      {
        key: "technical",
        title: "技术响应",
        description: "预览技术要求、评分项和待确认项，行业闭环留到 1.1。",
        status: technicalRows.length
          ? unresolvedTechnicalCount
            ? "todo"
            : "done"
          : knownMatrixCount
            ? "done"
            : "not_started",
        statusText: technicalRows.length
          ? unresolvedTechnicalCount
            ? `${unresolvedTechnicalCount} 待确认`
            : "已整理"
          : knownMatrixCount
            ? "已预留"
            : "未开始",
        actionText: "查看技术响应",
	        reason: technicalRows.length
	          ? `已识别 ${technicalRows.length} 条技术响应或评分相关要求。`
	          : knownMatrixCount
	            ? "当前矩阵暂无明确技术响应项，产品选型和技术标生成将在 1.1 完成。"
	            : "需要先生成合规矩阵。",
	        disabled: !canOpenMatrixDerived,
	        disabledReason: canOpenMatrixDerived ? null : extractionBlocked ? extractionBlockReason : "请先生成合规矩阵。"
	      },
      {
        key: "qualification",
        title: "资格预评估",
        description: "基于矩阵和企业画像生成 Go/No-Go 建议。",
        status: hasDecision
          ? qualificationDecisionNeedsConfirmation
            ? "todo"
            : qualificationDecision?.recommendation === "no_go"
            ? "risk"
            : "done"
          : knownMatrixCount
            ? "todo"
            : "not_started",
        statusText: hasDecision
          ? qualificationDecisionNeedsConfirmation
            ? "待确认"
            : decisionLabels[qualificationDecision?.recommendation ?? ""] ?? "已生成"
          : "未评估",
        actionText: hasDecision
          ? qualificationDecisionNeedsConfirmation
            ? "确认参标建议"
            : "查看参标建议"
          : qualificationEvaluations.length
            ? "生成参标建议"
            : "运行资格预评估",
	        reason: hasDecision
	          ? qualificationDecisionNeedsConfirmation
              ? "参标建议已生成，需人工确认后再作为商务草稿上下文。"
              : qualificationDecision?.summary ?? "参标建议已生成。"
		          : knownMatrixCount
	            ? "矩阵已有候选项，可以运行资格预评估并生成参标建议。"
	            : "需要先生成合规矩阵。",
	        disabled: !canOpenMatrixDerived,
	        disabledReason: canOpenMatrixDerived ? null : extractionBlocked ? extractionBlockReason : "请先生成合规矩阵。"
	      },
      {
        key: "chapter",
        title: "ContextPack",
        description: "生成和确认商务/资格草稿上下文包，作为 MVP1.3 草稿生成输入。",
        status: contextPackStatus,
        statusText: activeContextPack
          ? preflightLabel(activeContextPack.readiness_status)
          : contextPackPreview
            ? "已预览"
            : "未生成",
        actionText: activeContextPack ? "查看 ContextPack" : "生成/确认 ContextPack",
	        reason: activeContextPack
	          ? "ContextPack 已生成；MVP1.2 到这里收口，草稿生成、事实校验和导出顺延到 MVP1.3。"
            : qualificationDecisionConfirmed && qualificationDecisionIsNoGo
              ? "参标建议为 No-Go；如仍需构建上下文包，需要先记录风险接受说明。"
		          : qualificationDecisionConfirmed
		            ? "参标建议已确认，可以预览并确认 ContextPack。"
		            : qualificationDecisionNeedsConfirmation
	                ? "参标建议还未人工确认，请先回到资格预评估确认结论。"
	                : "需要先完成资格预评估。",
	        disabled: !canOpenChapter,
	        disabledReason: canOpenChapter
            ? null
            : extractionBlocked
              ? extractionBlockReason
              : qualificationDecisionNeedsConfirmation
                ? "请先确认参标建议。"
                : "请先完成资格预评估，生成参标建议。"
	      },
      {
        key: "approval",
        title: "草稿导出（MVP1.3）",
        description: "基于已确认 ContextPack 生成草稿、校验事实并导出 Word。",
        status: "not_started",
        statusText: "MVP1.3",
        actionText: "MVP1.3 预留",
	        reason: "草稿生成、事实校验、审批导出统一放到 MVP1.3；MVP1.2 只确认 ContextPack。",
	        disabled: !canOpenApproval,
	        disabledReason: canOpenApproval ? null : "草稿生成、事实校验和导出将在 MVP1.3 开放。"
      }
	    ];
	  }, [
	    approvalTasks,
      activeContextPack,
	    businessDraftChapters,
      contextPackPreview,
	    documents,
	    evidenceRows.length,
      extractionBlocked,
      extractionBlockReason,
      extractionQualityIssues.length,
      extractionQualityReport?.status,
      importProcessingDone,
      importProcessingFailed,
      importProcessingHasActiveTask,
      importProcessingInProgress,
      importProcessingPercent,
      importProcessingStageMessage,
	    exportFiles.length,
	      matrixTaskActive,
		    matrixRows,
      knownHighRiskCount,
      knownMatrixCount,
      knownPendingMatrixCount,
      knownUnresolvedHighRiskCount,
	      parseTaskActive,
      preflightCheck?.matrix_outdated,
	    technicalRows,
	    qualificationDecision,
      qualificationDecisionConfirmed,
      qualificationDecisionIsNoGo,
      qualificationDecisionNeedsConfirmation,
      qualificationEvaluations.length,
	    selectedProjectId,
	    selectedSectionId,
	    unresolvedHighRiskRows.length,
	    unresolvedMatrixRows.length
	  ]);

  const recommendedStep = useMemo(() => {
    const parsedDocumentCount = documents.filter((document) => isUsableParseStatus(document.current_version?.parse_status)).length;
    const unresolvedTechnicalCount = technicalRows.filter((row) => !isMatrixItemResolved(row)).length;
    let preferredKey: WorkflowStepKey | null = null;

    if (importProcessingInProgress) {
      preferredKey = "tasks";
    } else if (importProcessingQualityBlocked || extractionBlocked) {
      preferredKey = "quality";
    } else if (!parsedDocumentCount) {
      preferredKey = "documents";
	    } else if (!knownMatrixCount || preflightCheck?.matrix_outdated) {
      preferredKey = "matrix";
	    } else if (knownUnresolvedHighRiskCount || knownPendingMatrixCount) {
      preferredKey = "review";
    } else if (evidenceRows.length) {
      preferredKey = "evidence";
    } else if (unresolvedTechnicalCount) {
      preferredKey = "technical";
    } else if (!qualificationDecision || qualificationDecisionNeedsConfirmation) {
      preferredKey = "qualification";
    } else if (primaryBlockingPreflightTarget && primaryBlockingPreflightTarget !== "approval") {
      preferredKey = primaryBlockingPreflightTarget;
    } else if (!activeContextPack) {
      preferredKey = "chapter";
    } else if (primaryBlockingPreflightTarget) {
      preferredKey = primaryBlockingPreflightTarget;
    } else {
      preferredKey = "approval";
    }

    return (
      workflowSteps.find((step) => step.key === preferredKey && !step.disabled) ??
      workflowSteps.find((step) => !step.disabled && (step.status === "risk" || step.status === "todo")) ??
      workflowSteps.find((step) => !step.disabled && step.status === "not_started") ??
      workflowSteps.find((step) => !step.disabled) ??
      workflowSteps[workflowSteps.length - 1]
    );
  }, [
    activeContextPack,
    documents,
    evidenceRows.length,
    extractionBlocked,
    importProcessingInProgress,
    importProcessingQualityBlocked,
	    knownMatrixCount,
	    knownPendingMatrixCount,
	    knownUnresolvedHighRiskCount,
	      mvp13DraftWorkflowAvailable,
	    preflightCheck?.matrix_outdated,
    primaryBlockingPreflightTarget,
    qualificationDecision,
    qualificationDecisionNeedsConfirmation,
    technicalRows,
	    workflowSteps
  ]);

  const recommendedPreflightCheck = recommendedStep
    ? preflightChecksForDisplay.find(
        (item) => item.status === "block" && workflowStepForPreflightCheck(item) === recommendedStep.key
      ) ??
      preflightChecksForDisplay.find(
        (item) => item.status === "warn" && workflowStepForPreflightCheck(item) === recommendedStep.key
      ) ??
      null
    : null;

  const simpleWorkflowSteps = useMemo<SimpleWorkflowStep[]>(() => {
    const byKey = new Map(workflowSteps.map((step) => [step.key, step]));
	    const group = (key: string, title: string, targetKey: WorkflowStepKey, activeKeys: WorkflowStepKey[]) => {
	      const groupSteps = activeKeys.map((stepKey) => byKey.get(stepKey)).filter(Boolean) as WorkflowStep[];
	      const targetStep = byKey.get(targetKey) ?? groupSteps[0];
	      const waitsForCurrentTask = importProcessingOpenTask && key !== "prepare" && key !== "tasks";
	      const status: WorkflowStepStatus = groupSteps.some((step) => step.status === "risk")
        ? "risk"
        : groupSteps.some((step) => step.status === "todo")
          ? "todo"
          : groupSteps.length && groupSteps.every((step) => step.status === "done")
            ? "done"
            : groupSteps.some((step) => step.status === "not_started")
              ? "not_started"
	          : targetStep?.status ?? "not_started";
	      const resolvedStatus = waitsForCurrentTask ? "not_started" : status;
	      const isDone = resolvedStatus === "done";

	      return {
	        key,
	        title,
	        targetKey,
	        activeKeys,
	        status: resolvedStatus,
	        statusText: waitsForCurrentTask ? "待更新" : targetStep?.statusText ?? "未开始",
	        reason: waitsForCurrentTask ? "后台任务完成后会刷新本步骤结果。" : targetStep?.reason ?? "",
	        disabled: isDone ? false : waitsForCurrentTask ? true : targetStep?.disabled ?? true,
	        disabledReason: isDone
	          ? null
	          : waitsForCurrentTask
	            ? "请先等待第二步后台任务完成。"
	            : targetStep?.disabledReason ?? "请先完成前置步骤。"
	      };
	    };

    return [
      group("prepare", "上传文件", "documents", ["documents"]),
      group("tasks", "等待系统", "tasks", ["tasks"]),
      group("quality", "质检处理", "quality", ["quality"]),
      group("review", "审阅条款", knownMatrixCount ? "review" : "matrix", ["matrix", "review"]),
      group("evidence", "绑定资料", "evidence", ["evidence"]),
      group(
        "decision",
        "资格/技术",
        technicalRows.some((row) => !isMatrixItemResolved(row)) ? "technical" : "qualification",
        ["technical", "qualification"]
      ),
      group("draft", "上下文包", "chapter", ["chapter"])
    ];
  }, [importProcessingOpenTask, knownMatrixCount, technicalRows, workflowSteps]);

  useEffect(() => {
    if (!selectedSectionId || !recommendedStep) return;
    if (selectedTreeKey === `section:${selectedSectionId}`) {
      setActiveTab(recommendedStep.key);
      setSelectedTreeKey(`section:${selectedSectionId}:${recommendedStep.key}`);
    }
  }, [recommendedStep, selectedSectionId, selectedTreeKey]);

  const homeTodoRows = useMemo<HomeTodoRow[]>(() => {
    const matrixTodos = matrixRows
      .filter((row) => row.statusCode === "pending_confirm" || row.statusCode === "needs_material")
      .slice(0, 3)
      .map((row) => ({
        key: row.key,
        task: `${row.status}：${truncateText(row.requirement)}`,
        project: currentProject?.name ?? "当前项目",
        owner: row.owner,
        due: formatShortTime(currentSection?.bid_deadline_at ?? currentProject?.bid_deadline_at ?? null),
        priority: row.risk
      }));
    const fileTodos = sections
      .filter((section) => section.document_count === 0)
      .map((section) => ({
        key: `upload:${section.id}`,
        task: "上传招标文件",
        project: currentProject?.name ?? "当前项目",
        owner: "业务负责人",
        due: formatShortTime(section.bid_deadline_at),
        priority: "中"
      }));
    return [...matrixTodos, ...fileTodos].slice(0, 5);
  }, [currentProject?.bid_deadline_at, currentProject?.name, currentSection?.bid_deadline_at, matrixRows, sections]);

  const assistantMessages = useMemo(() => {
    const highRisk = unresolvedHighRiskRows[0];
    const pending = unresolvedMatrixRows.find((row) => row.statusCode === "pending_confirm");
    return [
      {
        key: "matrix",
        title: isMatrixComplete ? "合规矩阵已完成" : highRisk ? "发现高风险待确认项" : "待确认合规项",
        content: highRisk
          ? `${highRisk.owner} 负责的条款仍处于 ${highRisk.status} 状态，请优先处理。`
          : pending
            ? `${pending.owner} 负责的条款等待人工确认。`
            : isMatrixComplete
              ? "所有矩阵项已人工确认，建议继续处理证据绑定和资格预评估。"
              : "当前标段暂无高风险待确认项。",
        targetRowKey: highRisk?.key ?? pending?.key,
        action: highRisk || pending ? "定位条款" : isMatrixComplete ? "进入下一步" : "查看矩阵"
      },
      {
        key: "suggestion",
        title: isMatrixComplete ? "下一步建议" : "可生成响应建议",
        content: isMatrixComplete
          ? evidenceRows.length
            ? `还有 ${evidenceRows.length} 条矩阵项需要绑定企业资料证据。`
            : "证据已齐备，可以运行资格预评估并生成参标建议。"
          : "当前矩阵项已绑定原文证据，可在确认后继续生成章节草稿。",
        targetRowKey: undefined,
        action: isMatrixComplete ? "继续流程" : "生成草稿"
      }
    ];
  }, [evidenceRows.length, isMatrixComplete, unresolvedHighRiskRows, unresolvedMatrixRows]);

  const displayedLogs = useMemo(() => {
    const persistedLogs = auditLogs.map((log) => {
      const time = dayjs(log.created_at).format("HH:mm");
      return `${time} ${auditActionText(log)}${log.reason ? `：${log.reason}` : ""}`;
    });
    return [...actionLogs, ...persistedLogs].slice(0, 6);
  }, [actionLogs, auditLogs]);
  const focusQualityAssistant = activeTab === "quality" && extractionBlocked;

  const appendLog = useCallback((content: string) => {
    setActionLogs((logs) => [`刚刚 ${content}`, ...logs].slice(0, 5));
  }, []);

  const reloadMatrix = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return [];
    setLoadingMatrix(true);
    try {
      const data = await listComplianceItems(selectedProjectId, selectedSectionId, { limit: COMPLIANCE_ITEM_FETCH_LIMIT });
      setComplianceItems(data);
      setSelectedRowKeys([]);
      return data;
    } finally {
      setLoadingMatrix(false);
    }
  }, [selectedProjectId, selectedSectionId]);

  const reloadMatrixReview = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId || activeTab !== "review") return;
    const review = await getMatrixReview(selectedProjectId, selectedSectionId);
    setReviewChunks(review.chunks);
    setReviewOpenXmlDocument(review.review_document);
    setReviewHighlights(review.highlights);
    setComplianceItems(review.items);
    setReviewUncoveredChunks(review.uncovered_chunks);
    setReviewDuplicateGroups(review.duplicate_groups);
    return review;
  }, [activeTab, selectedProjectId, selectedSectionId]);

  const reloadAuditLogs = useCallback(async () => {
    if (!selectedProjectId) return;
    const data = await listAuditLogs(selectedProjectId);
    setAuditLogs(data);
  }, [selectedProjectId]);

  const reloadWorkspaceSummary = useCallback(async () => {
    if (!selectedProjectId) return;
    const [detail, sectionData] = await Promise.all([
      getProject(selectedProjectId),
      listSections(selectedProjectId)
    ]);
    setProjectDetail(detail);
    setSections(sectionData);
  }, [selectedProjectId]);

  const reloadDocumentsAndExports = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const [documentData, exportData] = await Promise.all([
      listDocuments(selectedProjectId, selectedSectionId),
      listExportFiles(selectedProjectId, selectedSectionId)
    ]);
    setDocuments(documentData);
    setExportFiles(exportData);
  }, [selectedProjectId, selectedSectionId]);

  const reloadQualificationEvaluations = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const data = await listQualificationEvaluations(selectedProjectId, selectedSectionId);
    setQualificationEvaluations(data);
    return data;
  }, [selectedProjectId, selectedSectionId]);

  const reloadQualificationDecision = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const decision = await getQualificationDecision(selectedProjectId, selectedSectionId);
    setQualificationDecision(decision);
  }, [selectedProjectId, selectedSectionId]);

  const reloadBusinessDraftChapters = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const chapters = await listBusinessDraftChapters(selectedProjectId, selectedSectionId);
    setBusinessDraftChapters(chapters);
    setSelectedDraftChapterId((current) => {
      if (current && chapters.some((chapter) => chapter.id === current)) return current;
      return chapters[0]?.id ?? "";
    });
  }, [selectedProjectId, selectedSectionId]);

  const reloadBusinessDraftContext = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const [contextPacks, blocks] = await Promise.all([
      listBusinessDraftContextPacks(selectedProjectId, selectedSectionId),
      listBusinessDraftBlocks(selectedProjectId, selectedSectionId)
    ]);
    setBusinessDraftContextPacks(contextPacks);
    setDraftBlocks(blocks);
  }, [selectedProjectId, selectedSectionId]);

  const reloadApprovalTasks = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const tasks = await listApprovalTasks(selectedProjectId, selectedSectionId);
    setApprovalTasks(tasks);
  }, [selectedProjectId, selectedSectionId]);

  const reloadPreflightCheck = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const data = await getPreflightCheck(selectedProjectId, selectedSectionId);
    setPreflightCheck(data);
  }, [selectedProjectId, selectedSectionId]);

  const refreshMatrixRelatedPanels = useCallback(async () => {
    await Promise.all([
      reloadAuditLogs(),
      reloadWorkspaceSummary(),
      reloadDocumentsAndExports(),
      reloadQualificationEvaluations(),
      reloadQualificationDecision(),
      reloadBusinessDraftChapters(),
      reloadBusinessDraftContext(),
      reloadApprovalTasks(),
      reloadPreflightCheck()
    ]);
  }, [
    reloadApprovalTasks,
    reloadAuditLogs,
    reloadBusinessDraftChapters,
    reloadBusinessDraftContext,
    reloadDocumentsAndExports,
    reloadPreflightCheck,
    reloadQualificationDecision,
    reloadQualificationEvaluations,
    reloadWorkspaceSummary
  ]);

  const refreshAfterMatrixMutation = useCallback(async () => {
    setContextPackPreview(null);
    setContextPackPreviewOpen(false);
    const [matrixItems, review] = await Promise.all([reloadMatrix(), reloadMatrixReview()]);
    void refreshMatrixRelatedPanels().catch((error) => {
      if (isHttpNotFoundError(error)) return;
      appendLog(error instanceof Error ? "后台刷新工作台摘要失败，矩阵结果已保存" : "后台刷新工作台摘要失败");
    });
    return review?.items ?? matrixItems ?? [];
  }, [
    appendLog,
    reloadMatrix,
    reloadMatrixReview,
    refreshMatrixRelatedPanels
  ]);

  useEffect(() => {
    saveImportProcessingState(importProcessing);
  }, [
    importProcessing?.projectId,
    importProcessing?.sectionId,
    importProcessing?.parseTaskId,
    importProcessing?.matrixTaskId
  ]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId || importProcessingHasActiveTask) return;
    let active = true;

    const recoverActiveTasks = async () => {
      const tasks = await listTasks({
        project_id: selectedProjectId,
        section_id: selectedSectionId,
        active: true,
        limit: 10
      });
      if (!active) return;
      const parseTask =
        tasks.find((task) => task.task_type === "document_parse" && !isAsyncTaskStale(task)) ?? null;
      const matrixTask =
        tasks.find((task) => task.task_type === "matrix_generate" && !isAsyncTaskStale(task)) ?? null;
      if (!parseTask && !matrixTask) return;
      setImportProcessing({
        projectId: selectedProjectId,
        sectionId: selectedSectionId,
        parseTaskId: parseTask?.id ?? null,
        matrixTaskId: matrixTask?.id ?? null,
        parseTask,
        matrixTask
      });
    };

    void recoverActiveTasks().catch(() => {
      // Best-effort recovery; normal polling continues when this tab started the task.
    });

    return () => {
      active = false;
    };
  }, [
    importProcessingHasActiveTask,
    selectedProjectId,
    selectedSectionId
  ]);

  useEffect(() => {
    if (!importProcessing) return;
    let active = true;
    let clearTimer: number | null = null;

    const pollTasks = async () => {
      const [parseTask, matrixTask] = await Promise.all([
        importProcessing.parseTaskId ? getTask(importProcessing.parseTaskId) : Promise.resolve(null),
        importProcessing.matrixTaskId ? getTask(importProcessing.matrixTaskId) : Promise.resolve(null)
      ]);
      if (!active) return;

      const staleTask = [parseTask, matrixTask].find((task) => isAsyncTaskStale(task));
      if (staleTask) {
        appendLog(`后台任务 ${staleTask.id.slice(0, 8)} 长时间未更新，已停止自动刷新`);
        setImportProcessing((current) => {
          if (
            current?.projectId === importProcessing.projectId &&
            current?.sectionId === importProcessing.sectionId &&
            current?.parseTaskId === importProcessing.parseTaskId &&
            current?.matrixTaskId === importProcessing.matrixTaskId
          ) {
            return null;
          }
          return current;
        });
        return;
      }

      setImportProcessing((current) => {
        if (
          !current ||
          current.projectId !== importProcessing.projectId ||
          current.sectionId !== importProcessing.sectionId ||
          current.parseTaskId !== importProcessing.parseTaskId ||
          current.matrixTaskId !== importProcessing.matrixTaskId
        ) {
          return current;
        }
        return {
          ...current,
          parseTask,
          matrixTask
        };
      });

      const terminalRefreshKeys = [
        importProcessing.parseTaskId && parseTask && isAsyncTaskTerminalStatus(parseTask.status)
          ? `${parseTask.id}:${parseTask.status}`
          : null,
        importProcessing.matrixTaskId && matrixTask && isAsyncTaskTerminalStatus(matrixTask.status)
          ? `${matrixTask.id}:${matrixTask.status}`
          : null
      ].filter((key): key is string => Boolean(key));
      const newTerminalRefreshKeys = terminalRefreshKeys.filter(
        (key) => !terminalTaskRefreshKeysRef.current.has(key)
      );

      if (newTerminalRefreshKeys.length) {
        newTerminalRefreshKeys.forEach((key) => terminalTaskRefreshKeysRef.current.add(key));
        await Promise.all([
          reloadWorkspaceSummary(),
          reloadDocumentsAndExports(),
          reloadMatrix(),
          reloadPreflightCheck(),
          reloadAuditLogs()
        ]);
      }

      const parseTerminal = isAsyncTaskTerminal(parseTask, importProcessing.parseTaskId);
      const matrixTerminal = isAsyncTaskTerminal(matrixTask, importProcessing.matrixTaskId);
      if (parseTerminal && matrixTerminal && !clearTimer) {
        clearTimer = window.setTimeout(() => {
          setImportProcessing((current) => {
            if (
              current?.projectId === importProcessing.projectId &&
              current?.sectionId === importProcessing.sectionId &&
              current?.parseTaskId === importProcessing.parseTaskId &&
              current?.matrixTaskId === importProcessing.matrixTaskId
            ) {
              return null;
            }
            return current;
          });
        }, 8000);
      }
    };

    void pollTasks().catch((error: unknown) => {
      setApiError(error instanceof Error ? error.message : "后台任务状态刷新失败");
    });
    const intervalId = window.setInterval(() => {
      void pollTasks().catch((error: unknown) => {
        setApiError(error instanceof Error ? error.message : "后台任务状态刷新失败");
      });
    }, 1500);

    return () => {
      active = false;
      window.clearInterval(intervalId);
      if (clearTimer) window.clearTimeout(clearTimer);
    };
  }, [
    appendLog,
    importProcessing?.projectId,
    importProcessing?.sectionId,
    importProcessing?.parseTaskId,
    importProcessing?.matrixTaskId,
    reloadAuditLogs,
    reloadDocumentsAndExports,
    reloadMatrix,
    reloadPreflightCheck,
    reloadWorkspaceSummary
  ]);

  useEffect(() => {
    if (!businessDraftGenerationTaskId) return;
    let active = true;
    let clearTimer: number | null = null;

    const pollBusinessDraftTask = async () => {
      const task = await getTask(businessDraftGenerationTaskId);
      if (!active) return;
      setBusinessDraftGenerationTask(task);

      if (!isAsyncTaskTerminalStatus(task.status)) return;
      const terminalKey = `${task.id}:${task.status}`;
      if (businessDraftTerminalTaskRef.current.has(terminalKey)) return;
      businessDraftTerminalTaskRef.current.add(terminalKey);
      setLoadingBusinessDraft(false);

      if (task.status === "succeeded") {
        await Promise.all([
          reloadBusinessDraftChapters(),
          reloadBusinessDraftContext(),
          reloadPreflightCheck(),
          reloadApprovalTasks(),
          reloadAuditLogs()
        ]);
        setViewMode("workspace");
        setActiveTab("chapter");
        setWorkspaceNode("chapter");
        appendLog(
          `商务草稿生成完成：${summaryNumber(task.output_json, "chapter_count")} 章，${summaryNumber(task.output_json, "block_count")} 个 block`
        );
        Modal.success({
          title: "草稿已生成",
          content: "已刷新商务标章节和结构化 block，请继续审阅待补证据和待补事实。",
          okText: "知道了"
        });
      } else {
        const message = task.error_message || "商务草稿生成任务失败";
        setApiError(message);
        appendLog(`商务草稿生成失败：${truncateText(message, 48)}`);
      }

      clearTimer = window.setTimeout(() => {
        if (!active) return;
        setBusinessDraftGenerationTaskId(null);
        setBusinessDraftGenerationTask(null);
      }, 8000);
    };

    void pollBusinessDraftTask().catch((error: unknown) => {
      setLoadingBusinessDraft(false);
      setApiError(error instanceof Error ? error.message : "商务草稿任务状态刷新失败");
    });
    const intervalId = window.setInterval(() => {
      void pollBusinessDraftTask().catch((error: unknown) => {
        setLoadingBusinessDraft(false);
        setApiError(error instanceof Error ? error.message : "商务草稿任务状态刷新失败");
      });
    }, 1500);

    return () => {
      active = false;
      window.clearInterval(intervalId);
      if (clearTimer) window.clearTimeout(clearTimer);
    };
  }, [
    appendLog,
    businessDraftGenerationTaskId,
    reloadApprovalTasks,
    reloadAuditLogs,
    reloadBusinessDraftChapters,
    reloadBusinessDraftContext,
    reloadPreflightCheck
  ]);

  const runMaterialSearch = useCallback(async (query: string) => {
    setMaterialSearchQuery(query);
    setLoadingMaterialSearch(true);
    try {
      const data = await searchEnterpriseMaterials({ query, limit: 12 });
      setMaterialSearchResults(data);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业资料检索失败");
    } finally {
      setLoadingMaterialSearch(false);
    }
  }, []);

  const openEvidenceBindingDrawer = useCallback(
    async (row: MatrixRow) => {
      if (!selectedProjectId || !selectedSectionId) return;
      setOpeningEvidenceItemId(row.key);
      setEvidenceDrawer(row);
      setEvidenceBindings([]);
      setMaterialSearchResults([]);
      setMaterialSearchQuery(row.requirement);
      setLoadingMaterialSearch(true);
      try {
        const [bindings, results] = await Promise.all([
          listComplianceEvidenceBindings(selectedProjectId, selectedSectionId, row.key),
          searchEnterpriseMaterials({ query: row.requirement, limit: 12 })
        ]);
        setEvidenceBindings(bindings);
        setMaterialSearchResults(results);
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "证据绑定信息加载失败");
      } finally {
        setLoadingMaterialSearch(false);
        setOpeningEvidenceItemId((current) => (current === row.key ? "" : current));
      }
    },
    [selectedProjectId, selectedSectionId]
  );

  const reloadEvidenceBindings = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId || !evidenceDrawer) return;
    const bindings = await listComplianceEvidenceBindings(selectedProjectId, selectedSectionId, evidenceDrawer.key);
    setEvidenceBindings(bindings);
  }, [evidenceDrawer, selectedProjectId, selectedSectionId]);

  const handleBindEvidence = useCallback(
    async (material: EnterpriseMaterialSearchResult) => {
      if (!selectedProjectId || !selectedSectionId || !evidenceDrawer) return;
      if (bindingMaterialId) return;
      if (material.verification_status === "conflict" || material.verification_status === "expired") {
        Modal.warning({ title: "该资料暂不可绑定", content: "冲突或过期资料不能作为响应证据绑定。" });
        return;
      }
      if (evidenceBindings.some((binding) => binding.enterprise_material_id === material.id)) {
        Modal.info({ title: "资料已绑定", content: "该资料已经绑定到当前条款，无需重复绑定。" });
        return;
      }
      setBindingMaterialId(material.id);
      try {
        const shouldRefreshQualification =
          evidenceDrawer.raw.item_type === "qualification" ||
          qualificationNeedsMaterialByItemId.has(evidenceDrawer.key);
        await bindComplianceEvidence(selectedProjectId, selectedSectionId, evidenceDrawer.key, {
          enterprise_material_id: material.id,
          evidence_text: material.snippet ?? material.evidence_text ?? material.name,
          confidence_score: material.confidence_score.toFixed(4),
          reason: `绑定企业资料：${material.name}`
        });
        appendLog(`绑定企业资料证据：${truncateText(material.name, 18)}`);
        if (shouldRefreshQualification) {
          setEvaluatingQualification(true);
          setGeneratingDecision(true);
          try {
            setContextPackPreview(null);
            setContextPackPreviewOpen(false);
            await Promise.all([reloadEvidenceBindings(), reloadMatrix(), reloadMatrixReview()]);
            await reloadQualificationEvaluations();
            const decision = await generateQualificationDecision(selectedProjectId, selectedSectionId);
            setQualificationDecision(decision);
            appendLog(`已刷新资格预评估和参标建议：${decisionLabels[decision.recommendation] ?? decision.recommendation}`);
            await Promise.all([reloadApprovalTasks(), reloadAuditLogs(), reloadPreflightCheck()]);
          } finally {
            setEvaluatingQualification(false);
            setGeneratingDecision(false);
          }
        } else {
          await Promise.all([reloadEvidenceBindings(), refreshAfterMatrixMutation()]);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "证据绑定失败";
        if (message.includes("already bound") || message.includes("409")) {
          await reloadEvidenceBindings().catch(() => undefined);
          Modal.info({ title: "资料已绑定", content: "该资料已经绑定到当前条款，列表已刷新。" });
        } else {
          setApiError(message);
        }
      } finally {
        setBindingMaterialId("");
      }
    },
    [
      appendLog,
      bindingMaterialId,
      evidenceDrawer,
      evidenceBindings,
      generateQualificationDecision,
      qualificationNeedsMaterialByItemId,
      refreshAfterMatrixMutation,
      reloadEvidenceBindings,
      reloadApprovalTasks,
      reloadAuditLogs,
      reloadMatrix,
      reloadMatrixReview,
      reloadPreflightCheck,
      reloadQualificationEvaluations,
      selectedProjectId,
      selectedSectionId
    ]
  );

  const handleWaiveEvidenceRequirement = useCallback(
    (row: MatrixRow) => {
      if (!selectedProjectId || !selectedSectionId) return;
      let reason = row.enterpriseEvidenceNotRequiredReason || "人工判定该条款无需绑定企业资料证据";
      Modal.confirm({
        title: "标记为无需绑定证据",
        content: (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Text>{truncateText(row.requirement, 96)}</Text>
            <Text type="secondary">
              适用于资格后审方式、提示性说明等不依赖本企业资料作为响应证据的条款；该条将不再计入缺证据预检。
            </Text>
            <TextArea
              defaultValue={reason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) => {
                reason = event.target.value;
              }}
            />
          </Space>
        ),
        okText: "无需绑定证据",
        cancelText: "取消",
        onOk: async () => {
          if (!reason.trim()) {
            Modal.warning({ title: "需要填写判断原因" });
            throw new Error("reason required");
          }
          setWaivingEvidenceItemId(row.key);
          try {
            await waiveComplianceEvidenceRequirement(selectedProjectId, selectedSectionId, row.key, {
              reason: reason.trim()
            });
            appendLog(`标记无需绑定证据：${truncateText(row.requirement, 18)}`);
            if (evidenceDrawer?.key === row.key) {
              setEvidenceDrawer(null);
              setEvidenceBindings([]);
              setMaterialSearchResults([]);
            }
            if (activeTab === "review") {
              await reloadMatrixReview();
            } else {
              await reloadMatrix();
            }
            void refreshMatrixRelatedPanels().catch((error) => {
              if (isHttpNotFoundError(error)) return;
              appendLog(error instanceof Error ? "后台刷新工作台摘要失败，证据豁免结果已保存" : "后台刷新工作台摘要失败");
            });
          } catch (error) {
            setApiError(error instanceof Error ? error.message : "标记无需绑定证据失败");
            throw error;
          } finally {
            setWaivingEvidenceItemId("");
          }
        }
      });
    },
    [
      appendLog,
      activeTab,
      evidenceDrawer?.key,
      refreshMatrixRelatedPanels,
      reloadMatrix,
      reloadMatrixReview,
      selectedProjectId,
      selectedSectionId,
      waiveComplianceEvidenceRequirement
    ]
  );

  const handleUnbindEvidence = useCallback(
    (binding: ComplianceEvidenceBinding) => {
      let reason = "解除企业资料证据绑定";
      Modal.confirm({
        title: "解除证据绑定",
        content: (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Text>{binding.material_name ?? "企业资料"}</Text>
            <TextArea
              defaultValue={reason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) => {
                reason = event.target.value;
              }}
            />
          </Space>
        ),
        okText: "解除",
        cancelText: "取消",
        onOk: async () => {
          if (!selectedProjectId || !selectedSectionId || !evidenceDrawer || !reason.trim()) {
            Modal.warning({ title: "需要填写解除原因" });
            throw new Error("reason required");
          }
          setUnbindingId(binding.id);
          try {
            await unbindComplianceEvidence(
              selectedProjectId,
              selectedSectionId,
              evidenceDrawer.key,
              binding.id,
              { reason: reason.trim() }
            );
            appendLog(`解除企业资料证据：${truncateText(binding.material_name ?? "企业资料", 18)}`);
            await Promise.all([reloadEvidenceBindings(), refreshAfterMatrixMutation()]);
          } catch (error) {
            setApiError(error instanceof Error ? error.message : "解除证据绑定失败");
            throw error;
          } finally {
            setUnbindingId("");
          }
        }
      });
    },
    [
      appendLog,
      evidenceDrawer,
      refreshAfterMatrixMutation,
      reloadEvidenceBindings,
      selectedProjectId,
      selectedSectionId
    ]
  );

  const setWorkspaceNode = useCallback(
    (tab: string, sectionId = selectedSectionId) => {
    if (!sectionId) return;
    setSelectedTreeKey(`section:${sectionId}:${tab}`);
  },
    [selectedSectionId]
  );

  const activateWorkflowStep = useCallback(
    (stepKey: WorkflowStepKey) => {
      const targetStep = workflowSteps.find((step) => step.key === stepKey);
      if (targetStep?.disabled) {
        appendLog(targetStep.disabledReason ?? "请先完成前置步骤");
        return;
      }
      setViewMode("workspace");
      setActiveTab(stepKey);
      setWorkspaceNode(stepKey);
    },
    [appendLog, setWorkspaceNode, workflowSteps]
  );

  useEffect(() => {
    const activeStep = workflowSteps.find((step) => step.key === activeTab);
    if (!activeStep?.disabled || !recommendedStep || recommendedStep.key === activeTab) return;
    setActiveTab(recommendedStep.key);
    setWorkspaceNode(recommendedStep.key);
  }, [activeTab, recommendedStep, setWorkspaceNode, workflowSteps]);

  const locateMatrixRow = useCallback(
    (rowKey?: string) => {
      setViewMode("workspace");
      setActiveTab("matrix");
      setWorkspaceNode("matrix");
      if (!rowKey) return;
      setHighlightedRowKey(rowKey);
      appendLog("定位风险或待确认条款并高亮对应矩阵行");
      window.setTimeout(() => {
        document.querySelector(`[data-row-key="${rowKey}"]`)?.scrollIntoView({
          block: "center",
          behavior: "smooth"
        });
      }, 80);
      window.setTimeout(() => setHighlightedRowKey(""), 2800);
    },
    [appendLog, setWorkspaceNode]
  );

  const openQualificationEvidenceWork = useCallback(() => {
    setViewMode("workspace");
    setActiveTab("evidence");
    setWorkspaceNode("evidence");
    const targetEvaluation = missingQualificationEvaluations[0];
    const targetRow =
      (targetEvaluation && matrixRows.find((row) => row.key === targetEvaluation.compliance_item_id)) ??
      evidenceRows[0];
    if (!targetRow) {
      appendLog("资格缺材料项暂未匹配到矩阵条款，请先回到矩阵审阅核对条款状态");
      return;
    }
    setHighlightedRowKey(targetRow.key);
    window.setTimeout(() => {
      document.querySelector(`[data-row-key="${targetRow.key}"]`)?.scrollIntoView({
        block: "center",
        behavior: "smooth"
      });
    }, 120);
    window.setTimeout(() => setHighlightedRowKey(""), 2800);
    void openEvidenceBindingDrawer(targetRow);
  }, [
    appendLog,
    evidenceRows,
    matrixRows,
    missingQualificationEvaluations,
    openEvidenceBindingDrawer,
    setWorkspaceNode
  ]);

  const focusDraftBlock = useCallback(
    (block: DraftBlock) => {
      setViewMode("workspace");
      setActiveTab("chapter");
      setWorkspaceNode("chapter");
      if (block.chapter_id) {
        setSelectedDraftChapterId(block.chapter_id);
      }
      setActiveDraftBlockId(block.id);
      appendLog("定位合规条目对应的草稿 block");
      window.setTimeout(() => {
        document.querySelector(`[data-draft-block-id="${block.id}"]`)?.scrollIntoView({
          block: "center",
          behavior: "smooth"
        });
      }, 160);
      window.setTimeout(() => setActiveDraftBlockId(""), 3000);
    },
    [appendLog, setWorkspaceNode]
  );

  const locateDraftBlockForRow = useCallback(
    (rowKey: string) => {
      const block = draftBlocksByComplianceItemId.get(rowKey)?.[0];
      if (!block) {
        appendLog("当前条款尚未覆盖到结构化草稿 block");
        return;
      }
      focusDraftBlock(block);
    },
    [appendLog, draftBlocksByComplianceItemId, focusDraftBlock]
  );

  const focusReviewRow = useCallback((row: MatrixRow) => {
    setActiveReviewItemId(row.key);
    setLocatingReviewItemId(row.key);
    const filteredIndex = matrixReviewRows.findIndex((item) => item.key === row.key);
    const allIndex = allMatrixReviewRows.findIndex((item) => item.key === row.key);
    const queueIndex = filteredIndex >= 0 ? filteredIndex : allIndex;
    if (queueIndex >= 0) {
      if (filteredIndex < 0) {
        setMatrixReviewFilter("all");
      }
      setReviewQueuePage(Math.floor(queueIndex / reviewQueuePageSize) + 1);
    }
    if (locateReviewTimerRef.current !== null) {
      window.clearTimeout(locateReviewTimerRef.current);
    }
    locateReviewTimerRef.current = window.setTimeout(() => {
      setLocatingReviewItemId("");
      locateReviewTimerRef.current = null;
    }, 1800);
    window.setTimeout(() => {
      const highlight = effectiveReviewHighlights.find((item) => item.item_id === row.key);
      const target =
        document.getElementById(`review-highlight-${row.key}`) ||
        (highlight ? document.getElementById(`review-block-${highlight.chunk_id}`) : null) ||
        (row.raw.source_chunk_id ? document.getElementById(`review-block-${row.raw.source_chunk_id}`) : null);
      if (target && reviewSourcePaneRef.current) {
        scrollElementIntoContainer(target, reviewSourcePaneRef.current);
      } else {
        target?.scrollIntoView({ block: "center", behavior: "smooth" });
      }
      const itemTarget = document.querySelector(`[data-review-item-id="${row.key}"]`);
      if (itemTarget instanceof HTMLElement && reviewItemPaneRef.current) {
        scrollElementIntoContainer(itemTarget, reviewItemPaneRef.current);
      } else {
        itemTarget?.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }, 160);
  }, [allMatrixReviewRows, effectiveReviewHighlights, matrixReviewRows, reviewQueuePageSize]);

  const focusReviewChunk = useCallback(
    (chunkId: string) => {
      const row = allMatrixReviewRows.find((item) => item.raw.source_chunk_id === chunkId);
      if (row) {
        focusReviewRow(row);
      }
    },
    [allMatrixReviewRows, focusReviewRow]
  );

  useEffect(() => {
    if (activeTab !== "review" || !activeReviewItemId) return;
    const itemTarget = document.querySelector(`[data-review-item-id="${activeReviewItemId}"]`);
    if (itemTarget instanceof HTMLElement && reviewItemPaneRef.current) {
      scrollElementIntoContainer(itemTarget, reviewItemPaneRef.current);
    }
  }, [activeReviewItemId, activeTab, pagedMatrixReviewRows]);

  const openSourceCreateDraft = useCallback((chunk: ReviewChunk, selectedText?: string) => {
    const text = (selectedText || chunk.content_text).trim();
    if (!text) {
      Modal.warning({ title: "没有可新增的原文内容" });
      return;
    }
    const startOffset = chunk.content_text.indexOf(text);
    setSourceSelectionDraft({
      chunk,
      selectedText: text,
      selectionStartOffset: startOffset >= 0 ? startOffset : null,
      selectionEndOffset: startOffset >= 0 ? startOffset + text.length : null,
      itemType: "mandatory_response",
      riskLevel: "medium",
      isMandatory: true,
      responseSuggestion: "请人工确认响应方式并补充证据。",
      reason: "人工从原文新增合规矩阵项"
    });
  }, []);

  const handleReviewChunkMouseUp = useCallback(
    (event: ReactMouseEvent<HTMLElement>, chunk: ReviewChunk) => {
      if (!sourceCreateMode) return;
      event.stopPropagation();
      const selectedText = window.getSelection()?.toString().trim() ?? "";
      if (selectedText.length < 2) return;
      openSourceCreateDraft(chunk, selectedText);
      setSourceCreateMode(false);
      window.getSelection()?.removeAllRanges();
    },
    [openSourceCreateDraft, sourceCreateMode]
  );

  const activateReviewHighlight = useCallback((highlight: MatrixReviewHighlight) => {
    const row = matrixRows.find((item) => item.key === highlight.item_id);
    if (row) {
      focusReviewRow(row);
      return;
    }
    setActiveReviewItemId(highlight.item_id);
  }, [focusReviewRow, matrixRows]);

  const renderHighlightedText = useCallback(
    (text: string, highlights: MatrixReviewHighlight[], baseKey: string, baseOffset = 0) => {
      if (!highlights.length) return text;
      const boundaries = new Set([0, text.length]);
      highlights.forEach((highlight) => {
        const start = Math.max(0, highlight.start_offset - baseOffset);
        const end = Math.min(text.length, highlight.end_offset - baseOffset);
        if (start < end) {
          boundaries.add(start);
          boundaries.add(end);
        }
      });
      const sorted = Array.from(boundaries).sort((left, right) => left - right);
      return sorted.slice(0, -1).map((start, index) => {
        const end = sorted[index + 1];
        const segment = text.slice(start, end);
        const absoluteStart = baseOffset + start;
        const absoluteEnd = baseOffset + end;
        const highlight = highlights.find(
          (item) => item.start_offset < absoluteEnd && item.end_offset > absoluteStart
        );
        if (!highlight) {
          return <span key={`${baseKey}-plain-${index}`}>{segment}</span>;
        }
        const isActive = highlight.item_id === activeReviewItemId;
        const isLocating = highlight.item_id === locatingReviewItemId;
        const isAnchor = absoluteStart === highlight.start_offset;
        return (
          <span
            key={`${baseKey}-highlight-${highlight.item_id}-${index}`}
            id={isAnchor ? `review-highlight-${highlight.item_id}` : undefined}
            className={`review-text-highlight review-highlight-${highlight.risk_level} ${
              highlight.match_source === "chunk_fallback" ? "fallback" : ""
            } ${isActive ? "active" : ""} ${isLocating ? "locating" : ""}`}
            title={highlight.match_source === "chunk_fallback" ? "定位到段落，未定位到精确文字" : "点击查看条目详情"}
            onClick={(event) => {
              event.stopPropagation();
              activateReviewHighlight(highlight);
            }}
          >
            {segment}
          </span>
        );
      });
    },
    [activateReviewHighlight, activeReviewItemId, locatingReviewItemId]
  );

  const renderReviewParagraph = useCallback(
    (paragraph: ReviewDocumentParagraph, highlights: MatrixReviewHighlight[], keyPrefix: string) => {
      let offset = 0;
      return paragraph.runs.length ? (
        <>
          {paragraph.runs.map((run, index) => {
            const start = offset;
            offset += run.text.length;
            return (
              <span key={`${keyPrefix}-run-${index}`} style={runCss(run)}>
                {renderHighlightedText(run.text, highlights, `${keyPrefix}-run-${index}`, start)}
              </span>
            );
          })}
        </>
      ) : (
        <>{renderHighlightedText(paragraph.text, highlights, keyPrefix)}</>
      );
    },
    [renderHighlightedText]
  );

  const blockToReviewChunk = useCallback(
    (block: ReviewDocumentBlock): ReviewChunk | null => {
      if (!block.chunk_id) return null;
      return (
        reviewChunkById.get(block.chunk_id) ?? {
          id: block.chunk_id,
          chunk_index: block.chunk_index ?? 0,
          page_no: null,
          heading_path: null,
          content_text: block.text,
          document_version_id: reviewOpenXmlDocument?.version_id ?? ""
        }
      );
    },
    [reviewChunkById, reviewOpenXmlDocument?.version_id]
  );

  const handleReviewBlockMouseUp = useCallback(
    (event: ReactMouseEvent<HTMLElement>, block: ReviewDocumentBlock) => {
      const chunk = blockToReviewChunk(block);
      if (!chunk) return;
      handleReviewChunkMouseUp(event, chunk);
    },
    [blockToReviewChunk, handleReviewChunkMouseUp]
  );

  const handleCreateSourceItem = async () => {
    if (!selectedProjectId || !selectedSectionId || !sourceSelectionDraft) return;
    if (!sourceSelectionDraft.selectedText.trim() || !sourceSelectionDraft.reason.trim()) {
      Modal.warning({ title: "请补充选中文本和新增原因" });
      return;
    }
    setSavingSourceItem(true);
    try {
      const result = await createComplianceItemFromSource(selectedProjectId, selectedSectionId, {
        source_chunk_id: sourceSelectionDraft.chunk.id,
        selected_text: sourceSelectionDraft.selectedText.trim(),
        selection_start_offset: sourceSelectionDraft.selectionStartOffset,
        selection_end_offset: sourceSelectionDraft.selectionEndOffset,
        item_type: sourceSelectionDraft.itemType,
        risk_level: sourceSelectionDraft.riskLevel,
        is_mandatory: sourceSelectionDraft.isMandatory,
        response_suggestion: sourceSelectionDraft.responseSuggestion || null,
        reason: sourceSelectionDraft.reason.trim()
      });
      appendLog(`从原文新增矩阵项：${truncateText(result.item.requirement_text, 18)}`);
      setSourceSelectionDraft(null);
      await refreshAfterMatrixMutation();
      if (result.similar_candidates.length > 0) {
        setSimilarBaseRow(mapMatrixRow(result.item));
        setSimilarCandidates(result.similar_candidates);
        setSimilarActions(
          Object.fromEntries(result.similar_candidates.map((candidate) => [candidate.candidate_key, "skip" as SimilarAction]))
        );
        setSimilarDrawerOpen(true);
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "从原文新增矩阵项失败");
    } finally {
      setSavingSourceItem(false);
    }
  };

  const openSimilarCandidates = async (row: MatrixRow) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setSimilarBaseRow(row);
    setSimilarCandidates([]);
    setSimilarActions({});
    setSimilarDrawerOpen(true);
    setLoadingSimilarCandidates(true);
    try {
      const candidates = await listSimilarCandidates(selectedProjectId, selectedSectionId, row.key);
      setSimilarCandidates(candidates);
      setSimilarActions(Object.fromEntries(candidates.map((candidate) => [candidate.candidate_key, "skip" as SimilarAction])));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "相似片段检索失败");
    } finally {
      setLoadingSimilarCandidates(false);
    }
  };

  const handleApplySimilarCandidates = async () => {
    if (!selectedProjectId || !selectedSectionId || !similarBaseRow) return;
    const selectedCandidates = similarCandidates
      .filter((candidate) => (similarActions[candidate.candidate_key] ?? "skip") !== "skip")
      .map((candidate) => ({
        candidate_key: candidate.candidate_key,
        source_chunk_id: candidate.source_chunk_id,
        selected_text: candidate.selected_text,
        selection_start_offset: candidate.selection_start_offset,
        selection_end_offset: candidate.selection_end_offset,
        action: similarActions[candidate.candidate_key] ?? "skip"
      }));
    if (selectedCandidates.length === 0) {
      setSimilarDrawerOpen(false);
      return;
    }
    setLoadingSimilarCandidates(true);
    try {
      const result = await applySimilarCandidates(selectedProjectId, selectedSectionId, similarBaseRow.key, {
        candidates: selectedCandidates,
        reason: "人工确认相似片段补票"
      });
      appendLog(`相似补票完成，影响 ${result.affected_item_count} 条矩阵项`);
      setSimilarDrawerOpen(false);
      await refreshAfterMatrixMutation();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "相似补票失败");
    } finally {
      setLoadingSimilarCandidates(false);
    }
  };

  const handleConfirmDuplicateGroup = async (row: MatrixRow) => {
    if (!selectedProjectId || !selectedSectionId) return;
    let reason = "人工确认这些条目为同一合规要求，启用状态级联";
    Modal.confirm({
      title: "确认重复关联组",
      content: (
        <Space direction="vertical" size={10} style={{ width: "100%" }}>
          <Text>{truncateText(row.requirement, 64)}</Text>
          <Text type="secondary">确认后，同组条目的确认状态可级联同步；风险等级、类型和强制属性不会自动改变。</Text>
          <TextArea defaultValue={reason} autoSize={{ minRows: 2, maxRows: 4 }} onChange={(event) => { reason = event.target.value; }} />
        </Space>
      ),
      okText: "确认关联",
      cancelText: "取消",
      onOk: async () => {
        if (!reason.trim()) throw new Error("reason required");
        const result = await confirmDuplicateGroup(selectedProjectId, selectedSectionId, row.key, { reason: reason.trim() });
        appendLog(`确认重复关联组：${result.affected_item_count} 条`);
        await refreshAfterMatrixMutation();
      }
    });
  };

  const handleUnlinkDuplicateGroup = async (row: MatrixRow) => {
    if (!selectedProjectId || !selectedSectionId) return;
    await unlinkDuplicateGroupItem(selectedProjectId, selectedSectionId, row.key, {
      reason: "人工判断该条与关联组存在差异，解除联动"
    });
    appendLog(`解除联动：${truncateText(row.requirement, 18)}`);
    await refreshAfterMatrixMutation();
  };

  const handleSplitDuplicateGroup = async (row: MatrixRow) => {
    if (!selectedProjectId || !selectedSectionId) return;
    await splitDuplicateGroupItem(selectedProjectId, selectedSectionId, row.key, {
      reason: "人工拆分为独立关联组"
    });
    appendLog(`拆分关联组：${truncateText(row.requirement, 18)}`);
    await refreshAfterMatrixMutation();
  };

  const renderDiffSegments = (segments: TextDiffSegment[]) => {
    if (!segments.length) return null;
    return (
      <span className="diff-inline">
        {segments.map((segment, index) => {
          if (segment.operation === "equal") {
            return <span key={index}>{segment.candidate_text ?? segment.base_text}</span>;
          }
          if (segment.operation === "insert") {
            return <ins key={index}>{segment.candidate_text}</ins>;
          }
          if (segment.operation === "delete") {
            return <del key={index}>{segment.base_text}</del>;
          }
          return (
            <span key={index}>
              <del>{segment.base_text}</del>
              <ins>{segment.candidate_text}</ins>
            </span>
          );
        })}
      </span>
    );
  };

  const confirmDraftGeneration = () => {
    Modal.confirm({
      title: "生成章节草稿",
      content: "草稿将基于当前合规矩阵和已绑定证据生成，生成结果需要人工复核后才能进入正式标书版本。",
      okText: "生成草稿",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId) return;
        setLoadingBusinessDraft(true);
        try {
          const chapters = await generateBusinessDraftChapters(selectedProjectId, selectedSectionId);
          setBusinessDraftChapters(chapters);
          setSelectedDraftChapterId(chapters[0]?.id ?? "");
          setViewMode("workspace");
          setActiveTab("chapter");
          setWorkspaceNode("chapter");
          appendLog(`生成商务标章节草稿：${chapters.length} 个章节`);
          await Promise.all([reloadApprovalTasks(), reloadAuditLogs()]);
        } catch (error) {
          setApiError(error instanceof Error ? error.message : "商务标章节生成失败");
          throw error;
        } finally {
          setLoadingBusinessDraft(false);
        }
      }
    });
  };

  const handlePreviewContextPack = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const preview = await previewBusinessDraftContextPack(selectedProjectId, selectedSectionId, {
        profile_id: "engineering_construction_business_v1"
      });
      const outline = preview.outline_plan_json as { sections?: unknown[] };
      setContextPackPreview(preview);
      setContextPackPreviewOpen(true);
      appendLog(`预览 ContextPack：${outline.sections?.length ?? 0} 个章节计划`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "ContextPack 预览失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const handleCreateContextPack = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (!qualificationDecisionConfirmed) {
      Modal.warning({
        title: "请先确认参标建议",
        content: contextPackQualificationGate.message,
        okText: "去资格预评估",
        onOk: () => activateWorkflowStep("qualification")
      });
      return;
    }
    setLoadingContextPack(true);
    setApiError("");
    try {
      const contextPack = await createBusinessDraftContextPack(selectedProjectId, selectedSectionId, {
        profile_id: "engineering_construction_business_v1"
      });
      setBusinessDraftContextPacks([contextPack]);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      setCoverageReview(null);
      appendLog(`确认 ContextPack：${contextPack.section_context_packs.length} 个章节上下文`);
      await reloadAuditLogs();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "ContextPack 生成失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const openContextPackDraftGenerationConfirm = () => {
    if (!activeContextPack || !selectedProjectId || !selectedSectionId) return;
    const isBlocked = activeContextPack.readiness_status === "block" || qualificationDecisionIsNoGo;
    Modal.confirm({
      title: isBlocked ? "生成内部草稿" : "按 ContextPack 生成草稿",
      content: isBlocked
        ? "当前 ContextPack 或资格结论仍存在阻塞项。本次只生成带待补占位的内部草稿，不代表可提交版本。"
        : "将按已确认的 ContextPack 生成结构化章节和可追溯 block，生成后会执行覆盖检查。",
      okText: isBlocked ? "生成内部草稿" : "生成草稿",
      cancelText: "取消",
      onOk: async () => {
        setLoadingBusinessDraft(true);
        setApiError("");
        try {
          const task = await generateBusinessDraftFromContextPackAsync(
            selectedProjectId,
            selectedSectionId,
            activeContextPack.id,
            { allow_blocked_internal_draft: isBlocked }
          );
          setBusinessDraftGenerationTaskId(task.id);
          setBusinessDraftGenerationTask(task);
          setViewMode("workspace");
          setActiveTab("chapter");
          setWorkspaceNode("chapter");
          appendLog(`商务草稿生成任务已启动：${task.id.slice(0, 8)}`);
        } catch (error) {
          setApiError(error instanceof Error ? error.message : "ContextPack 草稿生成失败");
          setLoadingBusinessDraft(false);
          throw error;
        }
      }
    });
  };

  const confirmContextPackDraftGeneration = () => {
    if (!activeContextPack || !selectedProjectId || !selectedSectionId) return;
    if (!qualificationDecisionConfirmed) {
      Modal.warning({
        title: "请先确认参标建议",
        content: contextPackQualificationGate.message,
        okText: "去资格预评估",
        onOk: () => activateWorkflowStep("qualification")
      });
      return;
    }
    if (qualificationDecisionIsNoGo) {
      confirmNoGoRiskAcceptance(openContextPackDraftGenerationConfirm);
      return;
    }
    openContextPackDraftGenerationConfirm();
  };

  const handleRunContextPackCoverageReview = async () => {
    if (!activeContextPack || !selectedProjectId || !selectedSectionId) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const review = await runBusinessDraftContextPackCoverageReview(
        selectedProjectId,
        selectedSectionId,
        activeContextPack.id
      );
      setCoverageReview(review);
      appendLog(`执行 ContextPack 覆盖检查：${review.status}`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "覆盖检查失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const handleUpdateDraftBlockStatus = async (
    block: DraftBlock,
    reviewStatus: string,
    reason: string,
    contentText?: string
  ) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setSavingBusinessDraft(true);
    setApiError("");
    try {
      const updated = await updateBusinessDraftBlock(selectedProjectId, selectedSectionId, block.id, {
        review_status: reviewStatus,
        content_text: contentText ?? null,
        reason
      });
      setDraftBlocks((blocks) => blocks.map((item) => (item.id === updated.id ? updated : item)));
      if (updated.chapter_id && contentText) {
        await reloadBusinessDraftChapters();
      }
      appendLog(`更新草稿 block 状态：${reviewStatus}`);
      await reloadAuditLogs();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "草稿 block 状态更新失败");
    } finally {
      setSavingBusinessDraft(false);
    }
  };

  const openEditDraftBlock = (block: DraftBlock) => {
    let contentText = block.content_text;
    let reason = "人工修改结构化草稿 block 内容";
    Modal.confirm({
      title: "编辑结构化 block",
      width: 760,
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text type="secondary">保存后该 block 会回到待审阅状态，并重新执行章节事实校验。</Text>
          <TextArea
            defaultValue={block.content_text}
            autoSize={{ minRows: 8, maxRows: 14 }}
            onChange={(event) => {
              contentText = event.target.value;
            }}
          />
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "保存",
      cancelText: "取消",
      onOk: async () => {
        if (!contentText.trim() || !reason.trim()) {
          Modal.warning({ title: "需要填写 block 内容和修改原因" });
          throw new Error("draft block content and reason required");
        }
        await handleUpdateDraftBlockStatus(block, "pending", reason.trim(), contentText.trim());
      }
    });
  };

  const confirmExport = () => {
    Modal.confirm({
      title: "导出矩阵快照",
      content: "将导出当前筛选条件下的合规矩阵快照，用于归档、会议或外部协作。导出文件不作为平台外修改入口，最新状态仍以平台为准。",
      okText: "导出快照",
      cancelText: "取消",
      onOk: handleExportExcel
    });
  };

  const openKeyInfoModal = () => {
    setKeyInfoDraft({
      projectName: currentProject?.name ?? "",
      purchaser: currentProject?.purchaser ?? "",
      agency: currentProject?.agency ?? "",
      budgetAmount: currentProject?.budget_amount ?? "",
      regionCode: currentProject?.region_code ?? "",
      industryCode: currentProject?.industry_code ?? "",
      noticeUrl: "notice_url" in (currentProject ?? {}) ? (currentProject as ProjectDetail).notice_url ?? "" : "",
      bidDeadlineAt: currentProject?.bid_deadline_at ?? null,
      sectionCode: currentSection?.code ?? "",
      sectionName: currentSection?.name ?? "",
      sectionBudgetAmount: currentSection?.budget_amount ?? "",
      sectionBidDeadlineAt: currentSection?.bid_deadline_at ?? null,
      reason: "人工确认项目和标段关键信息"
    });
    setKeyInfoModalOpen(true);
  };

  const handleContextPackCheckAction = (check: Record<string, unknown>) => {
    const target = workflowStepForContextPackCheck(check);
    setContextPackPreviewOpen(false);
    if (target === "project_info") {
      openKeyInfoModal();
      return;
    }
    if (target === "enterprise") {
      setViewMode("enterprise");
      return;
    }
    if (target === "evidence") {
      const sampleItemIds = Array.isArray(check.sample_item_ids)
        ? check.sample_item_ids.map(String)
        : [];
      const targetRow =
        matrixRows.find((row) => sampleItemIds.includes(row.key)) ??
        evidenceRows[0];
      if (targetRow) {
        setViewMode("workspace");
        setActiveTab("evidence");
        setWorkspaceNode("evidence");
        void openEvidenceBindingDrawer(targetRow);
        return;
      }
    }
    activateWorkflowStep(target);
  };

  const handleSaveKeyInfo = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (!keyInfoDraft.projectName.trim() || !keyInfoDraft.sectionName.trim() || !keyInfoDraft.reason.trim()) {
      Modal.warning({ title: "请填写项目名称、标段名称和修改原因" });
      return;
    }
    setSavingProject(true);
    try {
      const [updatedProject, updatedSection] = await Promise.all([
        updateProject(selectedProjectId, {
          name: keyInfoDraft.projectName.trim(),
          purchaser: keyInfoDraft.purchaser.trim() || null,
          agency: keyInfoDraft.agency.trim() || null,
          budget_amount: keyInfoDraft.budgetAmount.trim() || null,
          region_code: keyInfoDraft.regionCode.trim() || null,
          industry_code: keyInfoDraft.industryCode.trim() || null,
          notice_url: keyInfoDraft.noticeUrl.trim() || null,
          bid_deadline_at: keyInfoDraft.bidDeadlineAt,
          reason: keyInfoDraft.reason.trim()
        }),
        updateSection(selectedProjectId, selectedSectionId, {
          code: keyInfoDraft.sectionCode.trim() || null,
          name: keyInfoDraft.sectionName.trim(),
          budget_amount: keyInfoDraft.sectionBudgetAmount.trim() || null,
          bid_deadline_at: keyInfoDraft.sectionBidDeadlineAt,
          reason: keyInfoDraft.reason.trim()
        })
      ]);
      setProjectDetail(updatedProject);
      setProjects((items) => items.map((item) => (item.id === updatedProject.id ? { ...item, ...updatedProject } : item)));
      setSections((items) => items.map((item) => (item.id === updatedSection.id ? updatedSection : item)));
      setKeyInfoModalOpen(false);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog("更新项目和标段关键信息");
      await Promise.all([reloadAuditLogs(), reloadPreflightCheck()]);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "项目关键信息保存失败");
    } finally {
      setSavingProject(false);
    }
  };

  const confirmSubmit = () => {
    let riskAcceptanceReason = "";
    const hasBlocker = preflightCheck?.status === "block";
    Modal.confirm({
      title: hasBlocker ? "存在阻塞项，创建提交确认？" : "提交确认",
      content: hasBlocker ? (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Alert
            type="error"
            showIcon
            message="提交前核验存在阻塞项"
            description={preflightCheck?.summary}
          />
          <Text type="secondary">该说明会写入审批快照和审计，用于标记本次仅进入内部复核。</Text>
          <TextArea
            placeholder="请填写风险接受说明，例如：仅创建内部复核任务，待补齐证据后再正式提交。"
            autoSize={{ minRows: 3, maxRows: 5 }}
            onChange={(event) => {
              riskAcceptanceReason = event.target.value;
            }}
          />
        </Space>
      ) : (
        "该操作将触发审批流，不会直接提交投标文件。高风险缺项和未确认项仍需责任人处理。"
      ),
      okText: "触发审批流",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId) return;
        if (hasBlocker && !riskAcceptanceReason.trim()) {
          Modal.warning({ title: "需要填写风险接受说明" });
          throw new Error("risk acceptance required");
        }
        const task = await createApprovalTask(selectedProjectId, selectedSectionId, {
          task_type: "submit_confirmation",
          title: "提交前人工确认",
          description: "确认参标建议、商务标草稿、证据绑定和导出快照均已完成复核。",
          risk_acceptance_reason: riskAcceptanceReason.trim() || null
        });
        appendLog(`触发提交前审批流：${task.title}`);
        await Promise.all([reloadApprovalTasks(), reloadAuditLogs()]);
      }
    });
  };

  const handleGenerateMatrix = (source?: ProjectDocument | null) => {
    if (!selectedProjectId || !selectedSectionId) return;
    const version = source?.current_version;
    Modal.confirm({
      title: "生成合规矩阵",
      content: version
        ? `将基于 ${source?.title ?? "当前文件"} 的 ${version.version_label} 版本重新抽取矩阵，生成结果需要人工确认。`
        : "将基于当前标段已解析的招标文件抽取资格项、强制响应项和时间节点，生成结果需要人工确认。",
      okText: "生成",
      cancelText: "取消",
      onOk: async () => {
        setLoadingMatrix(true);
        setContextPackPreview(null);
        setContextPackPreviewOpen(false);
        try {
          const task = await generateComplianceMatrix(selectedProjectId, selectedSectionId, {
            document_id: source?.id,
            document_version_id: version?.id,
            force: true,
            async_processing: true
          });
          appendLog(`提交合规矩阵生成任务：${task.id.slice(0, 8)}`);
          if (task.status === "failed") {
            throw new Error(task.error_message || "合规矩阵生成失败");
          }
          if (task.status === "succeeded") {
            const [items] = await Promise.all([
              listComplianceItems(selectedProjectId, selectedSectionId, { limit: COMPLIANCE_ITEM_FETCH_LIMIT }),
              reloadDocumentsAndExports(),
              reloadExtractionQuality(),
              reloadAuditLogs(),
              getPreflightCheck(selectedProjectId, selectedSectionId).then(setPreflightCheck).catch(() => undefined),
              activeTab === "review" ? reloadMatrixReview() : Promise.resolve()
            ]);
            setComplianceItems(items);
            Modal.success({
              title: "合规矩阵已重新生成",
              content: `新增 ${task.output_json?.created_count ?? 0} 条，更新 ${task.output_json?.updated_count ?? 0} 条，淘汰旧项 ${task.output_json?.superseded_count ?? 0} 条。`
            });
            setLoadingMatrix(false);
            return;
          }
          Modal.info({
            title: "矩阵生成任务已提交",
            content: "任务正在后台处理，可在流程状态中查看进度；完成后会自动刷新矩阵。"
          });
          setImportProcessing({
            projectId: selectedProjectId,
            sectionId: selectedSectionId,
            parseTaskId: null,
            matrixTaskId: task.id,
            parseTask: null,
            matrixTask: task
          });
          setLoadingMatrix(false);
        } catch (error) {
          setLoadingMatrix(false);
          setApiError(error instanceof Error ? error.message : "合规矩阵生成失败");
        }
      }
    });
  };

  const handleRunQualificationEvaluation = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setEvaluatingQualification(true);
    try {
      const data = await runQualificationEvaluation(selectedProjectId, selectedSectionId);
      setQualificationEvaluations(data);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog(`运行参标资格预评估：${data.length} 条资格项`);
      await reloadAuditLogs();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "资格预评估失败");
    } finally {
      setEvaluatingQualification(false);
    }
  };

  const handleGenerateQualificationDecision = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setGeneratingDecision(true);
    try {
      const decision = await generateQualificationDecision(selectedProjectId, selectedSectionId);
      setQualificationDecision(decision);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog(`生成参标建议：${decisionLabels[decision.recommendation] ?? decision.recommendation}`);
      await Promise.all([reloadApprovalTasks(), reloadAuditLogs(), reloadQualificationEvaluations()]);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Go/No-Go 参标建议生成失败");
    } finally {
      setGeneratingDecision(false);
    }
  };

  const confirmNoGoRiskAcceptance = (onContinue: () => void) => {
    if (!qualificationDecision) return;
    let reason = "";
    Modal.confirm({
      title: "参标建议为 No-Go，仍继续？",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Alert
            type="error"
            showIcon
            message="当前建议不参标"
            description={qualificationDecision.summary || "资格预评估存在阻断或缺失项。"}
          />
          <Text type="secondary">继续生成商务草稿前，需要记录风险接受说明；该说明会写入本地操作日志。</Text>
          <TextArea
            placeholder="请填写继续原因，例如：仅生成内部评审草稿，待补齐材料后再决策是否正式参标。"
            autoSize={{ minRows: 3, maxRows: 5 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "风险接受并继续",
      cancelText: "返回处理资格项",
      onOk: () => {
        if (!reason.trim()) {
          Modal.warning({ title: "需要填写风险接受说明" });
          return Promise.reject();
        }
        appendLog(`No-Go 风险接受：${truncateText(reason.trim(), 36)}`);
        onContinue();
        return undefined;
      }
    });
  };

  const runWorkflowPrimaryAction = (stepKey: WorkflowStepKey) => {
    const targetStep = workflowSteps.find((step) => step.key === stepKey);
    if (targetStep?.disabled) {
      appendLog(targetStep.disabledReason ?? "请先完成前置步骤");
      return;
    }
    if (stepKey === "documents") {
      activateWorkflowStep("documents");
      return;
    }
    if (stepKey === "tasks") {
      activateWorkflowStep("tasks");
      return;
    }
    if (stepKey === "quality") {
      activateWorkflowStep("quality");
      return;
    }
    if (stepKey === "matrix") {
      if (extractionBlocked && !knownMatrixCount) {
        activateWorkflowStep("quality");
      } else if (matrixTaskActive && !knownMatrixCount) {
        activateWorkflowStep("matrix");
      } else if (preflightCheck?.matrix_outdated) {
        handleGenerateMatrix();
      } else if (knownMatrixCount) {
        activateWorkflowStep("matrix");
      } else {
        handleGenerateMatrix();
      }
      return;
    }
    if (stepKey === "review") {
      activateWorkflowStep("review");
      return;
    }
    if (stepKey === "evidence") {
      activateWorkflowStep("evidence");
      return;
    }
    if (stepKey === "technical") {
      activateWorkflowStep("technical");
      return;
    }
    if (stepKey === "qualification") {
      if (qualificationDecision) {
        if (qualificationDecisionNeedsConfirmation) {
          handleConfirmQualificationDecision();
        } else {
          activateWorkflowStep("qualification");
        }
      } else if (qualificationEvaluations.length) {
        void handleGenerateQualificationDecision();
      } else {
        void handleRunQualificationEvaluation().then(() => handleGenerateQualificationDecision());
      }
      return;
    }
    if (stepKey === "chapter") {
      if (!mvp13DraftWorkflowAvailable) {
        activateWorkflowStep("chapter");
      } else if (businessDraftChapters.length) {
        activateWorkflowStep("chapter");
      } else if (qualificationDecisionConfirmed && qualificationDecisionIsNoGo) {
        confirmNoGoRiskAcceptance(confirmDraftGeneration);
      } else {
        confirmDraftGeneration();
      }
      return;
    }
    if (stepKey === "approval") {
      if (!mvp13DraftWorkflowAvailable) {
        appendLog("草稿生成、事实校验和导出将在 MVP1.3 开放");
      } else if (approvalTasks.some((task) => task.status === "pending")) {
        activateWorkflowStep("approval");
      } else {
        confirmSubmit();
      }
    }
  };

  const handlePreflightCheckAction = (item: PreflightCheck["checks"][number]) => {
    const target = workflowStepForPreflightCheck(item);
    if (!target) {
      appendLog("该待办暂未绑定处理页面");
      return;
    }
    if (item.code === "matrix_version" || item.code === "draft_exists") {
      runWorkflowPrimaryAction(target);
      return;
    }
    activateWorkflowStep(target);
  };

  const handleConfirmQualificationDecision = () => {
    if (!selectedProjectId || !selectedSectionId || !qualificationDecision) return;
    let reason = "人工确认 Go/No-Go 参标建议";
    Modal.confirm({
      title: "确认参标建议",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{qualificationDecision.summary}</Text>
          <Text type="secondary">确认后会作为商务标草稿和提交审批的前置人工关口。</Text>
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "确认建议",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !qualificationDecision || !reason.trim()) {
          Modal.warning({ title: "需要填写确认说明" });
          throw new Error("reason required");
        }
        const decision = await confirmQualificationDecision(
          selectedProjectId,
          selectedSectionId,
          qualificationDecision.id,
          { reason: reason.trim() }
        );
        setQualificationDecision(decision);
        setContextPackPreview(null);
        setContextPackPreviewOpen(false);
        appendLog("确认 Go/No-Go 参标建议");
        await Promise.all([reloadApprovalTasks(), reloadAuditLogs()]);
      }
    });
  };

  const handleConfirmQualificationEvaluation = (evaluation: QualificationEvaluation) => {
    let reason = "人工确认资格预评估结果";
    Modal.confirm({
      title: "确认评估结果",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{truncateText(evaluation.requirement_text, 64)}</Text>
          <Text type="secondary">确认动作会写入审计日志，后续 Go/No-Go 建议会优先读取人工确认状态。</Text>
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "确认",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !reason.trim()) {
          Modal.warning({ title: "需要填写确认说明" });
          throw new Error("reason required");
        }
        const updated = await confirmQualificationEvaluation(
          selectedProjectId,
          selectedSectionId,
          evaluation.id,
          { reason: reason.trim() }
        );
        setQualificationEvaluations((items) =>
          items.map((item) => (item.id === updated.id ? updated : item))
        );
        appendLog(`确认资格预评估：${qualificationStatusLabels[updated.evaluation_status] ?? updated.evaluation_status}`);
        await reloadAuditLogs();
      }
    });
  };

  const handleSaveBusinessDraftChapter = () => {
    if (!selectedProjectId || !selectedSectionId || !selectedDraftChapter) return;
    let reason = "人工编辑商务标章节草稿";
    Modal.confirm({
      title: "保存章节修改",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>保存后会重新执行事实性校验，并写入审计日志。</Text>
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "保存并校验",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !selectedDraftChapter || !reason.trim()) {
          Modal.warning({ title: "需要填写修改原因" });
          throw new Error("reason required");
        }
        setSavingBusinessDraft(true);
        try {
          const updated = await updateBusinessDraftChapter(
            selectedProjectId,
            selectedSectionId,
            selectedDraftChapter.id,
            { content_text: draftEditorValue, reason: reason.trim() }
          );
          setBusinessDraftChapters((chapters) =>
            chapters.map((chapter) => (chapter.id === updated.id ? updated : chapter))
          );
          setDraftEditorValue(updated.content_text);
          appendLog(`保存商务标章节：${updated.title}`);
          await Promise.all([reloadAuditLogs(), reloadApprovalTasks()]);
        } catch (error) {
          setApiError(error instanceof Error ? error.message : "商务标章节保存失败");
          throw error;
        } finally {
          setSavingBusinessDraft(false);
        }
      }
    });
  };

  const handleRunDraftFactCheck = async () => {
    if (!selectedProjectId || !selectedSectionId || !selectedDraftChapter) return;
    setSavingBusinessDraft(true);
    try {
      const updated = await runBusinessDraftFactChecks(selectedProjectId, selectedSectionId, selectedDraftChapter.id);
      setBusinessDraftChapters((chapters) =>
        chapters.map((chapter) => (chapter.id === updated.id ? updated : chapter))
      );
      setDraftEditorValue(updated.content_text);
      appendLog(`执行事实性校验：${updated.title}`);
      await reloadAuditLogs();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "事实性校验失败");
    } finally {
      setSavingBusinessDraft(false);
    }
  };

  const handleExportBusinessWord = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const hasUnapprovedDraftBlocks = draftBlocks.length > 0 && unapprovedDraftBlockCount > 0;
    if (
      hasUnapprovedDraftBlocks ||
      (preflightCheck && (preflightCheck.unverified_fact_count > 0 || preflightCheck.status === "block"))
    ) {
      let riskAcceptanceReason = "";
      Modal.confirm({
        title: hasUnapprovedDraftBlocks ? "结构化草稿尚未全部通过" : "提交前核验仍有风险",
        content: (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Alert
              type={hasUnapprovedDraftBlocks || preflightCheck?.status === "block" ? "error" : "warning"}
              showIcon
              message="导出将被标记为内部草稿"
              description={
                hasUnapprovedDraftBlocks
                  ? `还有 ${unapprovedDraftBlockCount} 个结构化 block 未人工通过。导出的 Word 只能作为内部草稿。`
                  : `${preflightCheck?.summary ?? "提交前核验仍有风险。"} 导出的 Word 需人工复核后使用。`
              }
            />
            <TextArea
              placeholder="请填写风险接受说明，例如：导出内部草稿用于会议评审，待补齐证据后再形成正式版本。"
              autoSize={{ minRows: 3, maxRows: 5 }}
              onChange={(event) => {
                riskAcceptanceReason = event.target.value;
              }}
            />
          </Space>
        ),
        okText: "继续导出草稿",
        cancelText: "先处理风险",
        onOk: () => {
          if ((hasUnapprovedDraftBlocks || preflightCheck?.status === "block") && !riskAcceptanceReason.trim()) {
            Modal.warning({ title: "需要填写风险接受说明" });
            throw new Error("risk acceptance required");
          }
          void handleExportBusinessWordConfirmed(riskAcceptanceReason.trim() || undefined);
        }
      });
      return;
    }
    await handleExportBusinessWordConfirmed();
  };

  const handleExportBusinessWordConfirmed = async (riskAcceptanceReason?: string) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setExportingWord(true);
    try {
      const exportFile = await exportBusinessDraftWord(selectedProjectId, selectedSectionId, {
        risk_acceptance_reason: riskAcceptanceReason ?? null
      });
      appendLog(`导出商务标 Word：${exportFile.file_name}`);
      await Promise.all([reloadDocumentsAndExports(), reloadAuditLogs(), reloadPreflightCheck()]);
      window.open(`/api/v1/projects/${selectedProjectId}/export-files/${exportFile.id}/download`, "_blank");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "商务标 Word 导出失败");
    } finally {
      setExportingWord(false);
    }
  };

  const handleDecideApprovalTask = (task: ApprovalTask, action: "approve" | "reject") => {
    if (!selectedProjectId || !selectedSectionId) return;
    let reason = action === "approve" ? "人工复核通过" : "退回补充修改";
    const blockers = blockingSummary(task.evidence_snapshot_json);
    Modal.confirm({
      title: action === "approve" && blockers.some((item) => item.status === "block") ? "存在阻塞项，确认通过？" : action === "approve" ? "通过审批任务" : "退回审批任务",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{task.title}</Text>
          {blockers.length > 0 && (
            <Alert
              type={blockers.some((item) => item.status === "block") ? "error" : "warning"}
              showIcon
              message="审批阻塞摘要"
              description={blockers.slice(0, 4).map((item) => String(item.message)).join("；")}
            />
          )}
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: action === "approve" ? "通过" : "退回",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !reason.trim()) {
          Modal.warning({ title: "需要填写处理意见" });
          throw new Error("reason required");
        }
        setApprovalBusyId(task.id);
        try {
          await decideApprovalTask(selectedProjectId, selectedSectionId, task.id, {
            action,
            reason: reason.trim()
          });
          appendLog(`${action === "approve" ? "通过" : "退回"}审批任务：${task.title}`);
          await Promise.all([
            reloadApprovalTasks(),
            reloadBusinessDraftChapters(),
            reloadQualificationDecision(),
            reloadAuditLogs(),
            reloadPreflightCheck()
          ]);
        } catch (error) {
          setApiError(error instanceof Error ? error.message : "审批任务处理失败");
          throw error;
        } finally {
          setApprovalBusyId("");
        }
      }
    });
  };

  const handleQuickPrompt = (prompt: string) => {
    if (prompt === "查看技术响应") {
      activateWorkflowStep("technical");
      appendLog("查看技术响应预览；产品选型、图纸和技术标章节将在 MVP1.1 处理");
      return;
    }
    if (prompt === "检查缺项") {
      appendLog("执行只读缺项检查，未修改业务数据");
      locateMatrixRow(matrixRows.find((row) => row.riskCode === "high")?.key ?? matrixRows[0]?.key);
      return;
    }
    if (prompt === "整理审批意见") {
      activateWorkflowStep("approval");
      appendLog("打开审批任务列表，供人工整理确认意见");
      return;
    }
    appendLog(`流程助手记录只读请求：${prompt}；真实上下文问答将在 MVP1.1 接入`);
  };

  const handleAssistantMessageAction = (item: (typeof assistantMessages)[number]) => {
    if (item.targetRowKey) {
      locateMatrixRow(item.targetRowKey);
      return;
    }
    if (isMatrixComplete && recommendedStep) {
      runWorkflowPrimaryAction(recommendedStep.key);
      return;
    }
    confirmDraftGeneration();
  };

  const buildCurrentConfirmationQueue = (rows: MatrixRow[]) => {
    if (activeTab === "review") {
      return buildMatrixReviewRows(rows, matrixReviewFilter);
    }
    return buildMatrixTableRows(rows, {
      status: statusFilter,
      owner: ownerFilter,
      risk: riskFilter,
      mandatory: mandatoryFilter,
      prioritySortEnabled
    });
  };

  const focusAutoConfirmationRow = (nextRow: MatrixRow) => {
    if (activeTab === "review") {
      focusReviewRow(nextRow);
      return;
    }
    setHighlightedRowKey(nextRow.key);
    window.setTimeout(() => {
      document.querySelector(`[data-row-key="${nextRow.key}"]`)?.scrollIntoView({
        block: "center",
        behavior: "smooth"
      });
    }, 80);
    window.setTimeout(() => setHighlightedRowKey(""), 2800);
  };

  const handleConfirmItem = (row: MatrixRow) => {
    let reason = "人工逐条确认合规矩阵项";
    let sourceVerified = false;
    const needsSourceVerified = row.riskCode === "high" || row.mandatory || row.raw.item_type === "qualification";
    let confirmModal: ReturnType<typeof Modal.confirm>;
    confirmModal = Modal.confirm({
      title: "确认合规矩阵项",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{truncateText(row.requirement, 52)}</Text>
          <Text type="secondary">
            确认后会记录确认人、确认时间和审计日志；若该条已进入人工确认关联组，将同步确认同组条目。
            确认成功后会自动进入当前队列的下一条未确认项，取消可停止连续审阅。
          </Text>
          {needsSourceVerified && (
            <Checkbox onChange={(event) => { sourceVerified = event.target.checked; }}>
              我已核对招标文件原文和来源片段，确认该高风险/强制/资格项无误
            </Checkbox>
          )}
          <Text strong>确认说明（必填）</Text>
          <TextArea
            aria-label="确认说明"
            defaultValue={reason}
            placeholder="请填写本次确认依据，例如：已人工复核招标要求和响应证据，确认可响应。"
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "确认",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId) {
          Modal.warning({ title: "请先选择项目和标段" });
          throw new Error("project or section required");
        }
        if (!reason.trim()) {
          Modal.warning({
            title: "需要填写确认说明",
            content: "请在弹窗中的“确认说明（必填）”输入框填写本次确认依据。"
          });
          throw new Error("reason required");
        }
        if (needsSourceVerified && !sourceVerified) {
          Modal.warning({
            title: "需要核对原文",
            content: "高风险、强制项或资格项必须勾选“已核对原文”后才能确认。"
          });
          throw new Error("source verification required");
        }
        const confirmed = await confirmComplianceItem(selectedProjectId, selectedSectionId, row.key, {
          reason: reason.trim(),
          source_verified: sourceVerified,
          cascade: true
        });
        appendLog(`确认矩阵项：${truncateText(row.requirement, 18)}`);
        if (confirmed.cascade_affected_count > 0) {
          appendLog(`同步确认关联条目 ${confirmed.cascade_affected_count} 项`);
        }
        const review = activeTab === "review" ? await reloadMatrixReview() : undefined;
        const refreshedItems = review?.items ?? await reloadMatrix();
        void refreshMatrixRelatedPanels().catch((error) => {
          appendLog(error instanceof Error ? "后台刷新工作台摘要失败，矩阵确认结果已保存" : "后台刷新工作台摘要失败");
        });
        const refreshedRows = refreshedItems.map(mapMatrixRow);
        const nextRow = findNextUnresolvedMatrixRow(buildCurrentConfirmationQueue(refreshedRows), row.key);
        confirmModal.destroy();
        if (nextRow) {
          focusAutoConfirmationRow(nextRow);
          appendLog(`进入下一条待确认项：${truncateText(nextRow.requirement, 18)}`);
          window.setTimeout(() => handleConfirmItem(nextRow), 180);
          return;
        }
        if (refreshedRows.length > 0 && refreshedRows.every(isMatrixItemResolved)) {
          Modal.success({
            title: "合规矩阵已完成",
            content: "所有矩阵项已经完成确认。下一步建议处理证据绑定，再运行资格预评估。"
          });
          return;
        }
        if (confirmed.cascade_affected_count > 0) {
          Modal.success({
            title: "已同步确认关联条目",
            content: `已同步确认全文其他 ${confirmed.cascade_affected_count} 处相同要求。当前队列暂无下一条待确认项。`
          });
          return;
        }
        appendLog("当前队列暂无下一条待确认矩阵项");
      }
    });
  };

  const handleAssignItem = (row: MatrixRow) => {
    let reason = "指派给当前用户处理";
    Modal.confirm({
      title: "指派责任人",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{truncateText(row.requirement, 52)}</Text>
          <Text type="secondary">当前版本先支持快速指派给当前登录用户。</Text>
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "指派给我",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !reason.trim()) {
          Modal.warning({ title: "需要填写指派说明" });
          throw new Error("reason required");
        }
        await assignComplianceItem(selectedProjectId, selectedSectionId, row.key, { reason: reason.trim() });
        appendLog(`指派矩阵项：${truncateText(row.requirement, 18)}`);
        await refreshAfterMatrixMutation();
      }
    });
  };

  const openEditDraft = (row: MatrixRow) => {
    setEditDraft({
      row,
      status: row.statusCode === "confirmed" ? "pending_confirm" : row.statusCode,
      riskLevel: row.riskCode,
      isMandatory: row.mandatory,
      responseSuggestion: row.raw.response_suggestion ?? "",
      reason: ""
    });
  };

  const handleSaveEditDraft = async () => {
    if (!selectedProjectId || !selectedSectionId || !editDraft) return;
    if (!editDraft.reason.trim()) {
      Modal.warning({ title: "需要填写修改原因" });
      return;
    }
    setSavingMatrixAction(true);
    try {
      await updateComplianceItem(selectedProjectId, selectedSectionId, editDraft.row.key, {
        status: editDraft.status,
        risk_level: editDraft.riskLevel,
        is_mandatory: editDraft.isMandatory,
        response_suggestion: editDraft.responseSuggestion || null,
        reason: editDraft.reason.trim()
      });
      appendLog(`修改矩阵项：${truncateText(editDraft.row.requirement, 18)}`);
      setEditDraft(null);
      await refreshAfterMatrixMutation();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "矩阵项修改失败");
    } finally {
      setSavingMatrixAction(false);
    }
  };

  const openWorkspace = (tab = "matrix") => {
    setViewMode("workspace");
    setActiveTab(tab);
    const workspaceTabs = new Set(["approval", "chapter", "evidence", "review", "documents", "tasks", "quality", "qualification"]);
    setWorkspaceNode(workspaceTabs.has(tab) ? tab : "matrix");
  };

  const openProjectWorkspace = (projectId: string, tab = "matrix") => {
    const sameProject = projectId === selectedProjectId;
    const sectionId = sameProject ? selectedSectionId ?? sections[0]?.id : undefined;
    setSelectedProjectId(projectId);
    setSelectedSectionId(sectionId);
    setViewMode("workspace");
    setActiveTab(tab);
    setSelectedTreeKey(sectionId ? `section:${sectionId}:${tab}` : "");
  };

  const resetNewProjectDraft = () => {
    setNewProjectDraft({
      name: "",
      purchaser: "",
      agency: "",
      budgetAmount: "",
      regionCode: "CN-4306",
      industryCode: "municipal-gas",
      noticeUrl: "",
      bidDeadlineAt: null,
      sectionName: "一标段"
    });
    setProjectImportDraft(null);
    setImportUrl("");
    setImportUrlSite("");
  };

  const openCreateProjectModal = (mode: ProjectCreateMode = "manual") => {
    resetNewProjectDraft();
    setProjectCreateMode(mode);
    setNewProjectOpen(true);
  };

  const applyImportDraft = (draft: ProjectImportDraft) => {
    setProjectImportDraft(draft);
    setNewProjectDraft({
      name: draft.project.name,
      purchaser: draft.project.purchaser ?? "",
      agency: draft.project.agency ?? "",
      budgetAmount: draft.project.budget_amount ?? "",
      regionCode: draft.project.region_code ?? "CN-4306",
      industryCode: draft.project.industry_code ?? "municipal-gas",
      noticeUrl: draft.project.notice_url ?? draft.source.source_url ?? "",
      bidDeadlineAt: draft.project.bid_deadline_at,
      sectionName: draft.sections[0]?.name ?? `一标段：${draft.project.name}`
    });
  };

  const activateProjectWorkspace = async (projectId: string, preferredSectionId?: string) => {
    const projectList = await listProjects();
    setProjects(projectList);
    const sectionData = await listSections(projectId);
    setSections(sectionData);
    const sectionId = preferredSectionId ?? sectionData[0]?.id;
    setSelectedProjectId(projectId);
    setSelectedSectionId(sectionId);
    setViewMode("workspace");
    setActiveTab("documents");
    if (sectionId) setSelectedTreeKey(`section:${sectionId}:documents`);
  };

  const handleImportDraftFile: UploadProps["beforeUpload"] = (file) => {
    setImportingProjectDraft(true);
    createProjectImportDraftFromFile(file)
      .then((draft) => {
        applyImportDraft(draft);
        appendLog(`从文件识别项目信息：${draft.source.original_filename}`);
      })
      .catch((error: unknown) => {
        setApiError(error instanceof Error ? error.message : "文件导入识别失败");
      })
      .finally(() => setImportingProjectDraft(false));
    return false;
  };

  const handleImportDraftUrl = async () => {
    if (!importUrl.trim()) {
      Modal.warning({ title: "请填写公告网页或附件 URL" });
      return;
    }
    setImportingProjectDraft(true);
    try {
      const draft = await createProjectImportDraftFromUrl({
        source_url: importUrl.trim(),
        source_site: importUrlSite || null,
        title: "公告导入项目"
      });
      applyImportDraft(draft);
      appendLog("从网页或公告链接识别项目信息");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "网页导入识别失败");
    } finally {
      setImportingProjectDraft(false);
    }
  };

  const handleBatchConfirm = () => {
    const selectedRows = matrixRows.filter((row) => selectedRowKeys.includes(row.key));
    if (selectedRows.some((row) => !row.raw.is_batch_confirm_allowed)) {
      Modal.warning({
        title: "存在不可批量确认项",
        content: "高风险项、强制项或缺材料项必须逐条人工确认。"
      });
      appendLog("拦截批量确认：存在必须逐条确认的矩阵项");
      return;
    }
    let reason = "批量确认低风险合规矩阵项";
    Modal.confirm({
      title: "批量确认",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>将确认 {selectedRowKeys.length} 条合规矩阵项，并记录确认人和时间。</Text>
          <Text strong>批量确认说明（必填）</Text>
          <TextArea
            aria-label="批量确认说明"
            defaultValue={reason}
            placeholder="请填写批量确认依据，例如：已抽检低风险项，确认本批次可响应。"
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "确认",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId) {
          Modal.warning({ title: "请先选择项目和标段" });
          throw new Error("project or section required");
        }
        if (!reason.trim()) {
          Modal.warning({
            title: "需要填写批量确认说明",
            content: "请在弹窗中的“批量确认说明（必填）”输入框填写本次批量确认依据。"
          });
          throw new Error("reason required");
        }
        await bulkConfirmComplianceItems(selectedProjectId, selectedSectionId, {
          item_ids: selectedRowKeys.map(String),
          reason: reason.trim()
        });
        appendLog(`批量确认 ${selectedRowKeys.length} 条矩阵项`);
        await refreshAfterMatrixMutation();
        if (selectedRows.length > 0 && selectedRows.length === unresolvedMatrixRows.length) {
          Modal.success({
            title: "合规矩阵已完成",
            content: "所有矩阵项已经完成确认。下一步建议处理证据绑定，再运行资格预评估。"
          });
        }
      }
    });
  };

  const handleBatchAssign = () => {
    let reason = "批量指派给当前用户处理";
    Modal.confirm({
      title: "批量指派责任人",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>将为 {selectedRowKeys.length} 条矩阵项指派当前用户，变更会写入审计日志。</Text>
          <TextArea
            defaultValue={reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => {
              reason = event.target.value;
            }}
          />
        </Space>
      ),
      okText: "指派给我",
      cancelText: "取消",
      onOk: async () => {
        if (!selectedProjectId || !selectedSectionId || !reason.trim()) {
          Modal.warning({ title: "需要填写批量指派说明" });
          throw new Error("reason required");
        }
        await bulkAssignComplianceItems(selectedProjectId, selectedSectionId, {
          item_ids: selectedRowKeys.map(String),
          reason: reason.trim()
        });
        appendLog(`批量指派 ${selectedRowKeys.length} 条矩阵项`);
        await refreshAfterMatrixMutation();
      }
    });
  };

  const handleCreateProject = async () => {
    if (savingProject) return;
    if (projectCreateMode !== "manual" && !projectImportDraft) {
      Modal.warning({ title: projectCreateMode === "file" ? "请先上传招标文件并完成识别" : "请先完成导入识别" });
      return;
    }
    if (projectCreateMode === "manual" && !newProjectDraft.name.trim()) {
      Modal.warning({ title: "请填写项目名称" });
      return;
    }
    setSavingProject(true);
    try {
      if (projectCreateMode !== "manual" && projectImportDraft) {
        const result = await confirmProjectImportDraft({
          source: projectImportDraft.source,
          project: projectImportDraft.project,
          sections: projectImportDraft.sections,
          auto_parse: true,
          auto_generate_matrix: true,
          async_processing: true
        });
        appendLog(
          result.parse_task_id
            ? `导入创建项目：${result.project.name}，后台解析任务 ${result.parse_task_id.slice(0, 8)} 已启动`
            : `导入创建项目：${result.project.name}`
        );
        if (result.parse_task_id || result.matrix_task_id) {
          setImportProcessing({
            projectId: result.project.id,
            sectionId: result.section_id,
            parseTaskId: result.parse_task_id,
            matrixTaskId: result.matrix_task_id,
            parseTask: null,
            matrixTask: null
          });
        }
        setNewProjectOpen(false);
        await activateProjectWorkspace(result.project.id, result.section_id);
        Modal.info({
          title: "项目已创建",
          content: result.parse_task_id
            ? "文件解析和合规矩阵生成已转入后台处理。工作台顶部会持续显示后台任务状态，完成后自动刷新。"
            : "项目已创建完成。"
        });
        window.setTimeout(() => {
          activateProjectWorkspace(result.project.id, result.section_id).catch(() => undefined);
          reloadAuditLogs().catch(() => undefined);
        }, 1800);
        return;
      }

      const project = await createProject({
        name: newProjectDraft.name.trim(),
        purchaser: newProjectDraft.purchaser || null,
        agency: newProjectDraft.agency || null,
        budget_amount: newProjectDraft.budgetAmount || null,
        region_code: newProjectDraft.regionCode || null,
        industry_code: newProjectDraft.industryCode || null,
        notice_url: newProjectDraft.noticeUrl || null,
        bid_deadline_at: newProjectDraft.bidDeadlineAt,
        section_name: newProjectDraft.sectionName || "一标段"
      });
      appendLog(`新建项目：${project.name}`);
      setNewProjectOpen(false);
      await activateProjectWorkspace(project.id);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "项目创建失败");
    } finally {
      setSavingProject(false);
    }
  };

  const executeProjectDeletion = async (projectIds: string[]) => {
    if (!projectIds.length) return;
    setDeletingProjects(true);
    try {
      await Promise.all(projectIds.map((projectId) => deleteProject(projectId)));
      appendLog(projectIds.length === 1 ? "删除项目并归档隐藏" : `批量删除 ${projectIds.length} 个项目并归档隐藏`);
      setSelectedProjectRowKeys([]);
      if (selectedProjectId && projectIds.includes(selectedProjectId)) {
        setViewMode("home");
        setSelectedSectionId(undefined);
        setSelectedTreeKey("");
        setProjectDetail(null);
        setSections([]);
        setDocuments([]);
        setExportFiles([]);
        setComplianceItems([]);
        setQualificationEvaluations([]);
        setQualificationDecision(null);
        setBusinessDraftChapters([]);
        setApprovalTasks([]);
        setAuditLogs([]);
      }
      await reloadProjects();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "项目删除失败");
      throw error;
    } finally {
      setDeletingProjects(false);
    }
  };

  const confirmDeleteProjects = (projectIds: string[]) => {
    const targetProjects = projects.filter((project) => projectIds.includes(project.id));
    if (!targetProjects.length) return;
    Modal.confirm({
      title: targetProjects.length === 1 ? "删除项目" : `批量删除 ${targetProjects.length} 个项目`,
      content: (
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          <Text>
            删除后项目会归档隐藏，默认项目列表不再显示；项目文件、矩阵、审批和审计记录会保留在系统中。
          </Text>
          <Text type="secondary">
            {targetProjects
              .slice(0, 5)
              .map((project) => project.name)
              .join("、")}
            {targetProjects.length > 5 ? ` 等 ${targetProjects.length} 个项目` : ""}
          </Text>
        </Space>
      ),
      okText: "删除项目",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: () => executeProjectDeletion(projectIds)
    });
  };

  const handleUploadDocument: UploadProps["customRequest"] = async (options) => {
    if (!selectedProjectId || !selectedSectionId || !(options.file instanceof File)) return;
    setDocumentBusy(true);
    try {
      const document = await uploadDocument(selectedProjectId, selectedSectionId, {
        file: options.file,
        title: options.file.name.replace(/\.[^.]+$/, "")
      });
      const parseTask = await createParseTask(selectedProjectId, selectedSectionId, document.id);
      appendLog(`上传并解析文件：${document.original_filename}`);
      options.onSuccess?.(parseTask, options.file);
      await refreshAfterMatrixMutation();
    } catch (error) {
      options.onError?.(error as Error);
      setApiError(error instanceof Error ? error.message : "文件上传或解析失败");
    } finally {
      setDocumentBusy(false);
    }
  };

  const handlePublicUrlAcquisition = async () => {
    if (!selectedProjectId || !selectedSectionId || !publicUrl.trim()) {
      Modal.warning({ title: "请填写公开附件链接" });
      return;
    }
    setDocumentBusy(true);
    try {
      const acquisition = await requestPublicUrlAcquisition(selectedProjectId, selectedSectionId, {
        source_url: publicUrl.trim(),
        source_site: publicUrlSite || null,
        title: "公开链接招标文件"
      });
      if (acquisition.task.status === "failed") {
        setApiError(acquisition.task.error_message || acquisition.blocked_reason || "公开文件获取失败");
      } else {
        appendLog("获取公开附件并创建解析任务");
        setPublicUrl("");
        setPublicUrlSite("");
      }
      await refreshAfterMatrixMutation();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "公开链接获取失败");
    } finally {
      setDocumentBusy(false);
    }
  };

  const handleReparseDocument = async (document: ProjectDocument) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setDocumentBusy(true);
    try {
      const parseTask = await createParseTask(selectedProjectId, selectedSectionId, document.id);
      const latestTask = await getTask(parseTask.task.id);
      appendLog(`重新解析文件：${document.original_filename}（${latestTask.status}）`);
      await refreshAfterMatrixMutation();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "重新解析失败");
    } finally {
      setDocumentBusy(false);
    }
  };

  const handleReplanSemanticSections = async () => {
    if (!selectedProjectId || !selectedSectionId || !reviewDocument?.current_version_id) {
      Modal.warning({ title: "当前没有可重新规划的解析版本" });
      return;
    }
    setSectionPlanLoading(true);
    try {
      const sections = await replanDocumentSemanticSections(
        selectedProjectId,
        selectedSectionId,
        reviewDocument.id,
        reviewDocument.current_version_id
      );
      setSemanticSections(sections);
      await reloadExtractionQuality();
      appendLog(`重新规划章节：${sections.length} 段`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "重新规划章节失败");
      await reloadExtractionQuality();
    } finally {
      setSectionPlanLoading(false);
    }
  };

  const handleExtractSemanticSection = async (semanticSection: DocumentSemanticSection) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setSectionExtractingId(semanticSection.id);
    try {
      const task = await extractDocumentSemanticSectionCompliance(
        selectedProjectId,
        selectedSectionId,
        semanticSection.id
      );
      if (task.status === "failed") {
        throw new Error(task.error_message || "单段合规抽取失败");
      }
      appendLog(`重抽章节：${semanticSection.title}`);
      const [items] = await Promise.all([
        listComplianceItems(selectedProjectId, selectedSectionId, { limit: COMPLIANCE_ITEM_FETCH_LIMIT }),
        reloadExtractionQuality(),
        activeTab === "review" ? reloadMatrixReview() : Promise.resolve(),
        getPreflightCheck(selectedProjectId, selectedSectionId).then(setPreflightCheck).catch(() => undefined)
      ]);
      setComplianceItems(items);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "单段合规抽取失败");
      await reloadExtractionQuality();
    } finally {
      setSectionExtractingId("");
    }
  };

  const handleOpenRevisionDrawer = async (document: ProjectDocument) => {
    if (!selectedProjectId || !selectedSectionId || !document.current_version_id) {
      Modal.warning({ title: "文件尚无可查看的解析版本" });
      return;
    }
    setRevisionDrawerOpen(true);
    setRevisionDocument(document);
    setRevisionReason("");
    setRevisionSearch("");
    setLoadingRevisionChunks(true);
    try {
      const chunks = await listDocumentChunks(
        selectedProjectId,
        selectedSectionId,
        document.id,
        document.current_version_id
      );
      setRevisionChunks(chunks);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "解析分块加载失败");
      setRevisionChunks([]);
    } finally {
      setLoadingRevisionChunks(false);
    }
  };

  const updateRevisionChunk = (chunkId: string, patch: Partial<DocumentChunk>) => {
    setRevisionChunks((chunks) =>
      chunks.map((chunk) => (chunk.id === chunkId ? { ...chunk, ...patch } : chunk))
    );
  };

  const handlePublishManualRevision = async () => {
    if (!selectedProjectId || !selectedSectionId || !revisionDocument?.current_version_id) return;
    if (!revisionReason.trim()) {
      Modal.warning({ title: "请填写修正原因" });
      return;
    }
    if (revisionChunks.some((chunk) => !chunk.content_text.trim())) {
      Modal.warning({ title: "解析分块正文不能为空" });
      return;
    }
    setPublishingRevision(true);
    try {
      const result = await publishDocumentManualRevision(
        selectedProjectId,
        selectedSectionId,
        revisionDocument.id,
        revisionDocument.current_version_id,
        {
          reason: revisionReason.trim(),
          chunks: revisionChunks.map((chunk, index) => ({
            chunk_index: index + 1,
            page_no: chunk.page_no,
            heading_path: chunk.heading_path,
            content_text: chunk.content_text,
            bbox_json: chunk.bbox_json,
            table_json: chunk.table_json
          }))
        }
      );
      setRevisionDocument(result.document);
      setRevisionChunks(result.chunks);
      setRevisionReason("");
      appendLog(`发布解析修正版：${result.new_version.version_label}`);
      await reloadDocumentsAndExports();
      Modal.success({
        title: "解析修正版已发布",
        content: "新版本不会自动覆盖合规矩阵。可在文件列表中手动重新生成矩阵。"
      });
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "解析修正版发布失败");
    } finally {
      setPublishingRevision(false);
    }
  };

  const handleExportExcel = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setExportingExcel(true);
    try {
      const task = await exportComplianceMatrixExcel(selectedProjectId, selectedSectionId, {
        status: statusFilter,
        risk_level: riskFilter,
        owner_user_id: ownerFilter,
        item_type: undefined
      });
      appendLog(`导出合规矩阵快照：${task.status}`);
      await refreshAfterMatrixMutation();
      const exportFileId = task.output_json?.export_file_id;
      if (typeof exportFileId === "string") {
        window.open(`/api/v1/projects/${selectedProjectId}/export-files/${exportFileId}/download`, "_blank");
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "矩阵快照导出失败");
    } finally {
      setExportingExcel(false);
    }
  };

  const handleSaveEnterpriseProfile = async () => {
    if (!profileDraft.companyName.trim()) {
      Modal.warning({ title: "请填写企业名称" });
      return;
    }
    setSavingEnterprise(true);
    try {
      const profile = await upsertEnterpriseProfile({
        company_name: profileDraft.companyName.trim(),
        unified_social_credit_code: profileDraft.unifiedSocialCreditCode || null,
        legal_representative: profileDraft.legalRepresentative || null,
        registered_address: profileDraft.registeredAddress || null,
        business_scope: profileDraft.businessScope || null,
        region_preferences: profileDraft.regionPreferences,
        industry_preferences: profileDraft.industryPreferences,
        forbidden_rules: profileDraft.forbiddenRulesText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean)
      });
      setEnterpriseProfile(profile);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog(`维护企业画像：${profile.company_name}`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业画像保存失败");
    } finally {
      setSavingEnterprise(false);
    }
  };

  const resetNewMaterialDraft = () => {
    setNewMaterialDraft({
      materialType: "qualification",
      name: "",
      issuingAuthority: "",
      certificateNo: "",
      holderName: "",
      projectName: "",
      amount: "",
      validUntil: null,
      dataLevel: "internal",
      verificationStatus: "pending_confirm",
      evidenceText: ""
    });
  };

  const handleCreateEnterpriseMaterial = async () => {
    if (!newMaterialDraft.name.trim()) {
      Modal.warning({ title: "请填写资料名称" });
      return;
    }
    setSavingEnterprise(true);
    try {
      const material = await createEnterpriseMaterial({
        material_type: newMaterialDraft.materialType,
        name: newMaterialDraft.name.trim(),
        issuing_authority: newMaterialDraft.issuingAuthority || null,
        certificate_no: newMaterialDraft.certificateNo || null,
        holder_name: newMaterialDraft.holderName || null,
        project_name: newMaterialDraft.projectName || null,
        amount: newMaterialDraft.amount || null,
        valid_until: newMaterialDraft.validUntil,
        data_level: newMaterialDraft.dataLevel,
        verification_status: newMaterialDraft.verificationStatus,
        structured_fields: {
          source: "manual",
          material_type_label: materialTypeLabels[newMaterialDraft.materialType]
        },
        evidence_text: newMaterialDraft.evidenceText || null
      });
      setEnterpriseMaterials((items) => [material, ...items]);
      setMaterialModalOpen(false);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      resetNewMaterialDraft();
      appendLog(`新增企业资料：${material.name}`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业资料新增失败");
    } finally {
      setSavingEnterprise(false);
    }
  };

  const modelConfigPayload = (includeEmptyKey = false): ChatModelConfigPayload => ({
    provider: modelConfigDraft.provider,
    base_url: modelConfigDraft.baseUrl.trim() || null,
    simple_model: modelConfigDraft.simpleModel.trim() || null,
    complex_model: modelConfigDraft.complexModel.trim() || null,
    timeout_seconds: Number(modelConfigDraft.timeoutSeconds || 30),
    enabled: modelConfigDraft.enabled,
    api_key: modelConfigDraft.apiKey.trim() || (includeEmptyKey ? "" : null),
    clear_api_key: modelConfigDraft.clearApiKey
  });

  const handleSaveModelConfig = async () => {
    setSavingModelConfig(true);
    try {
      const config = await saveChatModelConfig(modelConfigPayload());
      applyChatModelConfig(config);
      setModelConfigTestResult(null);
      appendLog("更新 Chat 模型配置");
      Modal.success({ title: "模型配置已保存" });
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "模型配置保存失败");
    } finally {
      setSavingModelConfig(false);
    }
  };

  const handleTestModelConfig = async () => {
    setTestingModelConfig(true);
    try {
      const result = await testChatModelConfig(modelConfigPayload(true));
      setModelConfigTestResult(result);
      appendLog(`测试 Chat 模型配置：${result.status === "success" ? "成功" : "失败"}`);
      if (result.status === "success") {
        await reloadChatModelConfig();
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "模型连接测试失败");
    } finally {
      setTestingModelConfig(false);
    }
  };

  const makeMaterialFileUploadRequest =
    (material: EnterpriseMaterial): UploadProps["customRequest"] =>
    async (options) => {
      if (!(options.file instanceof File)) return;
      setSavingEnterprise(true);
      try {
        const updated = await uploadEnterpriseMaterialFile(material.id, {
          file: options.file,
          reason: "补充企业资料原始文件"
        });
        setEnterpriseMaterials((items) =>
          items.map((item) => (item.id === updated.id ? updated : item))
        );
        options.onSuccess?.(updated, options.file);
        appendLog(`上传企业资料原始文件：${updated.name}`);
      } catch (error) {
        options.onError?.(error as Error);
        setApiError(error instanceof Error ? error.message : "企业资料文件上传失败");
      } finally {
        setSavingEnterprise(false);
      }
    };

  return (
    <>
      <Layout className="app-shell">
        <Header className="topbar">
          <Space size={18} className="topbar-left">
            <button className="brand-mark" onClick={() => setViewMode("home")}>
              投标 Agent
            </button>
            <Button
              icon={<SafetyCertificateOutlined />}
              type={viewMode === "enterprise" ? "primary" : "default"}
              onClick={() => setViewMode("enterprise")}
            >
              企业资料库
            </Button>
            <Button
              icon={<SettingOutlined />}
              type={viewMode === "settings" ? "primary" : "default"}
              onClick={() => setViewMode("settings")}
            >
              模型设置
            </Button>
            <Select
              className="project-switcher"
              placeholder="选择项目"
              value={selectedProjectId}
              loading={loadingProjects}
              onChange={(value) => {
                openProjectWorkspace(value);
              }}
              options={projects.map((project) => ({ value: project.id, label: project.name }))}
            />
            <Input
              className="global-search"
              prefix={<SearchOutlined />}
              placeholder={viewMode === "home" ? "搜索项目、任务、审批、风险" : "搜索项目、条款、文件、证据"}
            />
            <Tag className="todo-tag" icon={<WarningOutlined />} color="orange">
              {sections.filter((section) => section.status !== "confirmed").length || 0} 个标段有未完成项
            </Tag>
          </Space>
          <Space size={14}>
            <Badge count={homeTodoRows.length} size="small">
              <Button icon={<BellOutlined />} />
            </Badge>
            <Avatar size={32} icon={<TeamOutlined />} />
          </Space>
        </Header>

        {apiError && (
          <Alert
            className="api-alert"
            type="warning"
            showIcon
            closable
            message="数据加载提醒"
            description={apiError}
            onClose={() => setApiError("")}
          />
        )}

        {viewMode === "settings" ? (
          <Content className="settings-page">
            <section className="home-heading">
              <div>
                <Text type="secondary">系统设置</Text>
                <Title level={2}>模型设置</Title>
                <Text type="secondary">
                  MVP1.1 先接入 Chat/LLM 配置；Embedding 与 Rerank 会在 MVP1.4 接入检索链路。
                </Text>
              </div>
              <Space wrap>
                <Button onClick={reloadChatModelConfig} loading={loadingModelConfig}>
                  刷新
                </Button>
                <Button onClick={handleTestModelConfig} loading={testingModelConfig}>
                  测试连接
                </Button>
                <Button type="primary" onClick={handleSaveModelConfig} loading={savingModelConfig}>
                  保存配置
                </Button>
              </Space>
            </section>

            <section className="settings-grid">
              <div className="home-panel settings-main-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>Chat 模型配置</Text>
                    <p>模型调用会优先读取数据库配置；禁用或不完整时回退环境变量和本地规则兜底。</p>
                  </div>
                  <Space wrap>
                    <Tag color={chatModelConfig?.source === "db" ? "blue" : chatModelConfig?.source === "env" ? "green" : "default"}>
                      来源：{chatModelConfig?.source === "db" ? "数据库" : chatModelConfig?.source === "env" ? "环境变量" : "本地兜底"}
                    </Tag>
                    <Tag color={modelConfigDraft.enabled ? "green" : "default"}>
                      {modelConfigDraft.enabled ? "已启用" : "已禁用"}
                    </Tag>
                  </Space>
                </div>

                <Spin spinning={loadingModelConfig}>
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <Space.Compact style={{ width: "100%" }}>
                      <Select
                        className="provider-select"
                        value={modelConfigDraft.provider}
                        onChange={(value) => setModelConfigDraft((draft) => ({ ...draft, provider: value }))}
                        options={[
                          { value: "mock", label: "Mock / 本地兜底" },
                          { value: "deepseek", label: "DeepSeek" },
                          { value: "openai_compatible", label: "OpenAI Compatible" }
                        ]}
                      />
                      <Input
                        placeholder="Base URL，例如 https://api.deepseek.com/v1"
                        value={modelConfigDraft.baseUrl}
                        onChange={(event) =>
                          setModelConfigDraft((draft) => ({ ...draft, baseUrl: event.target.value }))
                        }
                      />
                    </Space.Compact>

                    <Space.Compact style={{ width: "100%" }}>
                      <Input
                        placeholder="Simple Model"
                        value={modelConfigDraft.simpleModel}
                        onChange={(event) =>
                          setModelConfigDraft((draft) => ({ ...draft, simpleModel: event.target.value }))
                        }
                      />
                      <Input
                        placeholder="Complex Model"
                        value={modelConfigDraft.complexModel}
                        onChange={(event) =>
                          setModelConfigDraft((draft) => ({ ...draft, complexModel: event.target.value }))
                        }
                      />
                    </Space.Compact>

                    <Space.Compact style={{ width: "100%" }}>
                      <Input.Password
                        placeholder={
                          chatModelConfig?.api_key_masked
                            ? `已保存：${chatModelConfig.api_key_masked}；输入新 Key 会覆盖`
                            : "API Key"
                        }
                        value={modelConfigDraft.apiKey}
                        onChange={(event) =>
                          setModelConfigDraft((draft) => ({
                            ...draft,
                            apiKey: event.target.value,
                            clearApiKey: false
                          }))
                        }
                      />
                      <Input
                        type="number"
                        min={1}
                        max={300}
                        placeholder="超时秒数"
                        className="timeout-input"
                        value={modelConfigDraft.timeoutSeconds}
                        onChange={(event) =>
                          setModelConfigDraft((draft) => ({
                            ...draft,
                            timeoutSeconds: Number(event.target.value || 30)
                          }))
                        }
                      />
                    </Space.Compact>

                    <div className="settings-toggle-row">
                      <Space wrap>
                        <Switch
                          checked={modelConfigDraft.enabled}
                          onChange={(checked) => setModelConfigDraft((draft) => ({ ...draft, enabled: checked }))}
                          checkedChildren="启用"
                          unCheckedChildren="禁用"
                        />
                        <Switch
                          checked={modelConfigDraft.clearApiKey}
                          disabled={!chatModelConfig?.has_api_key}
                          onChange={(checked) =>
                            setModelConfigDraft((draft) => ({ ...draft, clearApiKey: checked, apiKey: "" }))
                          }
                          checkedChildren="清除 Key"
                          unCheckedChildren="保留 Key"
                        />
                      </Space>
                      <Text type="secondary">
                        明文 API Key 不会返回前端；保存新 Key 需要后端配置 MODEL_CONFIG_ENCRYPTION_KEY。
                      </Text>
                    </div>

                    {chatModelConfig?.last_test_status && (
                      <Alert
                        type={chatModelConfig.last_test_status === "success" ? "success" : "warning"}
                        showIcon
                        message={`最近测试：${chatModelConfig.last_test_status === "success" ? "成功" : "失败"}`}
                        description={`${chatModelConfig.last_test_message ?? "无详情"}${
                          chatModelConfig.last_tested_at ? ` · ${formatDateTime(chatModelConfig.last_tested_at)}` : ""
                        }`}
                      />
                    )}
                    {modelConfigTestResult && (
                      <Alert
                        type={modelConfigTestResult.status === "success" ? "success" : "error"}
                        showIcon
                        message={modelConfigTestResult.status === "success" ? "本次测试成功" : "本次测试失败"}
                        description={`${modelConfigTestResult.message} · 模型：${
                          modelConfigTestResult.model_name || "未识别"
                        } · 来源：${modelConfigTestResult.source}`}
                      />
                    )}
                  </Space>
                </Spin>
              </div>

              <div className="home-panel settings-side-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>后续能力预留</Text>
                    <p>检索增强会单独接入向量化和重排，不混进 Chat 配置。</p>
                  </div>
                </div>
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Alert
                    type="info"
                    showIcon
                    message="Embedding：MVP1.4 预留"
                    description="计划使用 BAAI/bge-large-zh-v1.5，将企业资料切片写入 pgvector。"
                  />
                  <Alert
                    type="info"
                    showIcon
                    message="Rerank：MVP1.4 预留"
                    description="计划使用 BAAI/bge-reranker-large，对候选证据做二次排序和解释。"
                  />
                  <Alert
                    type="warning"
                    showIcon
                    message="安全边界"
                    description="外部文件和网页均视为非可信输入；MVP1.1 不允许模型自动审批、自动提交或覆盖人工确认状态。"
                  />
                </Space>
              </div>
            </section>
          </Content>
        ) : viewMode === "enterprise" ? (
          <Content className="enterprise-page">
            <section className="home-heading">
              <div>
                <Text type="secondary">企业资料库</Text>
                <Title level={2}>投标能力底座</Title>
                <Text type="secondary">维护企业画像、资质证照、人员材料、业绩案例和商务模板，后续用于资格预评估和商务标书草稿。</Text>
              </div>
              <Space wrap>
                <Button onClick={reloadEnterprise} loading={loadingEnterprise}>
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    resetNewMaterialDraft();
                    setMaterialModalOpen(true);
                  }}
                >
                  新增资料
                </Button>
              </Space>
            </section>

            <section className="enterprise-grid">
              <div className="home-panel profile-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>企业画像</Text>
                    <p>资格预评估会优先读取这些基础字段</p>
                  </div>
                  {enterpriseProfile && <Tag color="green">已建档</Tag>}
                </div>
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Input
                    placeholder="企业名称"
                    value={profileDraft.companyName}
                    onChange={(event) => setProfileDraft((draft) => ({ ...draft, companyName: event.target.value }))}
                  />
                  <Space.Compact style={{ width: "100%" }}>
                    <Input
                      placeholder="统一社会信用代码"
                      value={profileDraft.unifiedSocialCreditCode}
                      onChange={(event) =>
                        setProfileDraft((draft) => ({ ...draft, unifiedSocialCreditCode: event.target.value }))
                      }
                    />
                    <Input
                      placeholder="法定代表人"
                      value={profileDraft.legalRepresentative}
                      onChange={(event) =>
                        setProfileDraft((draft) => ({ ...draft, legalRepresentative: event.target.value }))
                      }
                    />
                  </Space.Compact>
                  <Input
                    placeholder="注册地址"
                    value={profileDraft.registeredAddress}
                    onChange={(event) =>
                      setProfileDraft((draft) => ({ ...draft, registeredAddress: event.target.value }))
                    }
                  />
                  <TextArea
                    placeholder="经营范围"
                    value={profileDraft.businessScope}
                    autoSize={{ minRows: 3, maxRows: 5 }}
                    onChange={(event) => setProfileDraft((draft) => ({ ...draft, businessScope: event.target.value }))}
                  />
                  <Select
                    mode="tags"
                    placeholder="地域偏好，例如：湖南省、岳阳市、CN-4306"
                    value={profileDraft.regionPreferences}
                    onChange={(value) => setProfileDraft((draft) => ({ ...draft, regionPreferences: value }))}
                    tokenSeparators={[",", "，", " "]}
                  />
                  <Select
                    mode="tags"
                    placeholder="行业偏好，例如：市政、燃气、municipal-gas"
                    value={profileDraft.industryPreferences}
                    onChange={(value) => setProfileDraft((draft) => ({ ...draft, industryPreferences: value }))}
                    tokenSeparators={[",", "，", " "]}
                  />
                  <TextArea
                    placeholder="禁投规则，每行一条；命中项目上下文时会进入 Go/No-Go 阻断"
                    value={profileDraft.forbiddenRulesText}
                    autoSize={{ minRows: 3, maxRows: 5 }}
                    onChange={(event) =>
                      setProfileDraft((draft) => ({ ...draft, forbiddenRulesText: event.target.value }))
                    }
                  />
                  <Button type="primary" loading={savingEnterprise} onClick={handleSaveEnterpriseProfile}>
                    保存企业画像
                  </Button>
                </Space>
              </div>

              <div className="home-panel materials-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>企业资料</Text>
                    <p>第一版先手工结构化，后续接文件抽取和 RAG 检索</p>
                  </div>
                  <Space wrap>
                    <Tag color="blue">{enterpriseMaterials.length} 条资料</Tag>
                    <Tag color="green">{enterpriseMaterials.filter((item) => item.verification_status === "confirmed").length} 条已确认</Tag>
                  </Space>
                </div>
                <Table<EnterpriseMaterial>
                  size="middle"
                  rowKey="id"
                  loading={loadingEnterprise}
                  dataSource={enterpriseMaterials}
                  pagination={{ pageSize: 8 }}
                  scroll={{ x: 1180 }}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无企业资料" /> }}
                  columns={[
                    {
                      title: "资料名称",
                      dataIndex: "name",
                      width: 260,
                      render: (value, record) => (
                        <Space direction="vertical" size={0}>
                          <Text strong>{value}</Text>
                          <Text type="secondary">
                            {record.certificate_no || record.project_name || record.holder_name || "待补充结构化字段"}
                          </Text>
                        </Space>
                      )
                    },
                    {
                      title: "类型",
                      dataIndex: "material_type",
                      width: 120,
                      render: (value) => <Tag>{materialTypeLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "数据等级",
                      dataIndex: "data_level",
                      width: 110,
                      render: (value) => <Tag color={value === "confidential" ? "red" : value === "restricted" ? "orange" : "blue"}>{dataLevelLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "状态",
                      dataIndex: "verification_status",
                      width: 110,
                      render: (value) => <Tag color={statusColor(value)}>{verificationStatusLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "有效期",
                      dataIndex: "valid_until",
                      width: 130,
                      render: (value) => value ?? "未设置"
                    },
                    {
                      title: "证据",
                      dataIndex: "evidence_text",
                      width: 260,
                      render: (value, record) => value || record.file_name || "待补充"
                    },
                    {
                      title: "原始文件",
                      dataIndex: "file_name",
                      width: 170,
                      render: (value, record) => (
                        <Space direction="vertical" size={4}>
                          <Text type={value ? undefined : "secondary"}>{value || "未上传"}</Text>
                          <Upload
                            showUploadList={false}
                            customRequest={makeMaterialFileUploadRequest(record)}
                          >
                            <Button size="small" icon={<CloudUploadOutlined />} loading={savingEnterprise}>
                              上传
                            </Button>
                          </Upload>
                        </Space>
                      )
                    }
                  ]}
                />
              </div>
            </section>
          </Content>
        ) : viewMode === "home" ? (
          <Content className="home-page">
            <section className="home-heading">
              <div>
                <Text type="secondary">系统首页</Text>
                <Title level={2}>工作总览</Title>
                <Text type="secondary">集中查看待办、风险、截止时间和审批任务，再进入具体项目工作台处理。</Text>
              </div>
              <Space wrap>
                <Button icon={<PlusOutlined />} onClick={() => openCreateProjectModal("manual")}>
                  新建项目
                </Button>
                <Button type="primary" onClick={() => openWorkspace("matrix")} disabled={!selectedProjectId}>
                  进入最近项目
                </Button>
              </Space>
            </section>

            <section className="home-metrics">
              <div className="home-metric urgent">
                <Text type="secondary">我的待办</Text>
                <strong>{homeTodoRows.length}</strong>
                <span>{homeTodoRows.filter((row) => row.priority === "高").length} 项高优先级</span>
              </div>
              <div className="home-metric">
                <Text type="secondary">进行中项目</Text>
                <strong>{projects.length}</strong>
                <span>{projects.filter((project) => project.high_risk_count > 0).length} 个项目存在高风险</span>
              </div>
              <div className="home-metric">
                <Text type="secondary">待确认</Text>
                <strong>{projects.reduce((sum, project) => sum + project.pending_confirm_count, 0)}</strong>
                <span>合规矩阵项等待人工确认</span>
              </div>
              <div className="home-metric">
                <Text type="secondary">即将截止</Text>
                <strong>
                  {
                    projects.filter((project) =>
                      project.bid_deadline_at
                        ? dayjs(project.bid_deadline_at).diff(dayjs(), "day") <= 14
                        : false
                    ).length
                  }
                </strong>
                <span>14 天内需处理</span>
              </div>
            </section>

            <section className="home-grid">
              <div className="home-panel wide">
                <div className="panel-title-row">
                  <div>
                    <Text strong>我的待办</Text>
                    <p>按优先级处理当前责任事项</p>
                  </div>
                  <Button onClick={() => openWorkspace("approval")} disabled={!selectedProjectId}>
                    查看全部
                  </Button>
                </div>
                <Table<HomeTodoRow>
                  size="middle"
                  loading={loadingMatrix}
                  pagination={false}
                  dataSource={homeTodoRows}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办" /> }}
                  columns={[
                    {
                      title: "任务",
                      dataIndex: "task",
                      render: (value, record) => (
                        <Button type="link" onClick={() => locateMatrixRow(record.key)}>
                          {value}
                          {record.priority === "高" && <Tag color="red">高</Tag>}
                        </Button>
                      )
                    },
                    { title: "项目", dataIndex: "project", width: 220 },
                    { title: "责任人", dataIndex: "owner", width: 110 },
                    { title: "截止", dataIndex: "due", width: 130 }
                  ]}
                />
              </div>

              <div className="home-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>高风险项目</Text>
                    <p>需要优先复核的风险点</p>
                  </div>
                </div>
                <div className="risk-list">
                  {matrixRows.filter((row) => row.riskCode !== "low").length ? (
                    matrixRows
                      .filter((row) => row.riskCode !== "low")
                      .slice(0, 3)
                      .map((row) => (
                        <button className="risk-item" key={row.key} onClick={() => locateMatrixRow(row.key)}>
                          <WarningOutlined />
                          <span>{truncateText(row.requirement, 18)}</span>
                          <Tag color={riskColor(row.risk)}>{row.risk}</Tag>
                        </button>
                      ))
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无高风险项" />
                  )}
                </div>
              </div>

              <div className="home-panel wide">
                <div className="panel-title-row">
                  <div>
                    <Text strong>近期项目</Text>
                    <p>从项目进入标段工作台</p>
                  </div>
                  <Space wrap>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      loading={deletingProjects}
                      disabled={!selectedProjectRowKeys.length}
                      onClick={() => confirmDeleteProjects(selectedProjectRowKeys.map(String))}
                    >
                      批量删除
                    </Button>
                  </Space>
                </div>
                <Table<ProjectSummary>
                  size="middle"
                  loading={loadingProjects}
                  pagination={false}
                  dataSource={projects}
                  rowKey="id"
                  rowSelection={{
                    selectedRowKeys: selectedProjectRowKeys,
                    onChange: setSelectedProjectRowKeys
                  }}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无项目" /> }}
                  columns={[
                    {
                      title: "项目名称",
                      dataIndex: "name",
                      render: (value, record) => (
                        <Button
                          type="link"
                          onClick={() => {
                            openProjectWorkspace(record.id, "matrix");
                          }}
                        >
                          {value}
                        </Button>
                      )
                    },
                    {
                      title: "标段",
                      dataIndex: "section_count",
                      width: 110,
                      render: (value) => `${value} 个标段`
                    },
                    {
                      title: "截止时间",
                      dataIndex: "bid_deadline_at",
                      width: 180,
                      render: (value) => formatDateTime(value)
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 110,
                      render: (value) => <Tag color={statusColor(value)}>{projectStatusLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "风险",
                      dataIndex: "high_risk_count",
                      width: 90,
                      render: (value, record) => {
                        const risk = value > 0 ? "高" : record.pending_confirm_count > 0 ? "中" : "低";
                        return <Tag color={riskColor(risk)}>{risk}</Tag>;
                      }
                    },
                    {
                      title: "操作",
                      dataIndex: "actions",
                      width: 90,
                      render: (_: unknown, record) => (
                        <Tooltip title="删除后项目会归档隐藏，审计和历史数据仍保留">
                          <Button
                            danger
                            type="text"
                            size="small"
                            icon={<DeleteOutlined />}
                            loading={deletingProjects}
                            onClick={() => confirmDeleteProjects([record.id])}
                          />
                        </Tooltip>
                      )
                    }
                  ]}
                />
              </div>

              <div className="home-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>截止提醒</Text>
                    <p>按时间排序的关键节点</p>
                  </div>
                </div>
                <div className="deadline-list">
                  {projects.slice(0, 3).map((project) => (
                    <div key={project.id}>
                      <Tag color={project.pending_confirm_count ? "orange" : "blue"}>
                        {formatShortTime(project.bid_deadline_at).split(" ")[0]}
                      </Tag>
                      <strong>{project.bid_deadline_at ? dayjs(project.bid_deadline_at).format("HH:mm") : "待定"}</strong>
                      <span>{project.name}</span>
                    </div>
                  ))}
                  {!projects.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无截止提醒" />}
                </div>
              </div>
            </section>
          </Content>
        ) : (
          <Layout className={projectNavCollapsed ? "workspace-layout project-nav-collapsed" : "workspace-layout"}>
            <aside className={projectNavCollapsed ? "project-nav collapsed" : "project-nav"}>
              <div className="pane-title-row">
                {!projectNavCollapsed && <Text strong>项目导航</Text>}
                <Space size={4}>
                  <Tooltip title={projectNavCollapsed ? "展开项目导航" : "收起项目导航"}>
                    <Button
                      type="text"
                      size="small"
                      aria-label={projectNavCollapsed ? "展开项目导航" : "收起项目导航"}
                      icon={projectNavCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                      onClick={() => setProjectNavCollapsed((value) => !value)}
                    />
                  </Tooltip>
                  {!projectNavCollapsed && (
                    <Tooltip title="新建项目">
                      <Button
                        type="text"
                        size="small"
                        aria-label="新建项目"
                        icon={<PlusOutlined />}
                        onClick={() => openCreateProjectModal("manual")}
                      />
                    </Tooltip>
                  )}
                </Space>
              </div>
              {projectNavCollapsed ? (
                <div className="project-nav-rail">
                  <Tooltip title="新建项目">
                    <Button
                      type="text"
                      size="small"
                      aria-label="新建项目"
                      icon={<PlusOutlined />}
                      onClick={() => openCreateProjectModal("manual")}
                    />
                  </Tooltip>
                  <Tooltip title="项目导航已收起">
                    <FolderOpenOutlined />
                  </Tooltip>
                </div>
              ) : (
                <>
                  <div className="todo-summary">
                    <div>
                      <Text strong>全局待办</Text>
                      <p>
                        {homeTodoRows.length
                          ? `${homeTodoRows.length} 项待办；${matrixRows.filter((row) => row.riskCode === "high").length} 条高风险缺项。`
                          : "当前项目暂无待办。"}
                      </p>
                    </div>
                    <Button size="small" onClick={() => locateMatrixRow(matrixRows[0]?.key)} disabled={!matrixRows.length}>
                      查看
                    </Button>
                  </div>
                  <Spin spinning={loadingWorkspace}>
                    <Tree
                      showIcon
                      defaultExpandAll
                      selectedKeys={[selectedSectionId ? `section:${selectedSectionId}` : selectedProjectId ? `project:${selectedProjectId}` : ""]}
                      treeData={projectTreeData}
                      onSelect={(keys) => {
                        const key = keys[0] ? String(keys[0]) : "";
                        const [scope, id] = key.split(":");
                        if (scope === "project" && id) {
                          openProjectWorkspace(id, recommendedStep?.key ?? "documents");
                          return;
                        }
                        if (scope === "section" && id) {
                          setSelectedSectionId(id);
                          setSelectedTreeKey(`section:${id}:${recommendedStep?.key ?? "documents"}`);
                          setActiveTab(recommendedStep?.key ?? "documents");
                        }
                      }}
                    />
                  </Spin>
                </>
              )}
            </aside>

            <Content className="work-area">
              <section className="context-bar">
                <div>
                  <Title level={3}>{contextTitle}</Title>
                  <Space size={8} wrap>
                    <Text type="secondary">{currentSection?.name ?? "请选择标段"}</Text>
                    <Tooltip title="冻结后仍允许人工修正解析结果；保存修正会生成新版本，原冻结版本将存档用于审计回溯。">
                      <Tag color="blue">解析结果已冻结 v0.1</Tag>
                    </Tooltip>
                  </Space>
                </div>
                <Space wrap>
                  <Tag icon={<ClockCircleOutlined />} color="processing">
                    截止 {formatDateTime(currentSection?.bid_deadline_at ?? currentProject?.bid_deadline_at ?? null)}
                  </Tag>
                  <Button onClick={openKeyInfoModal} disabled={!currentProject || !currentSection}>
                    项目信息
                  </Button>
                  <Button type="primary" onClick={confirmSubmit}>
                    提交确认
                  </Button>
                </Space>
              </section>

              {importProcessingVisible && importProcessing && (
                <section className="background-task-panel">
                  <Alert
                    showIcon
                    type={importProcessingFailed ? "error" : importProcessingDone ? "success" : "info"}
                    message={importProcessingStageTitle}
                    description={
                      importProcessingQualityBlocked
                        ? "系统已暂停本轮写入，上一版矩阵仍保留。请进入质量门禁页按建议处理阻断项。"
                        : importProcessingParseFailed
                        ? "文件解析失败，请在文件解析页重新解析；如果原文件异常，可重新上传后再生成矩阵。"
                        : importProcessingMatrixFailed
                        ? "矩阵生成失败，请查看矩阵任务错误后重新生成；如果被质量门禁拦截，先处理质检阻断。"
                        : importProcessingFailed
                        ? "解析或矩阵生成失败，请查看下方任务状态后重新解析或重新生成矩阵。"
                        : importProcessingDone
                          ? "文件解析和合规矩阵已刷新，可继续处理风险、证据和确认项。"
                          : "这是后台异步任务，可以切换页面继续查看项目；完成后会自动刷新。"
                    }
                  />
                  <div className="background-task-overview">
                    <div className="background-task-overview-header">
                      <div>
                        <Text strong>后台解析/生成进度</Text>
                        <Text type="secondary">{importProcessingStageMessage}</Text>
                      </div>
                      <Tag color={importProcessingFailed ? "red" : importProcessingDone ? "green" : "blue"}>
                        {importProcessingPercent}%
                      </Tag>
                    </div>
                    <Progress
                      percent={importProcessingPercent}
                      status={importProcessingFailed ? "exception" : importProcessingDone ? "success" : "active"}
                      showInfo={false}
                    />
                    {!importProcessingDone && !importProcessingFailed && (
                      <Text type="secondary" className="background-task-hint">
                        当前不需要人工操作；如果质量门禁拦截，系统会在完成后引导到专门处理页。
                      </Text>
                    )}
                    {(importProcessingInProgress || importProcessingQualityBlocked || importProcessingFailed) && (
                      <Space className="background-task-actions" wrap>
                        <Button onClick={() => openWorkspace("tasks")}>
                          进入任务中心
                        </Button>
                        {importProcessingQualityBlocked && (
                          <Button type="primary" onClick={() => openWorkspace("quality")}>
                            处理质量门禁
                          </Button>
                        )}
                      </Space>
                    )}
                  </div>
                  <div className="background-task-grid">
                    {importProcessing.parseTaskId && (
                      <div className="background-task-card">
                        <div className="background-task-title">
                          <Text strong>文件解析</Text>
                          <Tag color={asyncTaskStatusColors[importProcessing.parseTask?.status ?? "pending"]}>
                            {asyncTaskStatusLabels[importProcessing.parseTask?.status ?? "pending"] ?? "处理中"}
                          </Tag>
                        </div>
                        <Text type="secondary">
                          {taskProgressMessage(
                            importProcessing.parseTask,
                            "正在读取文件并切分条款...",
                            "解析版本已生成。"
                          )}
                        </Text>
                      </div>
                    )}
                    {importProcessing.matrixTaskId && (
                      <div className="background-task-card">
                        <div className="background-task-title">
                          <Text strong>合规矩阵</Text>
                          <Tag color={asyncTaskStatusColors[importProcessing.matrixTask?.status ?? "pending"]}>
                            {asyncTaskStatusLabels[importProcessing.matrixTask?.status ?? "pending"] ?? "处理中"}
                          </Tag>
                        </div>
                        <Text type="secondary">{matrixTaskStageTitle(importProcessing.matrixTask)}</Text>
                        <Text type="secondary">
                          {taskProgressMessage(
                            importProcessing.matrixTask,
                            "正在抽取资格项、强制响应项和风险点...",
                            "矩阵已生成并刷新。"
                          )}
                        </Text>
                      </div>
                    )}
                  </div>
                </section>
              )}

              <section className={preflightCheck ? "command-center" : "command-center command-center-single"}>
                <div className="workflow-guide">
                  {recommendedStep && (
                    <div className="next-action-card">
                      <div className="next-action-copy">
                        <Text type="secondary" className="next-action-eyebrow">
                          现在先做
                        </Text>
                        <Text strong>当前任务：{recommendedStep.title}</Text>
                        <Text type="secondary">
                          {recommendedPreflightCheck
                            ? recommendedPreflightCheck.message
                            : recommendedStep.reason}
                        </Text>
                        <div className="next-action-tags">
                          {extractionQualityReport?.status === "passed" && <Tag color="green">质量门禁已通过</Tag>}
                          {preflightStatusForDisplay !== "pass" && (
                            <Tag color={preflightColor(preflightStatusForDisplay)}>
                              提交前核验{preflightLabel(preflightStatusForDisplay)}
                            </Tag>
                          )}
                          {visiblePreflightChecks
                            .filter((item) => item.status !== "pass")
                            .slice(0, 3)
                            .map((item) => (
                              <Tag key={item.code} color={preflightColor(item.status)}>
                                {item.title} {item.count}
                              </Tag>
                            ))}
                        </div>
                      </div>
                      <Button type="primary" onClick={() => runWorkflowPrimaryAction(recommendedStep.key)}>
                        {recommendedStep.actionText}
                      </Button>
                    </div>
                  )}
                  <div className="workflow-steps" aria-label="项目简化流程">
                    {simpleWorkflowSteps.map((step, index) => (
                      <Tooltip
                        key={step.key}
                        title={
                          <div className="workflow-step-tooltip">
                            <div className="workflow-step-tooltip-head">
                              <strong>{step.title}</strong>
                              <Tag color={workflowStatusColor(step.status)}>{step.statusText}</Tag>
                            </div>
                            <p>{step.disabled ? step.disabledReason : step.reason}</p>
                          </div>
                        }
                      >
                        <span
                          className="workflow-step-hitbox"
                          title={`${step.title} · ${step.statusText}\n${step.disabled ? step.disabledReason ?? "" : step.reason}`}
                        >
                          <button
                            className={[
                              "workflow-step",
                              `status-${step.status === "not_started" ? "not-started" : step.status}`,
                              step.activeKeys.includes(recommendedStep?.key as WorkflowStepKey) &&
                              step.status !== "done" &&
                              step.status !== "not_started"
                                ? "current-blocking"
                                : "",
                              step.activeKeys.includes(activeTab as WorkflowStepKey) ? "active" : "",
                              step.activeKeys.includes(recommendedStep?.key as WorkflowStepKey) ? "recommended" : "",
                              step.disabled ? "disabled" : ""
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            aria-label={`${index + 1}. ${step.title}，${step.statusText}`}
                            disabled={step.disabled}
                            onClick={() => activateWorkflowStep(step.targetKey)}
                          >
                            <span className="workflow-index">{index + 1}</span>
                            <strong>{step.title}</strong>
                          </button>
                        </span>
                      </Tooltip>
                    ))}
                  </div>

                  {currentProject && currentSection && missingKeyInfo.length > 0 && (
                    <section className="key-info-panel">
                      <div className="key-info-header">
                        <Space wrap>
                          <Text strong>项目关键信息</Text>
                          {missingKeyInfo.length ? (
                            <Tag color="orange">缺失 {missingKeyInfo.join("、")}</Tag>
                          ) : (
                            <Tag color="green">关键字段已填写</Tag>
                          )}
                        </Space>
                        <Button size="small" onClick={openKeyInfoModal}>
                          编辑/确认
                        </Button>
                      </div>
                      <div className="key-info-grid">
                        <div>
                          <Text type="secondary">招标人</Text>
                          <strong>{currentProject.purchaser || "未填写"}</strong>
                        </div>
                        <div>
                          <Text type="secondary">预算/限价</Text>
                          <strong>{currentSection.budget_amount || currentProject.budget_amount || "未填写"}</strong>
                        </div>
                        <div>
                          <Text type="secondary">投标截止</Text>
                          <strong>{formatDateTime(currentSection.bid_deadline_at ?? currentProject.bid_deadline_at)}</strong>
                        </div>
                        <div>
                          <Text type="secondary">地区/行业</Text>
                          <strong>{[currentProject.region_code, currentProject.industry_code].filter(Boolean).join(" / ") || "未填写"}</strong>
                        </div>
                      </div>
                    </section>
                  )}

                  <section className="status-grid">
                    <div className="metric-item">
                      <Text type="secondary">合规项</Text>
                      <strong>{currentSection?.compliance_item_count ?? matrixRows.length}</strong>
                      <Text type="secondary">{unresolvedMatrixRows.length ? `${unresolvedMatrixRows.length} 条待确认` : "已全部确认"}</Text>
                    </div>
                    <div className="metric-item">
                      <Text type="secondary">缺项</Text>
                      <strong>{matrixRows.filter((row) => row.statusCode === "needs_material").length}</strong>
                      <Text type="secondary">需要补资料或说明</Text>
                    </div>
	                    <div className="metric-item">
	                      <Text type="secondary">已确认</Text>
	                      <strong>{matrixRows.length ? matrixRows.filter((row) => row.statusCode === "confirmed").length : knownConfirmedMatrixCount}</strong>
	                      <Text type="secondary">人工核对完成</Text>
	                    </div>
                    <div className="metric-item">
                      <Text type="secondary">高风险</Text>
                      <strong>{currentSection?.high_risk_count ?? 0}</strong>
                      <Text type="secondary">{unresolvedHighRiskRows.length ? `${unresolvedHighRiskRows.length} 条待处理` : "暂无待处理"}</Text>
                    </div>
                    <div className="metric-item approval-metric">
                      <Text type="secondary">{mvp13DraftWorkflowAvailable ? "待审批" : "上下文包"}</Text>
                      <strong>
                        {mvp13DraftWorkflowAvailable
                          ? approvalTasks.filter((task) => task.status === "pending").length
                          : activeContextPack
                            ? 1
                            : 0}
                      </strong>
                      <Button size="small" onClick={() => activateWorkflowStep(mvp13DraftWorkflowAvailable ? "tasks" : "chapter")}>
                        {mvp13DraftWorkflowAvailable ? "进入任务中心" : "查看 ContextPack"}
                      </Button>
                    </div>
                  </section>
                </div>

                {preflightCheck && (
                  <div className="preflight-panel">
                    <div className="preflight-header">
                      <Space wrap>
                        <Text strong>待办队列</Text>
                        <Tag color={preflightColor(preflightStatusForDisplay)}>{preflightLabel(preflightStatusForDisplay)}</Tag>
                        {preflightCheck.matrix_outdated && <Tag color="red">矩阵已过期</Tag>}
                      </Space>
                      <Text type="secondary">
                        {visiblePreflightChecks.some((item) => item.status !== "pass")
                          ? "按卡片顺序处理；点击卡片会进入对应页面或执行对应操作。"
                          : preflightCheck.summary}
                      </Text>
                    </div>
                    <div className="preflight-checks">
                      {visiblePreflightChecks.map((item) => (
                        <button
                          key={item.code}
                          className={`preflight-check ${item.status}`}
                          onClick={() => handlePreflightCheckAction(item)}
                        >
                          <Tag color={preflightColor(item.status)}>{item.title}</Tag>
                          <strong>{item.status === "pass" ? "已通过" : item.count}</strong>
                          <span>{item.message}</span>
                          <span className="preflight-action-text">{preflightActionText(item)}</span>
                        </button>
                      ))}
                    </div>
                    {preflightChecksForDisplay.length > 4 && (
                      <Button
                        type="text"
                        size="small"
                        className="preflight-expand-button"
                        onClick={() => setPreflightExpanded((value) => !value)}
                      >
                        {preflightExpanded ? "收起待办" : `展开全部（还有 ${hiddenPreflightCheckCount} 项）`}
                      </Button>
                    )}
                  </div>
                )}
              </section>

              <Tabs
                className="workspace-tabs"
                activeKey={activeTab}
                renderTabBar={() => <></>}
                onChange={(key) => {
                  activateWorkflowStep(key as WorkflowStepKey);
                }}
                items={[
                  {
                    key: "tasks",
                    label: "任务中心",
                    children: (
                      <div className="workspace-panel task-center-panel">
                        <div className="tab-intro">
                          <div>
                            <Text strong>后台任务中心</Text>
                            <p>集中查看文件解析、并发抽取、质量门禁和下一步动作。</p>
                          </div>
                        </div>

                        <div className="task-center-status">
                          <div className="task-center-status-main">
                            <div>
                              <Text strong>{importProcessingStageTitle}</Text>
                              <p>{importProcessingStageMessage}</p>
                            </div>
                            <Tag color={importProcessingFailed ? "red" : importProcessingDone ? "green" : currentImportProcessing ? "blue" : "default"}>
                              {currentImportProcessing ? `${importProcessingPercent}%` : "空闲"}
                            </Tag>
                          </div>
                          {currentImportProcessing && (
                            <Progress
                              percent={importProcessingPercent}
                              status={importProcessingFailed ? "exception" : importProcessingDone ? "success" : importProcessingOpenTask ? "active" : "normal"}
                              showInfo={false}
                            />
                          )}
                          <div className="task-center-actions">
                            {importProcessingQualityBlocked ? (
                              <Button type="primary" icon={<WarningOutlined />} onClick={() => activateWorkflowStep("quality")}>
                                处理质量门禁
                              </Button>
                            ) : importProcessingParseFailed ? (
                              <Button
                                type="primary"
                                icon={<FileTextOutlined />}
                                onClick={() => (reviewDocument ? handleReparseDocument(reviewDocument) : activateWorkflowStep("documents"))}
                              >
                                重新解析文件
                              </Button>
                            ) : importProcessingMatrixFailed ? (
                              <Button type="primary" icon={<RobotOutlined />} onClick={() => handleGenerateMatrix(reviewDocument ?? undefined)}>
                                重新生成矩阵
                              </Button>
                            ) : importProcessingFailed ? (
                              <Button type="primary" icon={<RobotOutlined />} onClick={() => handleGenerateMatrix(reviewDocument ?? undefined)}>
                                重试后台处理
                              </Button>
                            ) : matrixTaskActive ? (
                              <Button icon={<ClockCircleOutlined />} disabled>
                                等待后台完成
                              </Button>
                            ) : matrixRows.length ? (
                              <Button type="primary" icon={<FileSearchOutlined />} onClick={() => activateWorkflowStep("matrix")}>
                                进入合规矩阵
                              </Button>
                            ) : reviewDocument?.current_version_id ? (
                              <Button type="primary" icon={<RobotOutlined />} onClick={() => handleGenerateMatrix(reviewDocument)}>
                                生成合规矩阵
                              </Button>
                            ) : (
                              <Button type="primary" icon={<FileTextOutlined />} onClick={() => activateWorkflowStep("documents")}>
                                去上传/解析文件
                              </Button>
                            )}
                            <Button onClick={() => activateWorkflowStep("documents")}>查看文件解析</Button>
                          </div>
                        </div>

                        {currentImportProcessing && (currentImportProcessing.parseTaskId || currentImportProcessing.matrixTaskId) ? (
                          <div className="task-center-grid">
                            {currentImportProcessing.parseTaskId && (
                              <div className="task-center-card">
                                <div className="task-center-card-head">
                                  <div>
                                    <Text strong>文件解析</Text>
                                    <Text type="secondary">任务 {taskShortId(currentImportProcessing.parseTaskId)}</Text>
                                  </div>
                                  <Tag color={asyncTaskStatusColors[currentImportProcessing.parseTask?.status ?? "pending"]}>
                                    {asyncTaskStatusText(currentImportProcessing.parseTask, currentImportProcessing.parseTaskId)}
                                  </Tag>
                                </div>
                                <Text type="secondary">
                                  {taskProgressMessage(
                                    currentImportProcessing.parseTask,
                                    "正在读取文件、识别页码并切分条款。",
                                    "解析版本已生成。"
                                  )}
                                </Text>
                                <Text type="secondary">{taskTimeRange(currentImportProcessing.parseTask)}</Text>
                              </div>
                            )}

                            {currentImportProcessing.matrixTaskId && (
                              <div className="task-center-card">
                                <div className="task-center-card-head">
                                  <div>
                                    <Text strong>合规矩阵</Text>
                                    <Text type="secondary">任务 {taskShortId(currentImportProcessing.matrixTaskId)}</Text>
                                  </div>
                                  <Tag color={asyncTaskStatusColors[currentImportProcessing.matrixTask?.status ?? "pending"]}>
                                    {asyncTaskStatusText(currentImportProcessing.matrixTask, currentImportProcessing.matrixTaskId)}
                                  </Tag>
                                </div>
                                <Text type="secondary">{matrixTaskStageTitle(currentImportProcessing.matrixTask)}</Text>
                                <Text type="secondary">
                                  {taskProgressMessage(
                                    currentImportProcessing.matrixTask,
                                    "正在抽取资格项、强制响应项和风险点。",
                                    "矩阵已生成并刷新。"
                                  )}
                                </Text>
                                <div className="task-center-stats">
                                  {matrixForkJoinWorkers ? <Tag color="blue">并发 {matrixForkJoinWorkers}</Tag> : null}
                                  {matrixForkJoinTotal ? (
                                    <Tag color="geekblue">
                                      已完成 {matrixForkJoinCompleted || 0}/{matrixForkJoinTotal} 段
                                    </Tag>
                                  ) : null}
                                  {matrixForkJoinPending ? <Tag color="gold">剩余 {matrixForkJoinPending} 段</Tag> : null}
                                </div>
                                {matrixForkJoinPendingSections.length > 0 && (
                                  <div className="task-center-pending-list">
                                    <Text type="secondary">正在处理或排队</Text>
                                    {matrixForkJoinPendingSections.map((section, index) => (
                                      <span key={`${section.section_index ?? index}-${section.section_title ?? "section"}`}>
                                        {section.section_index ? `${section.section_index}/` : ""}
                                        {matrixForkJoinTotal ? `${matrixForkJoinTotal} ` : ""}
                                        {String(section.section_title ?? "未命名章节")}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                <Text type="secondary">{taskTimeRange(currentImportProcessing.matrixTask)}</Text>
                              </div>
                            )}
                          </div>
                        ) : (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有后台任务" />
                        )}

                        <div className="task-center-next">
                          <Text strong>用户下一步</Text>
                          <Text type="secondary">
                            {importProcessingOpenTask
                              ? "不用在矩阵里找问题，等后台完成即可；如果被质量门禁拦截，系统会在这里给出处理按钮。"
                              : importProcessingQualityBlocked
                                ? "点击“处理质量门禁”，按建议重新生成或只重抽问题段。"
                                : importProcessingParseFailed
                                  ? "点击“重新解析文件”；如果同一文件继续失败，回到文件解析页重新上传或人工修正原文。"
                                  : importProcessingMatrixFailed
                                    ? "点击“重新生成矩阵”；如果再次失败，优先查看质量门禁或矩阵任务错误信息。"
                                : matrixRows.length
                                  ? "进入合规矩阵，优先确认高风险和强制响应条款。"
                                  : "先完成文件解析，再生成合规矩阵。"}
                          </Text>
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "documents",
                    label: "文件解析",
                    children: (
                      <div className="workspace-panel document-panel">
                        <div className="document-actions">
                          <Upload
                            showUploadList={false}
                            accept=".docx,.pdf"
                            customRequest={handleUploadDocument}
                            disabled={documentBusy}
                          >
                            <Button icon={<FileTextOutlined />} loading={documentBusy}>
                              上传 Word/PDF
                            </Button>
                          </Upload>
                          <Input
                            className="public-url-input"
                            prefix={<LinkOutlined />}
                            placeholder="公开附件链接（外部内容按非可信输入处理）"
                            value={publicUrl}
                            onChange={(event) => setPublicUrl(event.target.value)}
                          />
                          <Input
                            className="source-site-input"
                            placeholder="资源站点"
                            value={publicUrlSite}
                            onChange={(event) => setPublicUrlSite(event.target.value)}
                          />
                          <Button type="primary" loading={documentBusy} onClick={handlePublicUrlAcquisition}>
                            获取附件
                          </Button>
                        </div>
                        <Table<ProjectDocument>
                          className="document-table"
                          size="middle"
                          pagination={false}
                          rowKey="id"
                          loading={documentBusy}
                          dataSource={documents}
                          scroll={{ x: 1040 }}
                          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文件" /> }}
                          columns={[
                            {
                              title: "文件",
                              dataIndex: "title",
                              width: 360,
                              render: (value, record) => (
                                <div className="document-name-cell">
                                  <Tooltip title={value}>
                                    <Text strong className="document-name-text">
                                      {value}
                                    </Text>
                                  </Tooltip>
                                  <Tooltip title={record.original_filename}>
                                    <Text type="secondary" className="document-name-text">
                                      {record.original_filename}
                                    </Text>
                                  </Tooltip>
                                </div>
                              )
                            },
                            {
                              title: "来源",
                              dataIndex: "source_type",
                              width: 150,
                              render: (value, record) => (
                                <Tag color={value === "public_url" ? "blue" : "green"}>
                                  {value === "public_url" ? record.source_site || "公开链接" : "本地上传"}
                                </Tag>
                              )
                            },
                            {
                              title: "解析状态",
                              dataIndex: "current_version",
                              width: 130,
                              render: (_, record) => (
                                <Tag color={isUsableParseStatus(record.current_version?.parse_status) ? "green" : "orange"}>
                                  {record.current_version?.parse_status ?? "待解析"}
                                </Tag>
                              )
                            },
                            {
                              title: "获取时间",
                              dataIndex: "acquired_at",
                              width: 170,
                              render: (value) => formatDateTime(value)
                            },
                            {
                              title: "操作",
                              width: 300,
                              render: (_, record) => (
                                <Space size={6} wrap>
                                  <Button size="small" onClick={() => handleOpenRevisionDrawer(record)}>
                                    查看/修正
                                  </Button>
                                  <Button size="small" onClick={() => handleGenerateMatrix(record)}>
                                    重生成矩阵
                                  </Button>
                                  <Button size="small" onClick={() => handleReparseDocument(record)}>
                                    重新解析
                                  </Button>
                                </Space>
                              )
                            }
                          ]}
                        />
                        {reviewDocument?.current_version_id && (
                          <div className="section-plan-panel">
                            <div className="section-plan-header">
                              <div>
                                <Text strong>AI 章节计划与抽取质量</Text>
                                <p>
                                  {semanticSections.length
                                    ? `当前解析版本已规划 ${semanticSections.length} 个语义段。`
                                    : "当前解析版本尚未生成章节计划。"}
                                </p>
                              </div>
                              <Space>
                                {extractionQualityReport && (
                                  <Tag color={extractionQualityReport.status === "blocked" ? "red" : "green"}>
                                    {extractionQualityReport.status === "blocked" ? "质量阻断" : "质量通过"}
                                  </Tag>
                                )}
                                <Button loading={sectionPlanLoading} onClick={handleReplanSemanticSections}>
                                  重新规划章节
                                </Button>
                              </Space>
                            </div>
                            {extractionQualityReport?.status === "blocked" && (
                              <Alert
                                type="warning"
                                showIcon
                                message="存在质量门禁阻断"
                                description={
                                  <Space direction="vertical" size={8}>
                                    <Text>
                                      本轮生成结果未写入，{matrixRows.length ? "上一版矩阵仍可查看。" : "请处理后重新生成矩阵。"}
                                    </Text>
                                    <Button size="small" type="primary" onClick={() => activateWorkflowStep("quality")}>
                                      进入质量门禁
                                    </Button>
                                  </Space>
                                }
                              />
                            )}
                            <Table<DocumentSemanticSection>
                              size="small"
                              pagination={false}
                              rowKey="id"
                              loading={sectionPlanLoading}
                              dataSource={semanticSections}
                              locale={{
                                emptyText: (
                                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无章节计划" />
                                )
                              }}
                              columns={[
                                {
                                  title: "段",
                                  dataIndex: "section_index",
                                  width: 64,
                                  render: (value) => <Tag>{value}</Tag>
                                },
                                {
                                  title: "标题",
                                  dataIndex: "title",
                                  render: (value, record) => (
                                    <div className="document-name-cell">
                                      <Text strong>{value}</Text>
                                      <Text type="secondary">{record.evidence || record.section_type}</Text>
                                    </div>
                                  )
                                },
                                {
                                  title: "页码",
                                  width: 110,
                                  render: (_, record) => `${record.start_page}-${record.end_page}`
                                },
                                {
                                  title: "置信度",
                                  width: 100,
                                  render: (_, record) =>
                                    record.confidence_score == null
                                      ? "-"
                                      : `${Math.round(record.confidence_score * 100)}%`
                                },
                                {
                                  title: "状态",
                                  dataIndex: "status",
                                  width: 120,
                                  render: (value) => (
                                    <Tag color={value === "verified" ? "green" : value === "low_confidence" ? "orange" : "blue"}>
                                      {value}
                                    </Tag>
                                  )
                                },
                                {
                                  title: "操作",
                                  width: 130,
                                  render: (_, record) => (
                                    <Button
                                      size="small"
                                      loading={sectionExtractingId === record.id}
                                      onClick={() => handleExtractSemanticSection(record)}
                                    >
                                      重抽当前段
                                    </Button>
                                  )
                                }
                              ]}
                            />
                          </div>
                        )}
                        {exportFiles.length > 0 && (
                          <div className="export-list">
                            <Text strong>归档快照</Text>
                            {exportFiles.slice(0, 3).map((file) => (
                              <a
                                key={file.id}
                                href={`/api/v1/projects/${file.project_id}/export-files/${file.id}/download`}
                                target="_blank"
                                rel="noreferrer"
                              >
                                <DownloadOutlined />
                                {file.file_name}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
	                    )
	                  },
                  {
                    key: "quality",
                    label: "质量门禁",
                    children: (
                      <div className="workspace-panel quality-gate-panel">
                        <div className="tab-intro">
                          <div>
                            <Text strong>{extractionBlocked ? "处理质量门禁" : "抽取质量门禁"}</Text>
                            <p>
                              {extractionBlocked
                                ? "系统已拦截本轮生成结果，按建议重新生成即可。"
                                : "生成矩阵时自动检查章节规划、来源回链和关键条款覆盖。"}
                            </p>
                          </div>
                          <Tag color={extractionBlocked ? "red" : extractionQualityReport ? "green" : "default"}>
                            {extractionBlocked ? `${extractionQualityIssueCount} 个阻断` : extractionQualityReport ? "质量通过" : "待生成"}
                          </Tag>
                        </div>

                        {!reviewDocument?.current_version_id ? (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先上传并解析招标文件" />
                        ) : !extractionQualityReport ? (
                          <Alert
                            type="info"
                            showIcon
                            message="尚未形成质量报告"
                            description={
                              <Space direction="vertical" size={8}>
                                <Text>先生成合规矩阵；系统会自动检查是否漏抽关键条款。</Text>
                                <Button type="primary" icon={<RobotOutlined />} onClick={() => handleGenerateMatrix(reviewDocument)}>
                                  生成合规矩阵
                                </Button>
                              </Space>
                            }
                          />
                        ) : extractionQualityReport.status === "passed" ? (
                          <Alert
                            type="success"
                            showIcon
                            message="质量门禁已通过"
                            description={
                              <Space direction="vertical" size={8}>
                                <Text>最近一次抽取未发现阻断项，可以继续处理合规矩阵。</Text>
                                <Button type="primary" icon={<FileSearchOutlined />} onClick={() => activateWorkflowStep("matrix")}>
                                  进入合规矩阵
                                </Button>
                              </Space>
                            }
                          />
                        ) : (
                          <>
                            <div className="quality-recommendation-card">
                              <div className="quality-recommendation-main">
                                <span className="quality-recommendation-icon">
                                  <WarningOutlined />
                                </span>
                                <div>
                                  <Text strong>现在只需要做一件事</Text>
                                  <p>
                                    点击“按建议处理”，系统会用已补齐的漏抽规则重新生成全量矩阵。通过后再回到矩阵审阅。
                                  </p>
                                </div>
                              </div>
                              <div className="quality-recommendation-actions">
                                <Button
                                  type="primary"
                                  icon={<RobotOutlined />}
                                  loading={loadingMatrix || matrixTaskActive}
                                  disabled={matrixTaskActive}
                                  onClick={() => handleGenerateMatrix(reviewDocument)}
                                >
                                  {matrixTaskActive ? "正在重新生成" : "按建议处理"}
                                </Button>
                                <Button
                                  icon={<FileSearchOutlined />}
                                  disabled={!matrixRows.length}
                                  onClick={() => activateWorkflowStep("matrix")}
                                >
                                  查看上一版矩阵
                                </Button>
                              </div>
                              <div className="quality-safety-notes">
                                <span>失败结果未写入</span>
                                <span>上一版矩阵保留</span>
                                <span>{extractionQualityIssueCount} 个阻断会重新校验</span>
                              </div>
                            </div>
                            <details className="quality-details">
                              <summary>技术诊断（可选）：查看 {extractionQualityIssueCount} 个阻断</summary>
                              <div className="quality-detail-intro">
                                <Text strong>系统定位到的漏抽位置</Text>
                                <p>
                                  这些内容只用于核查原因。正常处理时不需要逐条操作，直接使用上方“按建议处理”即可。
                                </p>
                              </div>
                              <Spin spinning={loadingQualityChunks}>
                                <div className="quality-issue-list quality-issue-list-standalone">
                                  {extractionQualityIssues.length ? (
                                    extractionQualityIssues.map((issue, index) => {
                                      const semanticSection = semanticSections.find((section) => section.id === issue.section_id);
                                      const terms = qualityIssueSearchTerms(issue);
                                      const sourceChunk = qualityIssueSourceChunk(issue, semanticSection, qualityDisplayChunks);
                                      const sourceExcerpt = qualityIssueSourceExcerpt(sourceChunk, terms);
                                      return (
                                        <div className="quality-issue-item" key={`${issue.code}-${issue.section_id ?? "unknown"}-${index}`}>
                                          <div className="quality-issue-title">
                                            <Space size={6} wrap>
                                              <Tag color={qualityIssueSeverityColor(issue.severity)}>{issue.severity}</Tag>
                                              <Text strong>{issue.section_title ?? semanticSection?.title ?? "未定位章节"}</Text>
                                              {semanticSection && <Tag>{semanticSection.start_page}-{semanticSection.end_page} 页</Tag>}
                                              {issue.page_no && <Tag>第 {issue.page_no} 页</Tag>}
                                              {issue.source_chunk_index && <Tag>chunk {issue.source_chunk_index}</Tag>}
                                            </Space>
                                          </div>
                                          <Text>{issue.message}</Text>
                                          <Text type="secondary">{qualityIssueActionText(issue)}</Text>
                                          {sourceExcerpt && (
                                            <div className="quality-source-snippet">
                                              <Text type="secondary">
                                                原文定位：第 {sourceChunk?.page_no ?? "-"} 页
                                                {sourceChunk?.chunk_index ? ` · chunk ${sourceChunk.chunk_index}` : ""}
                                              </Text>
                                              <p>{sourceExcerpt}</p>
                                            </div>
                                          )}
                                          <Button
                                            size="small"
                                            disabled={!semanticSection}
                                            loading={Boolean(semanticSection && sectionExtractingId === semanticSection.id)}
                                            onClick={() => semanticSection && handleExtractSemanticSection(semanticSection)}
                                          >
                                            只重抽这一段
                                          </Button>
                                        </div>
                                      );
                                    })
                                  ) : (
                                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可展示的阻断明细" />
                                  )}
                                </div>
                              </Spin>
                              <div className="quality-gate-toolbar">
                                <Text type="secondary">高级操作</Text>
                                <Button size="small" loading={sectionPlanLoading} onClick={handleReplanSemanticSections}>
                                  重新规划章节
                                </Button>
                                <Button size="small" disabled={!matrixRows.length} onClick={() => activateWorkflowStep("review")}>
                                  打开审阅台
                                </Button>
                              </div>
                            </details>
                          </>
                        )}
                      </div>
                    )
                  },
	                  {
	                    key: "evidence",
                    label: "证据处理",
                    children: (
                      <div className="workspace-panel evidence-work-panel">
                        <div className="tab-intro">
                          <div>
                            <Text strong>集中处理缺证据项</Text>
                            <p>优先为缺材料、未绑定企业资料的矩阵项补证，再进入资格预评估和商务草稿。</p>
                          </div>
                          <Tag color={evidenceRows.length ? "gold" : "green"}>
                            {evidenceRows.length ? `${evidenceRows.length} 项待处理` : "证据已补齐"}
                          </Tag>
                        </div>
                        <Table<MatrixRow>
                          size="middle"
                          pagination={LARGE_TABLE_PAGINATION}
                          rowKey="key"
                          rowClassName={(record) => (record.key === highlightedRowKey ? "highlighted-row" : "")}
                          dataSource={evidenceRows}
                          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无缺证据项" /> }}
                          columns={[
                            {
                              title: "招标要求",
                              dataIndex: "requirement",
                              render: (value: string, record) => {
                                const qualificationIssue = qualificationNeedsMaterialByItemId.get(record.key);
                                return (
                                  <Space direction="vertical" size={4}>
                                    <Tooltip title={value}>
                                      <span className="clamped-cell">{value}</span>
                                    </Tooltip>
                                    {qualificationIssue && (
                                      <Space size={6} wrap>
                                        <Tag color="red">资格缺材料</Tag>
                                        <Text type="secondary">
                                          {qualificationIssue.missing_materials?.join("、") ||
                                            qualificationIssue.reason ||
                                            "需补充企业资料"}
                                        </Text>
                                      </Space>
                                    )}
                                  </Space>
                                );
                              }
                            },
                            {
                              title: "状态",
                              dataIndex: "status",
                              width: 110,
                              render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>
                            },
                            {
                              title: "风险",
                              dataIndex: "risk",
                              width: 90,
                              render: (value: string) => <Tag color={riskColor(value)}>{value}</Tag>
                            },
                            {
                              title: "已绑定资料",
                              dataIndex: "enterpriseEvidenceCount",
                              width: 130,
                              render: (value: number) => <Tag color={value ? "blue" : "default"}>{value} 项</Tag>
                            },
                            {
                              title: "处理",
                              dataIndex: "actions",
                              width: 230,
                              render: (_: unknown, record) => (
                                <Space size={6} wrap>
                                  <Button
                                    type="primary"
                                    size="small"
                                    loading={openingEvidenceItemId === record.key}
                                    disabled={Boolean(openingEvidenceItemId) && openingEvidenceItemId !== record.key}
                                    onClick={() => openEvidenceBindingDrawer(record)}
                                  >
                                    绑定资料
                                  </Button>
                                  <Button
                                    size="small"
                                    loading={waivingEvidenceItemId === record.key}
                                    disabled={Boolean(waivingEvidenceItemId) && waivingEvidenceItemId !== record.key}
                                    onClick={() => handleWaiveEvidenceRequirement(record)}
                                  >
                                    无需绑定证据
                                  </Button>
                                </Space>
                              )
                            }
                          ]}
                        />
                      </div>
                    )
                  },
                  {
                    key: "qualification",
                    label: "资格预评估",
                    children: (
                      <div className="workspace-panel qualification-panel">
                        <div className="qualification-summary">
                          <div>
                            <Text strong>参标资格预评估</Text>
                            <p>基于资格类矩阵项和企业资料库执行轻量规则判断，结论需人工确认。</p>
                          </div>
                          <Space wrap>
                            <Tag color="green">
                              满足 {qualificationEvaluations.filter((item) => item.evaluation_status === "satisfied").length}
                            </Tag>
                            <Tag color="red">
                              阻断 {blockingQualificationEvaluations.length}
                            </Tag>
                            <Tag color="gold">
                              待确认 {qualificationEvaluations.filter((item) => item.evaluation_status === "pending_confirm").length}
                            </Tag>
                            <Button
                              type="primary"
                              icon={<RobotOutlined />}
                              loading={evaluatingQualification}
                              onClick={handleRunQualificationEvaluation}
                            >
                              重新评估
                            </Button>
                            <Button
                              icon={<SafetyCertificateOutlined />}
                              loading={generatingDecision}
                              onClick={handleGenerateQualificationDecision}
                            >
                              生成参标建议
                            </Button>
                          </Space>
                        </div>
                        <div className="decision-card">
                          {qualificationDecision ? (
                            <>
                              <div className="decision-head">
                                <Space wrap>
                                  <Tag color={decisionColors[qualificationDecision.recommendation]}>
                                    {decisionLabels[qualificationDecision.recommendation] ??
                                      qualificationDecision.recommendation}
                                  </Tag>
                                  <Tag color={qualificationDecision.status === "confirmed" ? "green" : "gold"}>
                                    {qualificationDecision.status === "confirmed" ? "已确认" : "待确认"}
                                  </Tag>
                                  <Text type="secondary">
                                    满足 {qualificationDecision.satisfied_count} / 缺材料{" "}
                                    {qualificationDecision.missing_count} / 阻断 {qualificationDecision.blocking_count}
                                  </Text>
                                </Space>
                                <Button
                                  size="small"
                                  type="primary"
                                  disabled={qualificationDecision.status === "confirmed"}
                                  onClick={handleConfirmQualificationDecision}
                                >
                                  确认建议
                                </Button>
                              </div>
                              <p>{qualificationDecision.summary}</p>
                              {qualificationDecision.status === "confirmed" && qualificationDecision.recommendation === "no_go" && (
                                <Alert
                                  type="error"
                                  showIcon
                                  message="当前结论为 No-Go"
                                  description="如仍需生成商务草稿，请先在草稿入口填写风险接受说明；建议优先回到矩阵和证据项处理阻断。"
                                />
                              )}
                            </>
                          ) : (
                            <Alert
                              type="info"
                              showIcon
                              message="尚未生成 Go/No-Go 参标建议"
                              description="先运行资格预评估，再生成参标建议；系统会同时创建资格确认审批任务。"
                            />
                          )}
                        </div>
                        {blockingQualificationEvaluations.length > 0 && (
                          <Alert
                            className="qualification-blocker-alert"
                            type="error"
                            showIcon
                            message={`当前存在 ${blockingQualificationEvaluations.length} 个资格阻断项`}
                            description={
                              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                                <Text>
                                  {missingQualificationEvaluations.length
                                    ? `先处理 ${missingQualificationEvaluations.length} 项缺资料/未匹配企业资料；`
                                    : ""}
                                  {notSatisfiedQualificationEvaluations.length
                                    ? `再复核 ${notSatisfiedQualificationEvaluations.length} 项不满足规则；`
                                    : ""}
                                  处理后重新运行资格预评估，并重新生成/确认参标建议。
                                </Text>
                                <Space wrap>
                                  {missingQualificationEvaluations.length > 0 && (
                                    <Button size="small" type="primary" onClick={openQualificationEvidenceWork}>
                                      去补资料
                                    </Button>
                                  )}
                                  <Button size="small" onClick={() => activateWorkflowStep("review")}>
                                    回到矩阵审阅
                                  </Button>
                                  <Button size="small" loading={evaluatingQualification} onClick={handleRunQualificationEvaluation}>
                                    重新评估
                                  </Button>
                                </Space>
                              </Space>
                            }
                          />
                        )}
                        <div className="qualification-next-step">
                          {!qualificationEvaluations.length ? (
                            <>
                              <div>
                                <Text strong>下一步：运行资格预评估</Text>
                                <p>先把资格类矩阵项和企业资料库做一次规则匹配，形成可确认的评估表。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<RobotOutlined />}
                                loading={evaluatingQualification}
                                onClick={handleRunQualificationEvaluation}
                              >
                                运行资格预评估
                              </Button>
                            </>
                          ) : !qualificationDecision ? (
                            <>
                              <div>
                                <Text strong>下一步：生成参标建议</Text>
                                <p>评估表已有结果，继续汇总为 Go/No-Go 建议，并创建资格确认审批任务。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<SafetyCertificateOutlined />}
                                loading={generatingDecision}
                                onClick={handleGenerateQualificationDecision}
                              >
                                生成参标建议
                              </Button>
                            </>
                          ) : qualificationDecision.status !== "confirmed" ? (
                            <>
                              <div>
                                <Text strong>下一步：确认参标建议</Text>
                                <p>确认后即可把该结论作为商务标生成前的资格上下文。</p>
                              </div>
                              <Button type="primary" onClick={handleConfirmQualificationDecision}>
                                确认建议
                              </Button>
                            </>
                          ) : (
                            <>
                              <div>
                                <Text strong>下一步：生成商务标草稿</Text>
                                <p>资格结论已确认，可以进入商务草稿生成，把评估结果传给最终产出。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<SendOutlined />}
                                onClick={() => {
                                  setActiveTab("chapter");
                                  setWorkspaceNode("chapter");
                                }}
                              >
                                去商务草稿
                              </Button>
                            </>
                          )}
                        </div>
                        <div className="qualification-table-scroll">
                          <Table<QualificationEvaluation>
                            size="middle"
                            rowKey="id"
                            pagination={LARGE_TABLE_PAGINATION}
                            loading={evaluatingQualification}
                            scroll={{ x: 1580 }}
                            dataSource={qualificationEvaluations}
                            locale={{
                              emptyText: (
                                <Empty
                                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                                  description="尚未运行资格预评估"
                                />
                              )
                            }}
                            columns={[
                              {
                                title: "资格要求",
                                dataIndex: "requirement_text",
                                width: 340,
                                render: (value) => (
                                  <Tooltip title={value}>
                                    <span className="clamped-cell">{value}</span>
                                  </Tooltip>
                                )
                              },
                              {
                                title: "类型",
                                dataIndex: "requirement_type",
                                width: 120,
                                render: (value) => <Tag>{qualificationTypeLabels[value] ?? value}</Tag>
                              },
                              {
                                title: "评估结果",
                                dataIndex: "evaluation_status",
                                width: 120,
                                render: (value) => (
                                  <Tag color={statusColor(value)}>{qualificationStatusLabels[value] ?? value}</Tag>
                                )
                              },
                              {
                                title: "风险",
                                dataIndex: "risk_level",
                                width: 90,
                                render: (value) => <Tag color={riskColor(value)}>{riskLabels[value] ?? value}</Tag>
                              },
                              {
                                title: "匹配资料",
                                dataIndex: "matched_material_name",
                                width: 220,
                                render: (value, record) => value || record.missing_materials?.join("、") || "需人工确认"
                              },
                              {
                                title: "规则",
                                dataIndex: "matched_rule_code",
                                width: 190,
                                render: (value, record) => (
                                  <Space direction="vertical" size={0}>
                                    <Text>{value}</Text>
                                    <Text type="secondary">v{record.rule_version}</Text>
                                  </Space>
                                )
                              },
                              {
                                title: "判断说明",
                                dataIndex: "reason",
                                width: 340,
                                render: (value) => (
                                  <Tooltip title={value}>
                                    <span className="clamped-cell">{value}</span>
                                  </Tooltip>
                                )
                              },
                              {
                                title: "确认",
                                dataIndex: "confirmed_at",
                                width: 160,
                                fixed: "right",
                                render: (value, record) =>
                                  value ? (
                                    <Tag color="green">已确认</Tag>
                                  ) : (
                                    <Button size="small" onClick={() => handleConfirmQualificationEvaluation(record)}>
                                      人工确认
                                    </Button>
                                  )
                              }
                            ]}
                          />
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "matrix",
                    label: "合规矩阵",
                    children: (
                      <div className="workspace-panel">
                        <div className="matrix-toolbar">
                          <Space wrap>
                            <Select
                              allowClear
                              placeholder="状态"
                              value={statusFilter}
                              onChange={setStatusFilter}
                              options={Object.entries(statusLabels).map(([value, label]) => ({
                                value,
                                label
                              }))}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="责任人"
                              value={ownerFilter}
                              onChange={setOwnerFilter}
                              options={ownerOptions}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="风险"
                              value={riskFilter}
                              onChange={setRiskFilter}
                              options={Object.entries(riskLabels).map(([value, label]) => ({ value, label }))}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="强制项"
                              value={mandatoryFilter}
                              onChange={setMandatoryFilter}
                              options={[
                                { value: "mandatory", label: "仅强制项" },
                                { value: "normal", label: "非强制项" }
                              ]}
                              className="toolbar-select"
                            />
                            <Switch
                              checked={prioritySortEnabled}
                              onChange={setPrioritySortEnabled}
                              checkedChildren="推荐处理"
                              unCheckedChildren="原顺序"
                            />
                          </Space>
                          <Space wrap>
                            <Button icon={<RobotOutlined />} loading={loadingMatrix} onClick={() => handleGenerateMatrix()}>
                              生成矩阵
                            </Button>
                            <Button icon={<FileSearchOutlined />} disabled={!matrixRows.length} onClick={() => activateWorkflowStep("review")}>
                              矩阵审阅
                            </Button>
                            <Button disabled={!selectedRowKeys.length} onClick={handleBatchConfirm}>
                              批量确认
                            </Button>
                            <Button
                              disabled={!selectedRowKeys.length}
                              onClick={handleBatchAssign}
                            >
                              批量指派
                            </Button>
                            <Tooltip title="导出当前筛选结果的只读快照，用于归档、会议或外部协作；最新状态以平台为准。">
                              <Button icon={<DownloadOutlined />} onClick={confirmExport} loading={exportingExcel}>
                                导出快照
                              </Button>
                            </Tooltip>
                          </Space>
                        </div>
                        {preflightCheck?.matrix_outdated && (
                          <Alert
                            className="matrix-completion-alert"
                            type="error"
                            showIcon
                            message="矩阵已过期，建议基于最新解析版本重新生成"
                            description={`当前最新解析版本：${preflightCheck.latest_document_version_label ?? "未识别"}；矩阵使用版本：${preflightCheck.matrix_version_labels.join("、") || "未生成"}`}
                            action={
                              <Button size="small" type="primary" onClick={() => handleGenerateMatrix()}>
                                重新生成矩阵
                              </Button>
                            }
                          />
                        )}
                        {isMatrixComplete && (
                          <Alert
                            className="matrix-completion-alert"
                            type="success"
                            showIcon
                            message="合规矩阵已完成"
                            description={
                              evidenceRows.length
                                ? `已确认 ${matrixRows.length} 条矩阵项。下一步建议处理 ${evidenceRows.length} 条证据绑定，再运行资格预评估。`
                                : "所有矩阵项已确认且证据已齐备，可以运行资格预评估并生成参标建议。"
                            }
                            action={
                              <Button
                                size="small"
                                type="primary"
                                onClick={() => runWorkflowPrimaryAction(recommendedStep?.key ?? "evidence")}
                              >
                                进入下一步
                              </Button>
                            }
                          />
                        )}
                        <Table<MatrixRow>
                          size="middle"
                          pagination={LARGE_TABLE_PAGINATION}
                          loading={loadingMatrix}
                          rowSelection={{
                            selectedRowKeys,
                            onChange: setSelectedRowKeys
                          }}
                          rowClassName={(record) => (record.key === highlightedRowKey ? "highlighted-row" : "")}
                          scroll={{ x: 1840 }}
                          dataSource={displayedMatrixRows}
                          locale={{
                            emptyText: (
                              <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description={
                                  documents.some((document) => isUsableParseStatus(document.current_version?.parse_status))
                                    ? "暂无合规矩阵项；请先点击生成合规矩阵"
                                    : "暂无合规矩阵项；请先完成文件解析"
                                }
                              />
                            )
                          }}
                          columns={[
                            {
                              title: "招标要求",
                              dataIndex: "requirement",
                              width: 360,
                              render: (value: string) => (
                                <Tooltip title={value}>
                                  <span className="clamped-cell">{value}</span>
                                </Tooltip>
                              )
                            },
                            {
                              title: "证据来源",
                              dataIndex: "source",
                              width: 240,
                              render: (value: string, record) => (
                                <Tooltip title={value}>
                                  <Button
                                    type="link"
                                    className="table-link-text"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setSourceDrawer(record);
                                    }}
                                  >
                                    {value}
                                  </Button>
                                </Tooltip>
                              )
                            },
                            {
                              title: "章节",
                              dataIndex: "chapter",
                              width: 120,
                              sorter: (a, b) => a.chapter.localeCompare(b.chapter)
                            },
                            {
                              title: "推荐处理",
                              dataIndex: ["raw", "priority_label"],
                              width: 150,
                              sorter: (a, b) => a.raw.priority_rank - b.raw.priority_rank,
                              render: (_: unknown, record) => (
                                <Tooltip title={record.raw.priority_reason}>
                                  <Tag color={record.raw.priority_rank <= 1 ? "red" : record.raw.priority_rank === 2 ? "blue" : "default"}>
                                    {record.raw.priority_label}
                                  </Tag>
                                </Tooltip>
                              )
                            },
                            {
                              title: "强制项",
                              dataIndex: "mandatory",
                              width: 100,
                              render: (value: boolean, record) => (
                                <Tooltip title={explanationText(record.raw.rule_explanation, "batch_confirm_reason")}>
                                  {value ? <Tag color="red">是</Tag> : <Tag>否</Tag>}
                                </Tooltip>
                              )
                            },
                            {
                              title: "责任人",
                              dataIndex: "owner",
                              width: 120,
                              sorter: (a, b) => a.owner.localeCompare(b.owner)
                            },
                            {
                              title: "状态",
                              dataIndex: "status",
                              width: 110,
                              sorter: (a, b) => a.status.localeCompare(b.status),
                              render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>
                            },
                            {
                              title: "风险",
                              dataIndex: "risk",
                              width: 90,
                              sorter: (a, b) => {
                                const order: Record<string, number> = { 高: 3, 中: 2, 低: 1 };
                                return order[a.risk] - order[b.risk];
                              },
                              render: (value: string, record) => (
                                <Tooltip title={explanationText(record.raw.rule_explanation, "risk_reason")}>
                                  <Tag color={riskColor(value)}>{value}</Tag>
                                </Tooltip>
                              )
                            },
                            {
                              title: "响应证据",
                              dataIndex: "evidence",
                              width: 360,
                              fixed: "right",
                              render: (value: string, record) => (
                                <Space direction="vertical" size={6} className="evidence-cell">
                                  <Tooltip title={value}>
                                    <Text className="evidence-text">{value}</Text>
                                  </Tooltip>
                                  <Space size={6} wrap>
                                    {record.enterpriseEvidenceCount > 0 && (
                                      <Tag color="blue">已绑定 {record.enterpriseEvidenceCount} 项</Tag>
                                    )}
                                    {record.enterpriseEvidenceNotRequired && (
                                      <Tooltip title={record.enterpriseEvidenceNotRequiredReason ?? "人工判定无需绑定企业资料证据"}>
                                        <Tag color="green">无需绑定证据</Tag>
                                      </Tooltip>
                                    )}
                                    <Button
                                      size="small"
                                      type={record.statusCode === "needs_material" && !record.enterpriseEvidenceNotRequired ? "primary" : "default"}
                                      icon={<FileSearchOutlined />}
                                      loading={openingEvidenceItemId === record.key}
                                      disabled={Boolean(openingEvidenceItemId) && openingEvidenceItemId !== record.key}
                                      onClick={() => openEvidenceBindingDrawer(record)}
                                    >
                                      {record.enterpriseEvidenceCount ? "管理资料" : "绑定资料"}
                                    </Button>
                                    {!record.enterpriseEvidenceNotRequired && record.enterpriseEvidenceCount === 0 && (
                                      <Button
                                        size="small"
                                        loading={waivingEvidenceItemId === record.key}
                                        disabled={Boolean(waivingEvidenceItemId) && waivingEvidenceItemId !== record.key}
                                        onClick={() => handleWaiveEvidenceRequirement(record)}
                                      >
                                        无需绑定证据
                                      </Button>
                                    )}
                                  </Space>
                                </Space>
                              )
                            },
                            {
                              title: "操作",
                              dataIndex: "actions",
                              width: 340,
                              fixed: "right",
                              render: (_: unknown, record) => (
                                <Space size={6}>
                                  <Button size="small" icon={<FileTextOutlined />} onClick={() => setSourceDrawer(record)}>
                                    原文
                                  </Button>
                                  <Tooltip
                                    title={
                                      draftBlocksByComplianceItemId.has(record.key)
                                        ? "定位覆盖该条款的结构化草稿 block"
                                        : "该条款尚未覆盖到结构化草稿 block"
                                    }
                                  >
                                    <span>
                                      <Button
                                        size="small"
                                        disabled={!draftBlocksByComplianceItemId.has(record.key)}
                                        onClick={() => locateDraftBlockForRow(record.key)}
                                      >
                                        草稿
                                      </Button>
                                    </span>
                                  </Tooltip>
                                  <Button
                                    size="small"
                                    type="primary"
                                    disabled={record.statusCode === "confirmed"}
                                    onClick={() => handleConfirmItem(record)}
                                  >
                                    确认
                                  </Button>
                                  <Button size="small" onClick={() => openEditDraft(record)}>
                                    编辑
                                  </Button>
                                  <Button size="small" onClick={() => handleAssignItem(record)}>
                                    指派
                                  </Button>
                                </Space>
                              )
                            }
                          ]}
                        />
                      </div>
                    )
                  },
                  {
                    key: "review",
                    label: "矩阵审阅",
                    children: (
                      <div className="workspace-panel matrix-review-panel">
                        <div className="matrix-review-header">
                          <div>
                            <Text strong>原文 / 矩阵对照审阅</Text>
                            <p>按解析 chunk 定位来源，支持人工划选补漏、重复关联、级联确认和相似片段差异核对。</p>
                          </div>
                          <Space wrap>
                            <Tag color="green">
                              已确认 {reviewProgress.confirmed}/{reviewProgress.total}
                            </Tag>
                            <Tag color={reviewProgress.highTotal === reviewProgress.highConfirmed ? "green" : "red"}>
                              高风险 {reviewProgress.highConfirmed}/{reviewProgress.highTotal}
                            </Tag>
                            <Tag color={reviewUncoveredChunks.length ? "gold" : "green"}>
                              疑似未覆盖 {reviewUncoveredChunks.length}
                            </Tag>
                            <Tag color={reviewDuplicateGroups.length ? "blue" : "default"}>
                              关联组 {reviewDuplicateGroups.length}
                            </Tag>
                            <Select<MatrixReviewFilter>
                              value={matrixReviewFilter}
                              onChange={(value) => {
                                setMatrixReviewFilter(value);
                                setReviewQueuePage(1);
                              }}
                              className="toolbar-select"
                              options={[
                                { value: "all", label: "全部条目" },
                                { value: "unconfirmed", label: "仅未确认" },
                                { value: "high", label: "高风险" },
                                { value: "mandatory", label: "强制项" },
                                { value: "missing_evidence", label: "缺证据" }
                              ]}
                            />
                            <Button
                              icon={<HighlightOutlined />}
                              type={sourceCreateMode ? "primary" : "default"}
                              onClick={() => setSourceCreateMode((value) => !value)}
                            >
                              从原文新增
                            </Button>
                          </Space>
                        </div>
                        {sourceCreateMode && (
                          <Alert
                            type="info"
                            showIcon
                            message="请在左侧原文中划选需要补入矩阵的文字"
                            description="划选后会打开新增条目弹窗，系统保存 chunk 来源并提示其他相似片段。"
                          />
                        )}
                        <Progress
                          percent={reviewProgress.total ? Math.round((reviewProgress.confirmed / reviewProgress.total) * 100) : 0}
                          showInfo={false}
                          strokeColor="#16a34a"
                        />
                        {matrixRows.length === 0 ? (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无矩阵项；请先生成合规矩阵" />
                        ) : (
                          <div className="matrix-review-layout">
                            <div className="review-source-pane" ref={reviewSourcePaneRef}>
                              <div className="review-pane-title">
                                <Text strong>招标文件原文</Text>
                                <Space size={6} wrap>
                                  <Tag
                                    color={
                                      reviewOpenXmlDocument?.mode === "word_xml"
                                        ? "blue"
                                        : reviewOpenXmlDocument?.mode === "pdf_layout"
                                          ? "cyan"
                                          : "gold"
                                    }
                                  >
                                    {reviewOpenXmlDocument?.mode === "word_xml"
                                      ? "Word 原文"
                                      : reviewOpenXmlDocument?.mode === "pdf_layout"
                                        ? "PDF 原文"
                                        : "解析文本"}
                                  </Tag>
                                  <Tag>
                                    {reviewOpenXmlDocument?.version_label ??
                                      reviewDocument?.current_version?.version_label ??
                                      "当前解析版本"}
                                  </Tag>
                                </Space>
                              </div>
                              <Spin spinning={loadingReviewChunks}>
                                {reviewOpenXmlDocument?.blocks.length ? (
                                  <div
                                    className={`word-review-document ${
                                      reviewOpenXmlDocument.mode === "word_xml"
                                        ? "word-mode"
                                        : reviewOpenXmlDocument.mode === "pdf_layout"
                                          ? "pdf-mode"
                                          : "fallback-mode"
                                    }`}
                                    style={{
                                      paddingTop: reviewOpenXmlDocument.page_margins?.top
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.top, 72)}pt`
                                        : undefined,
                                      paddingRight: reviewOpenXmlDocument.page_margins?.right
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.right, 72)}pt`
                                        : undefined,
                                      paddingBottom: reviewOpenXmlDocument.page_margins?.bottom
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.bottom, 72)}pt`
                                        : undefined,
                                      paddingLeft: reviewOpenXmlDocument.page_margins?.left
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.left, 72)}pt`
                                        : undefined
                                    }}
                                  >
                                    {reviewOpenXmlDocument.reason && (
                                      <Alert type="warning" showIcon message={reviewOpenXmlDocument.reason} className="review-fallback-alert" />
                                    )}
                                    {reviewOpenXmlDocument.headers.map((header, index) => (
                                      <div className="word-review-header-text" key={`header-${index}`}>
                                        {header}
                                      </div>
                                    ))}
                                    {(() => {
                                      let lastPdfPageNo: number | null = null;
                                      return reviewOpenXmlDocument.blocks.map((block) => {
                                      const highlights = block.chunk_id ? reviewHighlightByChunkId.get(block.chunk_id) ?? [] : [];
                                      const chunk = blockToReviewChunk(block);
                                      const uncovered = block.chunk_id ? uncoveredChunkMap.get(block.chunk_id) : undefined;
                                      const blockActive = highlights.some((highlight) => highlight.item_id === activeReviewItemId);
                                      const blockLocating = highlights.some((highlight) => highlight.item_id === locatingReviewItemId);
                                      const showPdfPage =
                                        reviewOpenXmlDocument.mode === "pdf_layout" &&
                                        block.page_no != null &&
                                        block.page_no !== lastPdfPageNo;
                                      if (block.page_no != null) lastPdfPageNo = block.page_no;
                                      const pageDivider = showPdfPage ? (
                                        <div className="pdf-review-page-break">第 {block.page_no} 页</div>
                                      ) : null;
                                      if (block.type === "table") {
                                        return (
                                          <Fragment key={block.id}>
                                            {pageDivider}
                                          <div
                                            id={block.chunk_id ? `review-block-${block.chunk_id}` : block.id}
                                            className={`word-review-block word-review-table-block ${blockActive ? "active" : ""} ${
                                              blockLocating ? "locating" : ""
                                            }`}
                                            style={reviewBlockCss(block)}
                                            onMouseUp={(event) => handleReviewBlockMouseUp(event, block)}
                                            onClick={() => block.chunk_id && focusReviewChunk(block.chunk_id)}
                                          >
                                            <table className="word-review-table">
                                              <tbody>
                                                {block.rows.map((row, rowIndex) => (
                                                  <tr key={`${block.id}-row-${rowIndex}`}>
                                                    {row.cells.map((cell, cellIndex) => (
                                                      <td key={`${block.id}-cell-${rowIndex}-${cellIndex}`}>
                                                        {cell.paragraphs.map((paragraph, paragraphIndex) => (
                                                          <p
                                                            key={`${block.id}-cell-p-${rowIndex}-${cellIndex}-${paragraphIndex}`}
                                                            style={paragraphCss(paragraph)}
                                                          >
                                                            {renderReviewParagraph(
                                                              paragraph,
                                                              highlights,
                                                              `${block.id}-cell-${rowIndex}-${cellIndex}-${paragraphIndex}`
                                                            )}
                                                          </p>
                                                        ))}
                                                      </td>
                                                    ))}
                                                  </tr>
                                                ))}
                                              </tbody>
                                            </table>
                                            {uncovered && chunk && (
                                              <div className="review-uncovered-hint">
                                                <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                                <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                  新增条目
                                                </Button>
                                              </div>
                                            )}
                                          </div>
                                          </Fragment>
                                        );
                                      }
                                      return (
                                        <Fragment key={block.id}>
                                          {pageDivider}
                                        <div
                                          id={block.chunk_id ? `review-block-${block.chunk_id}` : block.id}
                                          className={`word-review-block ${block.type === "heading" ? "word-review-heading" : ""} ${
                                            blockActive ? "active" : ""
                                          } ${blockLocating ? "locating" : ""}`}
                                          style={reviewBlockCss(block)}
                                          onMouseUp={(event) => handleReviewBlockMouseUp(event, block)}
                                          onClick={() => block.chunk_id && focusReviewChunk(block.chunk_id)}
                                        >
                                          <p style={paragraphCss(block.paragraph)}>
                                            {block.paragraph
                                              ? renderReviewParagraph(block.paragraph, highlights, block.id)
                                              : renderHighlightedText(block.text, highlights, block.id)}
                                          </p>
                                          {uncovered && chunk && (
                                            <div className="review-uncovered-hint">
                                              <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                              <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                新增条目
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                        </Fragment>
                                      );
                                      });
                                    })()}
                                    {reviewOpenXmlDocument.footers.map((footer, index) => (
                                      <div className="word-review-footer-text" key={`footer-${index}`}>
                                        {footer}
                                      </div>
                                    ))}
                                  </div>
                                ) : reviewDisplayChunks.length ? (
                                  <div className="word-review-document fallback-mode">
                                    <Alert
                                      type="warning"
                                      showIcon
                                      message="原文审阅结构暂未返回，已使用矩阵来源原文连续展示。"
                                      className="review-fallback-alert"
                                    />
                                    {reviewDisplayChunks.map((chunk) => {
                                      const highlights = reviewHighlightByChunkId.get(chunk.id) ?? [];
                                      const uncovered = uncoveredChunkMap.get(chunk.id);
                                      const blockActive = highlights.some((highlight) => highlight.item_id === activeReviewItemId);
                                      const blockLocating = highlights.some((highlight) => highlight.item_id === locatingReviewItemId);
                                      return (
                                        <div
                                          key={chunk.id}
                                          id={`review-block-${chunk.id}`}
                                          className={`word-review-block ${blockActive ? "active" : ""} ${blockLocating ? "locating" : ""}`}
                                          onMouseUp={(event) => handleReviewChunkMouseUp(event, chunk)}
                                          onClick={() => focusReviewChunk(chunk.id)}
                                        >
                                          {chunk.heading_path && <div className="word-review-fallback-heading">{chunk.heading_path}</div>}
                                          <p>{renderHighlightedText(chunk.content_text, highlights, `fallback-${chunk.id}`)}</p>
                                          {uncovered && (
                                            <div className="review-uncovered-hint">
                                              <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                              <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                新增条目
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可展示的原文内容" />
                                )}
                              </Spin>
                            </div>
                            <div className="review-item-pane" ref={reviewItemPaneRef}>
                              <div className="review-pane-title">
                                <Text strong>合规条目队列</Text>
                                <Space size={6}>
                                  <Badge count={matrixReviewRows.length} showZero color="#2563eb" />
                                  {matrixReviewFilter !== "all" && (
                                    <Text type="secondary">共 {matrixRows.length} 条</Text>
                                  )}
                                </Space>
                              </div>
                              {matrixReviewRows.length > reviewQueuePageSize && (
                                <Pagination
                                  className="review-queue-pagination"
                                  size="small"
                                  current={reviewQueuePage}
                                  pageSize={reviewQueuePageSize}
                                  total={matrixReviewRows.length}
                                  showSizeChanger
                                  pageSizeOptions={["25", "50", "100"]}
                                  showTotal={(total) => `共 ${total} 条`}
                                  onChange={(page, pageSize) => {
                                    setReviewQueuePage(page);
                                    setReviewQueuePageSize(pageSize);
                                  }}
                                />
                              )}
                              {matrixReviewRows.length ? (
                                pagedMatrixReviewRows.map((row) => {
                                  const isActive = row.key === activeReviewItemId;
                                  const duplicateGroups = duplicateGroupByItemId.get(row.key) ?? [];
                                  const reviewDetail = (
                                    <Space direction="vertical" size={8} className="review-popover">
                                      <Text strong>{row.requirement}</Text>
                                      {row.raw.source_quote && <Text type="secondary">来源摘录：{row.raw.source_quote}</Text>}
                                      {row.raw.classification_reason && <Text type="secondary">分类理由：{row.raw.classification_reason}</Text>}
                                      {row.raw.split_reason && <Text type="secondary">拆分理由：{row.raw.split_reason}</Text>}
                                      {row.raw.review_hint && <Alert type="warning" showIcon message={row.raw.review_hint} />}
                                      {duplicateGroups.length > 0 && (
                                        <Space wrap>
                                          {duplicateGroups.map((group) => (
                                            <Tag key={group.group_key} color={group.group_type === "confirmed" ? "green" : "blue"}>
                                              关联 x{group.item_count} · {group.group_type === "confirmed" ? "已确认" : "疑似"}
                                            </Tag>
                                          ))}
                                        </Space>
                                      )}
                                    </Space>
                                  );
                                  return (
                                    <div
                                      key={row.key}
                                      data-review-item-id={row.key}
                                      className={`review-item-card review-risk-${row.riskCode} ${row.statusCode === "confirmed" ? "confirmed" : ""} ${isActive ? "active" : ""}`}
                                      onClick={() => focusReviewRow(row)}
                                    >
                                      <div className="review-item-top">
                                        <Space size={6} wrap>
                                          <Tag color={riskColor(row.riskCode)}>{row.risk}</Tag>
                                          <Tag>{row.chapter}</Tag>
                                          {row.mandatory && <Tag color="red">强制</Tag>}
                                          {row.raw.needs_human_review && <Tag color="orange">需复核</Tag>}
                                          {row.enterpriseEvidenceCount === 0 && <Tag color="gold">缺证据</Tag>}
                                          {(row.raw.duplicate_group_count > 1 || duplicateGroups.length > 0) && (
                                            <Tag color={row.raw.duplicate_group_id ? "green" : "blue"} icon={<BranchesOutlined />}>
                                              关联 x{Math.max(row.raw.duplicate_group_count, duplicateGroups[0]?.item_count ?? 0)}
                                            </Tag>
                                          )}
                                        </Space>
                                        <Tag color={statusColor(row.statusCode)}>{row.status}</Tag>
                                      </div>
                                      <Popover content={reviewDetail} trigger="hover" mouseEnterDelay={0.15}>
                                        <Text strong className="review-item-summary">
                                          {truncateText(row.requirement, 44)}
                                        </Text>
                                      </Popover>
                                      <Text type="secondary" className="review-item-reason">
                                        {row.raw.review_hint ||
                                          row.raw.classification_reason ||
                                          explanationText(row.raw.rule_explanation, "risk_reason")}
                                      </Text>
                                      <Space size={6} wrap>
                                        <Button size="small" onClick={(event) => { event.stopPropagation(); focusReviewRow(row); }}>
                                          定位原文
                                        </Button>
                                        <Button size="small" onClick={(event) => { event.stopPropagation(); setSourceDrawer(row); }}>
                                          来源详情
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            openEditDraft(row);
                                          }}
                                        >
                                          编辑
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            void openSimilarCandidates(row);
                                          }}
                                        >
                                          查找相似
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            void handleConfirmDuplicateGroup(row);
                                          }}
                                        >
                                          确认关联
                                        </Button>
                                        {row.raw.duplicate_group_id && (
                                          <>
                                            <Button
                                              size="small"
                                              onClick={(event) => {
                                                event.stopPropagation();
                                                void handleUnlinkDuplicateGroup(row);
                                              }}
                                            >
                                              解除联动
                                            </Button>
                                            <Button
                                              size="small"
                                              onClick={(event) => {
                                                event.stopPropagation();
                                                void handleSplitDuplicateGroup(row);
                                              }}
                                            >
                                              拆分
                                            </Button>
                                          </>
                                        )}
                                        <Button
                                          size="small"
                                          type="primary"
                                          disabled={row.statusCode === "confirmed"}
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            handleConfirmItem(row);
                                          }}
                                        >
                                          确认
                                        </Button>
                                      </Space>
                                    </div>
                                  );
                                })
                              ) : (
                                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前筛选条件下暂无条目" />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  },
                  {
                    key: "technical",
                    label: "技术响应",
                    children: (
                      <div className="workspace-panel evidence-work-panel">
                        <div className="tab-intro">
                          <div>
                            <Text strong>技术响应预览</Text>
                            <p>当前版本只整理技术要求、评分项、风险和待确认项；产品选型、示意图和技术标章节将在 MVP1.1 完成。</p>
                          </div>
                          <Tag color={technicalRows.length ? "blue" : "default"}>
                            {technicalRows.length ? `${technicalRows.length} 项` : "暂无明确技术项"}
                          </Tag>
                        </div>
                        <Table<MatrixRow>
                          size="middle"
                          pagination={LARGE_TABLE_PAGINATION}
                          rowKey="key"
                          dataSource={technicalRows}
                          locale={{
                            emptyText: (
                              <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description="暂无技术响应项；请先生成合规矩阵"
                              />
                            )
                          }}
                          columns={[
                            {
                              title: "技术/评分要求",
                              dataIndex: "requirement",
                              render: (value: string) => (
                                <Tooltip title={value}>
                                  <span className="clamped-cell">{value}</span>
                                </Tooltip>
                              )
                            },
                            {
                              title: "类型",
                              dataIndex: "chapter",
                              width: 120,
                              render: (value: string) => <Tag>{value}</Tag>
                            },
                            {
                              title: "状态",
                              dataIndex: "status",
                              width: 110,
                              render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>
                            },
                            {
                              title: "风险",
                              dataIndex: "risk",
                              width: 90,
                              render: (value: string, record) => (
                                <Tooltip title={explanationText(record.raw.rule_explanation, "risk_reason")}>
                                  <Tag color={riskColor(value)}>{value}</Tag>
                                </Tooltip>
                              )
                            },
                            {
                              title: "来源",
                              dataIndex: "source",
                              width: 220,
                              render: (value: string, record) => (
                                <Button type="link" className="table-link-text" onClick={() => setSourceDrawer(record)}>
                                  {value}
                                </Button>
                              )
                            },
                            {
                              title: "处理",
                              dataIndex: "actions",
                              width: 180,
                              render: (_: unknown, record) => (
                                <Space size={6}>
                                  <Button size="small" onClick={() => setSourceDrawer(record)}>
                                    原文
                                  </Button>
                                  <Button size="small" onClick={() => locateMatrixRow(record.key)}>
                                    定位矩阵
                                  </Button>
                                </Space>
                              )
                            }
                          ]}
                        />
                      </div>
                    )
                  },
                  {
                    key: "chapter",
                    label: "商务标章节",
                    children: (
                      <div className="workspace-panel editor-panel">
                        <div className="section-outline">
                          <div className="outline-title">
                            <Text strong>章节大纲</Text>
                            <Tag>{businessDraftChapters.length}</Tag>
                          </div>
                          {businessDraftChapters.map((chapter, index) => (
                            <button
                              key={chapter.id}
                              className={chapter.id === selectedDraftChapterId ? "outline-row active" : "outline-row"}
                              onClick={() => setSelectedDraftChapterId(chapter.id)}
                            >
                              {index + 1}. {chapter.title}
                            </button>
                          ))}
                          {!businessDraftChapters.length && (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description={
                                mvp13DraftWorkflowAvailable
                                  ? "尚未生成草稿"
                                  : "MVP1.2 仅确认 ContextPack；章节草稿将在 MVP1.3 生成"
                              }
                            />
                          )}
                        </div>
                        <div className="draft-editor">
                          <div className="context-pack-strip">
                            <div className="context-pack-main">
                              <Space wrap>
                                <Text strong>ContextPack</Text>
                                <Tag color={preflightColor(contextPackSource?.readiness_status ?? "warn")}>
                                  {contextPackSource ? preflightLabel(contextPackSource.readiness_status) : "未生成"}
                                </Tag>
                                <Tag color="blue">{contextPackOutlineSections.length} 章计划</Tag>
                                <Tag color={contextPackReadinessSummary.missingEvidence ? "red" : "green"}>
                                  缺证据项 {contextPackReadinessSummary.missingEvidence}
                                </Tag>
                                <Tag color={contextPackReadinessSummary.missingFacts ? "gold" : "green"}>
                                  待补事实 {contextPackReadinessSummary.missingFacts}
                                </Tag>
                                {coverageReview && (
                                  <Tag color={preflightColor(coverageReview.status)}>
                                    覆盖检查（MVP1.3）{preflightLabel(coverageReview.status)}
                                  </Tag>
                                )}
                                {coverageReview && (
                                  <Tag color={summaryNumber(coverageReview.summary_json, "quality_score") >= 85 ? "green" : "gold"}>
                                    1.3 质量分 {summaryNumber(coverageReview.summary_json, "quality_score")}
                                  </Tag>
                                )}
                                {contextPackQualificationGate.status !== "pass" && (
                                  <Tag color={preflightColor(contextPackQualificationGate.status)}>
                                    {contextPackQualificationGate.message}
                                  </Tag>
                                )}
                              </Space>
                              {contextPackChecks.length > 0 ? (
                                <div className="context-pack-checks">
                                  {contextPackChecks.slice(0, 3).map((check, index) => (
                                    <Tag
                                      key={`${String(check.code ?? index)}-${index}`}
                                      color={preflightColor(String(check.status ?? "warn"))}
                                    >
                                      {String(check.summary ?? check.code ?? "待处理")}
                                    </Tag>
                                  ))}
                                </div>
                              ) : (
                                <Text type="secondary">生成前会固定项目字段、矩阵项、证据、缺项和章节范围。</Text>
                              )}
                              {blockingContextPackChecks.length > 0 && (
                                <div className="context-pack-blockers">
                                  {blockingContextPackChecks.slice(0, 4).map((check, index) => {
                                    return (
                                      <div className="context-pack-blocker" key={`${String(check.code ?? index)}-blocker`}>
                                        <Tag color={preflightColor(String(check.status ?? "warn"))}>
                                          {String(check.summary ?? check.code ?? "待处理")}
                                        </Tag>
                                        <Text type="secondary">{String(check.action ?? "按提示处理后重新确认 ContextPack。")}</Text>
                                        <Button size="small" onClick={() => handleContextPackCheckAction(check)}>
                                          {contextPackCheckActionText(check)}
                                        </Button>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                              {businessDraftGenerationTaskId && (
                                <div className="context-pack-task-progress">
                                  <Space wrap>
                                    <Text strong>草稿生成任务</Text>
                                    <Tag color={businessDraftGenerationActive ? "blue" : businessDraftGenerationTask?.status === "succeeded" ? "green" : "red"}>
                                      {businessDraftGenerationStatusText}
                                    </Tag>
                                    {businessDraftGenerationTask?.error_message && (
                                      <Text type="danger">{businessDraftGenerationTask.error_message}</Text>
                                    )}
                                  </Space>
                                  <Progress percent={businessDraftGenerationProgress} size="small" />
                                </div>
                              )}
                            </div>
                            <Space wrap>
                              <Button loading={loadingContextPack} onClick={handlePreviewContextPack}>
                                预览
                              </Button>
                              <Tooltip title={canConfirmContextPack ? "" : contextPackConfirmDisabledReason}>
                                <span>
                                  <Button
                                    loading={loadingContextPack}
                                    disabled={!canConfirmContextPack}
                                    onClick={handleCreateContextPack}
                                  >
                                    确认 ContextPack
                                  </Button>
                                </span>
                              </Tooltip>
                              <Tooltip
                                title={
                                  canGenerateContextPackDraft
                                    ? ""
                                    : activeContextPack
                                      ? contextPackDraftGenerationTip
                                      : "先确认 ContextPack。"
                                }
                              >
                                <span>
                                  <Button
                                    type="primary"
                                    icon={<RobotOutlined />}
                                    loading={loadingBusinessDraft || businessDraftGenerationActive}
                                    disabled={!canGenerateContextPackDraft || businessDraftGenerationActive}
                                    onClick={confirmContextPackDraftGeneration}
                                  >
                                    草稿生成（MVP1.3）
                                  </Button>
                                </span>
                              </Tooltip>
                              <Tooltip title="MVP1.3 将在生成 DraftBlock 后执行覆盖检查。">
                                <span>
                                  <Button
                                    loading={loadingContextPack}
                                    disabled
                                    onClick={handleRunContextPackCoverageReview}
                                  >
                                    覆盖检查（MVP1.3）
                                  </Button>
                                </span>
                              </Tooltip>
                            </Space>
                          </div>
                          <div className="draft-toolbar">
                            <Space wrap>
                              <Button
                                type="primary"
                                icon={<RobotOutlined />}
                                loading={loadingBusinessDraft || businessDraftGenerationActive}
                                disabled={businessDraftGenerationActive || !mvp13DraftWorkflowAvailable || Boolean(activeContextPack)}
                                onClick={() =>
                                  activeContextPack
                                    ? confirmContextPackDraftGeneration()
                                    : qualificationDecisionConfirmed && qualificationDecisionIsNoGo && !businessDraftChapters.length
                                    ? confirmNoGoRiskAcceptance(confirmDraftGeneration)
                                    : confirmDraftGeneration()
                                }
                              >
                                {!mvp13DraftWorkflowAvailable
                                  ? "草稿生成（MVP1.3）"
                                  : activeContextPack
                                  ? "草稿生成（MVP1.3）"
                                  : qualificationDecisionConfirmed && qualificationDecisionIsNoGo && !businessDraftChapters.length
                                  ? "风险接受后生成草稿"
                                  : "生成商务标草稿"}
                              </Button>
                              <Button
                                icon={<SafetyCertificateOutlined />}
                                disabled={!mvp13DraftWorkflowAvailable || !selectedDraftChapter}
                                loading={savingBusinessDraft}
                                onClick={handleRunDraftFactCheck}
                              >
                                事实校验（MVP1.3）
                              </Button>
                              <Button
                                icon={<DownloadOutlined />}
                                disabled={!mvp13DraftWorkflowAvailable || !businessDraftChapters.length}
                                loading={exportingWord}
                                onClick={handleExportBusinessWord}
                              >
                                导出 Word（MVP1.3）
                              </Button>
                            </Space>
                            {selectedDraftChapter && (
                              <Space wrap>
                                <Tag color={chapterStatusLabels[selectedDraftChapter.status] === "已确认" ? "green" : "gold"}>
                                  {chapterStatusLabels[selectedDraftChapter.status] ?? selectedDraftChapter.status}
                                </Tag>
                                <Tag color={selectedDraftChapter.fact_check_status === "verified" ? "green" : "red"}>
                                  {selectedDraftChapter.fact_check_status === "verified" ? "事实已核验" : "存在待核验事实"}
                                </Tag>
                                <Text type="secondary">v{selectedDraftChapter.version_no}</Text>
                              </Space>
                            )}
                          </div>
                          {selectedDraftChapter ? (
                            <>
                              <div className="draft-meta">
                                <Text strong>{selectedDraftChapter.title}</Text>
                                <Space wrap>
                                  <Tag color="blue">
                                    已绑定证据 {summaryNumber(selectedDraftChapter.evidence_summary_json, "bound_evidence_count")}
                                  </Tag>
                                  <Tag color={summaryNumber(selectedDraftChapter.evidence_summary_json, "unbound_item_count") ? "red" : "green"}>
                                    待补证 {summaryNumber(selectedDraftChapter.evidence_summary_json, "unbound_item_count")}
                                  </Tag>
                                </Space>
                              </div>
                              {selectedDraftChapter.fact_checks.some((check) => check.check_status !== "verified") && (
                                <Alert
                                  type="warning"
                                  showIcon
                                  className="draft-fact-alert"
                                  message="草稿存在待确认事实"
                                  description={`无法验证 ${selectedDraftChapter.fact_checks.filter((check) => check.check_status === "unverified").length} 项，风险提示 ${selectedDraftChapter.fact_checks.filter((check) => check.check_status === "warning").length} 项。导出前请人工复核。`}
                                />
                              )}
                              <TextArea
                                value={draftEditorValue}
                                readOnly={!mvp13DraftWorkflowAvailable}
                                onChange={(event) => {
                                  if (mvp13DraftWorkflowAvailable) setDraftEditorValue(event.target.value);
                                }}
                                autoSize={{ minRows: 12, maxRows: 18 }}
                              />
                              <div className="draft-action-row">
                                <Button
                                  type="primary"
                                  loading={savingBusinessDraft}
                                  disabled={!mvp13DraftWorkflowAvailable || draftEditorValue === selectedDraftChapter.content_text}
                                  onClick={handleSaveBusinessDraftChapter}
                                >
                                  {mvp13DraftWorkflowAvailable ? "保存修改" : "保存修改（MVP1.3）"}
                                </Button>
                                <Text type="secondary">
                                  {mvp13DraftWorkflowAvailable
                                    ? "保存会重新校验证书编号、金额、日期等事实，并替换无法验证内容。"
                                    : "当前 MVP1.2 只确认 ContextPack；历史草稿内容仅供查看。"}
                                </Text>
                              </div>
                              {selectedDraftDiff && (
                                <div className="draft-diff-card">
                                  <div className="draft-diff-head">
                                    <Space wrap>
                                      <Text strong>最近修改对比</Text>
                                      <Tag color={selectedDraftDiff.action === "business_draft.block_updated" ? "blue" : "purple"}>
                                        {selectedDraftDiff.action === "business_draft.block_updated" ? "Block" : "章节"}
                                      </Tag>
                                      <Tag color={selectedDraftDiff.delta >= 0 ? "green" : "gold"}>
                                        {selectedDraftDiff.delta >= 0 ? "+" : ""}
                                        {selectedDraftDiff.delta} 字
                                      </Tag>
                                    </Space>
                                    <Text type="secondary">{formatDateTime(selectedDraftDiff.createdAt)}</Text>
                                  </div>
                                  <div className="draft-diff-grid">
                                    <div>
                                      <Text type="secondary">修改前</Text>
                                      <p>{truncateText(selectedDraftDiff.beforeText || "无旧内容", 180)}</p>
                                    </div>
                                    <div>
                                      <Text type="secondary">修改后</Text>
                                      <p>{truncateText(selectedDraftDiff.afterText || "无新内容", 180)}</p>
                                    </div>
                                  </div>
                                  {selectedDraftDiff.reason && (
                                    <Text type="secondary">原因：{selectedDraftDiff.reason}</Text>
                                  )}
                                </div>
                              )}
                              {selectedChapterBlocks.length > 0 && (
                                <div className="draft-block-list">
                                  <div className="draft-block-title">
                                    <Text strong>结构化 block 审阅</Text>
                                    <Tag>{selectedChapterBlocks.length}</Tag>
                                  </div>
                                  {selectedChapterBlocks.map((block) => {
                                    const complianceItemIds = draftBlockLinkIds(block, "compliance_item_ids");
                                    const evidenceBindingIds = draftBlockLinkIds(block, "evidence_binding_ids");
                                    const linkedRows = complianceItemIds
                                      .map((itemId) => matrixRowsById.get(itemId))
                                      .filter((row): row is MatrixRow => Boolean(row));
                                    return (
                                      <div
                                        className={`draft-block-item ${activeDraftBlockId === block.id ? "active" : ""}`}
                                        data-draft-block-id={block.id}
                                        key={block.id}
                                      >
                                        <div>
                                          <Space wrap>
                                            <Tag color={draftBlockStatusColors[block.review_status] ?? "default"}>
                                              {draftBlockStatusLabels[block.review_status] ?? block.review_status}
                                            </Tag>
                                            <Tag color="blue">
                                              条款 {complianceItemIds.length}
                                            </Tag>
                                            <Tag color="green">
                                              证据 {evidenceBindingIds.length}
                                            </Tag>
                                          </Space>
                                          <p>{block.content_text}</p>
                                          {linkedRows.length > 0 && (
                                            <div className="draft-block-trace">
                                              {linkedRows.slice(0, 4).map((row, index) => (
                                                <Tooltip title={row.requirement} key={`${block.id}-${row.key}`}>
                                                  <Button
                                                    size="small"
                                                    className="draft-block-trace-button"
                                                    onClick={() => locateMatrixRow(row.key)}
                                                  >
                                                    条款 {index + 1}
                                                  </Button>
                                                </Tooltip>
                                              ))}
                                              <Button
                                                size="small"
                                                onClick={() => {
                                                  setSourceDrawer(linkedRows[0]);
                                                }}
                                              >
                                                原文
                                              </Button>
                                              <Button
                                                size="small"
                                                onClick={() => {
                                                  setViewMode("workspace");
                                                  setActiveTab("review");
                                                  setWorkspaceNode("review");
                                                  window.setTimeout(() => focusReviewRow(linkedRows[0]), 100);
                                                }}
                                              >
                                                审阅台
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                        <Space wrap>
                                          <Button
                                            size="small"
                                            loading={savingBusinessDraft}
                                            disabled={!mvp13DraftWorkflowAvailable}
                                            onClick={() => openEditDraftBlock(block)}
                                          >
                                            {mvp13DraftWorkflowAvailable ? "编辑" : "编辑（MVP1.3）"}
                                          </Button>
                                          <Button
                                            size="small"
                                            disabled={!mvp13DraftWorkflowAvailable || block.review_status === "approved"}
                                            loading={savingBusinessDraft}
                                            onClick={() =>
                                              handleUpdateDraftBlockStatus(block, "approved", "人工审阅通过该结构化 block")
                                            }
                                          >
                                            通过
                                          </Button>
                                          <Button
                                            size="small"
                                            danger
                                            disabled={block.review_status === "needs_evidence"}
                                            loading={savingBusinessDraft}
                                            onClick={() =>
                                              handleUpdateDraftBlockStatus(block, "needs_evidence", "人工标记该 block 仍需补充证据")
                                            }
                                          >
                                            需补证
                                          </Button>
                                        </Space>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                              <div className="fact-check-list">
                                <Text strong>事实性校验</Text>
                                {selectedDraftChapter.fact_checks.map((check) => (
                                  <div className="fact-check-item" key={check.id}>
                                    <Tag color={check.check_status === "verified" ? "green" : "red"}>
                                      {factCheckLabels[check.check_status] ?? check.check_status}
                                    </Tag>
                                    <Text>{check.fact_text}</Text>
                                    <Text type="secondary">{check.detail}</Text>
                                  </div>
                                ))}
                              </div>
                            </>
                          ) : (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description={
                                mvp13DraftWorkflowAvailable
                                  ? "生成后可在这里编辑商务标章节草稿"
                                  : "MVP1.3 将基于已确认 ContextPack 生成章节草稿"
                              }
                            />
                          )}
                        </div>
                      </div>
                    )
                  },
                  {
                    key: "approval",
                    label: "审批任务",
                    children: (
                      <div className="workspace-panel approval-list">
                        <div className="approval-toolbar">
                          <Text strong>人工关口</Text>
                          <Button onClick={confirmSubmit}>创建提交确认</Button>
                        </div>
                        {approvalTasks.map((task) => (
                            <div className="approval-item" key={task.id}>
                              <WarningOutlined className={task.status === "rejected" ? "danger-icon" : "info-icon"} />
                              <div>
                                <Space wrap>
                                  <Text strong>{task.title}</Text>
                                  <Tag>{approvalTaskTypeLabels[task.task_type] ?? task.task_type}</Tag>
                                  <Tag color={task.status === "approved" ? "green" : task.status === "rejected" ? "red" : "gold"}>
                                    {approvalStatusLabels[task.status] ?? task.status}
                                  </Tag>
                                </Space>
                                <p>
                                  {task.description ?? "等待责任人处理"}；创建时间：{formatDateTime(task.created_at)}
                                </p>
                                {blockingSummary(task.evidence_snapshot_json).length > 0 && (
                                  <div className="approval-blockers">
                                    {blockingSummary(task.evidence_snapshot_json).slice(0, 3).map((item) => (
                                      <Tag key={`${task.id}-${String(item.code)}`} color={preflightColor(String(item.status))}>
                                        {String(item.title)}：{String(item.message)}
                                      </Tag>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <Space>
                                <Button
                                  size="small"
                                  type="primary"
                                  disabled={task.status !== "pending"}
                                  loading={approvalBusyId === task.id}
                                  onClick={() => handleDecideApprovalTask(task, "approve")}
                                >
                                  通过
                                </Button>
                                <Button
                                  size="small"
                                  danger
                                  disabled={task.status !== "pending"}
                                  loading={approvalBusyId === task.id}
                                  onClick={() => handleDecideApprovalTask(task, "reject")}
                                >
                                  退回
                                </Button>
                              </Space>
                            </div>
                          ))}
                        {!approvalTasks.length && (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无审批任务" />
                        )}
                      </div>
                    )
                  }
                ]}
              />
            </Content>

            <aside className={assistantCollapsed ? "assistant collapsed" : "assistant"}>
              <div className="assistant-header">
                {!assistantCollapsed && (
                  <Space>
                    <Avatar icon={<RobotOutlined />} className="assistant-avatar" />
                    <div>
                      <Text strong>流程助手</Text>
                      <div className="assistant-subtitle">MVP1.0 负责流程导航，真实问答顺延 1.1</div>
                    </div>
                  </Space>
                )}
                <Tooltip title={assistantCollapsed ? "展开助手" : "折叠助手"}>
                  <Button
                    type="text"
                    icon={assistantCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                    onClick={() => setAssistantCollapsed((value) => !value)}
                  />
                </Tooltip>
              </div>

              {assistantCollapsed ? (
                <div className="assistant-rail">
                  <Tooltip title="流程助手">
                    <Button type="primary" icon={<RobotOutlined />} />
                  </Tooltip>
                  <Tooltip title="主动提醒">
                    <Badge dot>
                      <Button icon={<CommentOutlined />} />
                    </Badge>
                  </Tooltip>
                </div>
              ) : (
                <>
                  <div className="assistant-feed">
                    {recommendedStep && (
                      <div className="assistant-message primary-next">
                        <div className="message-title-row">
                          <Text strong>当前建议：{recommendedStep.title}</Text>
                          <Tag color={workflowStatusColor(recommendedStep.status)}>{recommendedStep.statusText}</Tag>
                        </div>
                        <p>{recommendedStep.reason}</p>
                        <Button type="primary" onClick={() => runWorkflowPrimaryAction(recommendedStep.key)}>
                          {recommendedStep.actionText}
                        </Button>
                      </div>
                    )}

                    {!focusQualityAssistant && (
                      <div className="quick-prompts compact">
                        {quickPrompts.map((prompt) => (
                          <Button size="small" key={prompt} onClick={() => handleQuickPrompt(prompt)}>
                            {prompt}
                          </Button>
                        ))}
                      </div>
                    )}

                    {!focusQualityAssistant &&
                      assistantMessages.map((item) => (
                        <div className="assistant-message" key={item.key}>
                          <div className="message-title-row">
                            <Text strong>{item.title}</Text>
                            <Button type="text" size="small" icon={<CloseOutlined />} />
                          </div>
                          <p>{item.content}</p>
                          <Space size={8}>
                            <Button
                              size="small"
                              type="primary"
                              onClick={() => handleAssistantMessageAction(item)}
                            >
                              {item.action}
                            </Button>
                            <Button size="small">转为任务</Button>
                          </Space>
                        </div>
                      ))}

                    <div className="operation-log">
                      <Text strong>操作日志</Text>
                      {displayedLogs.length ? (
                        displayedLogs.map((log, index) => (
                          <div className="log-line" key={`${log}-${index}`}>
                            {log}
                          </div>
                        ))
                      ) : (
                        <Text type="secondary">暂无操作日志</Text>
                      )}
                    </div>
                  </div>

                  <div className="assistant-input">
                    <TextArea
                      placeholder="MVP1.1 将支持上下文问答；当前可使用上方快捷入口处理流程。"
                      autoSize={{ minRows: 3, maxRows: 5 }}
                    />
                    <div className="assistant-actions">
                      <Text type="secondary">自然语言 Agent 问答为 MVP1.1 预留，当前不触发自动执行。</Text>
                      <Button
                        type="primary"
                        icon={<SendOutlined />}
                        onClick={() => appendLog("记录自然语言请求；真实上下文问答将在 MVP1.1 接入")}
                      >
                        发送
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </aside>
          </Layout>
        )}
      </Layout>
      <Modal
        title="新建投标项目"
        open={newProjectOpen}
        width={760}
        okText={savingProject ? "创建中..." : projectCreateMode === "manual" ? "创建项目" : "确认导入并创建"}
        cancelText="取消"
        confirmLoading={savingProject}
        okButtonProps={{ disabled: savingProject || importingProjectDraft || (projectCreateMode !== "manual" && !projectImportDraft) }}
        onOk={handleCreateProject}
        onCancel={() => {
          if (!savingProject) setNewProjectOpen(false);
        }}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          {savingProject && projectCreateMode !== "manual" && (
            <Alert
              type="info"
              showIcon
              message="正在创建项目"
              description="请勿重复点击。项目创建成功后会自动进入工作台，文件解析和矩阵生成将在后台继续处理。"
            />
          )}
          <Tabs
            activeKey={projectCreateMode}
            tabBarExtraContent={savingProject ? <Tag color="processing">创建中</Tag> : null}
            onChange={(key) => {
              if (savingProject) return;
              setProjectCreateMode(key as ProjectCreateMode);
              setProjectImportDraft(null);
            }}
            items={[
              {
                key: "manual",
                label: "手工新建",
                children: <Text type="secondary">录入项目基础信息后创建空项目。</Text>
              },
              {
                key: "file",
                label: "从文件导入",
                children: (
                  <Space direction="vertical" size={10} className="import-upload-panel">
                    <Upload
                      maxCount={1}
                      showUploadList={false}
                      accept=".doc,.docx,.pdf,.html,.htm"
                      disabled={savingProject}
                      beforeUpload={handleImportDraftFile}
                    >
                      <Button type="primary" icon={<CloudUploadOutlined />} loading={importingProjectDraft} disabled={savingProject}>
                        导入招标文件
                      </Button>
                    </Upload>
                    <Text type="secondary">
                      支持 Word、可复制 PDF 和网页 HTML。外部文件按非可信输入处理，识别结果必须人工确认。
                    </Text>
                  </Space>
                )
              },
              {
                key: "url",
                label: "从网页导入",
                children: (
                  <Space direction="vertical" size={10} style={{ width: "100%" }}>
                    <Space.Compact style={{ width: "100%" }}>
                      <Input
                        placeholder="公告网页或附件 URL（按非可信输入处理）"
                        value={importUrl}
                        disabled={savingProject}
                        onChange={(event) => setImportUrl(event.target.value)}
                      />
                      <Input
                        placeholder="资源站点"
                        value={importUrlSite}
                        disabled={savingProject}
                        onChange={(event) => setImportUrlSite(event.target.value)}
                        style={{ width: 160 }}
                      />
                      <Button
                        type="primary"
                        icon={<LinkOutlined />}
                        loading={importingProjectDraft}
                        disabled={savingProject}
                        onClick={handleImportDraftUrl}
                      >
                        识别
                      </Button>
                    </Space.Compact>
                  </Space>
                )
              }
            ]}
          />

          {projectImportDraft && (
            <div className="import-draft-panel">
              <div className="import-draft-title">
                <Text strong>导入识别结果</Text>
                <Tag color="blue">{projectImportDraft.source.original_filename}</Tag>
              </div>
              {projectImportDraft.warnings.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message={projectImportDraft.warnings.join("；")}
                />
              )}
              <div className="import-draft-summary">
                <div>
                  <Text type="secondary">项目名称</Text>
                  <strong>{projectImportDraft.project.name}</strong>
                </div>
                <div>
                  <Text type="secondary">采购人</Text>
                  <strong>{projectImportDraft.project.purchaser || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">代理机构</Text>
                  <strong>{projectImportDraft.project.agency || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">预算金额</Text>
                  <strong>{projectImportDraft.project.budget_amount || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">标段</Text>
                  <strong>{projectImportDraft.sections.map((section) => section.name).join("、")}</strong>
                </div>
                <div>
                  <Text type="secondary">投标截止时间</Text>
                  <strong>{formatDateTime(projectImportDraft.project.bid_deadline_at)}</strong>
                </div>
              </div>
              <div className="import-confidence">
                {Object.entries(projectImportDraft.confidence).map(([key, value]) => (
                  <Tag key={key} color={value >= 0.7 ? "green" : value > 0 ? "gold" : "default"}>
                    {key} {Math.round(value * 100)}%
                  </Tag>
                ))}
              </div>
              <div className="import-preview-text">{projectImportDraft.preview_text}</div>
            </div>
          )}

          {projectCreateMode === "manual" && (
            <>
              <Input
                placeholder="项目名称"
                value={newProjectDraft.name}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, name: event.target.value }))
                }
              />
              <Input
                placeholder="采购人"
                value={newProjectDraft.purchaser}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, purchaser: event.target.value }))
                }
              />
              <Input
                placeholder="代理机构"
                value={newProjectDraft.agency}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, agency: event.target.value }))
                }
              />
              <Space.Compact style={{ width: "100%" }}>
                <Input
                  placeholder="预算金额"
                  value={newProjectDraft.budgetAmount}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, budgetAmount: event.target.value }))
                  }
                />
                <Input
                  placeholder="标段名称"
                  value={newProjectDraft.sectionName}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, sectionName: event.target.value }))
                  }
                />
              </Space.Compact>
              <Space.Compact style={{ width: "100%" }}>
                <Input
                  placeholder="地区编码"
                  value={newProjectDraft.regionCode}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, regionCode: event.target.value }))
                  }
                />
                <Input
                  placeholder="行业编码"
                  value={newProjectDraft.industryCode}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, industryCode: event.target.value }))
                  }
                />
              </Space.Compact>
              <Input
                placeholder="公告链接"
                value={newProjectDraft.noticeUrl}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, noticeUrl: event.target.value }))
                }
              />
              <DatePicker
                showTime
                style={{ width: "100%" }}
                placeholder="投标截止时间"
                value={newProjectDraft.bidDeadlineAt ? dayjs(newProjectDraft.bidDeadlineAt) : null}
                onChange={(value) =>
                  setNewProjectDraft((draft) => ({
                    ...draft,
                    bidDeadlineAt: value ? value.toISOString() : null
                  }))
                }
              />
            </>
          )}
        </Space>
      </Modal>
      <Modal
        title="项目关键信息"
        open={keyInfoModalOpen}
        width={760}
        okText="保存并确认"
        cancelText="取消"
        confirmLoading={savingProject}
        onOk={handleSaveKeyInfo}
        onCancel={() => setKeyInfoModalOpen(false)}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Alert
            type={missingKeyInfo.length ? "warning" : "info"}
            showIcon
            message={missingKeyInfo.length ? `仍缺少：${missingKeyInfo.join("、")}` : "关键字段已填写"}
            description="这些字段会进入提交前核验、审批说明和导出复盘。复杂的保证金、工期、质量标准等字段暂由合规矩阵承载。"
          />
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="项目名称"
              value={keyInfoDraft.projectName}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, projectName: event.target.value }))}
            />
            <Input
              placeholder="标段名称"
              value={keyInfoDraft.sectionName}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, sectionName: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="招标人/采购人"
              value={keyInfoDraft.purchaser}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, purchaser: event.target.value }))}
            />
            <Input
              placeholder="代理机构"
              value={keyInfoDraft.agency}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, agency: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="项目预算/限价"
              value={keyInfoDraft.budgetAmount}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, budgetAmount: event.target.value }))}
            />
            <Input
              placeholder="标段预算/限价"
              value={keyInfoDraft.sectionBudgetAmount}
              onChange={(event) =>
                setKeyInfoDraft((draft) => ({ ...draft, sectionBudgetAmount: event.target.value }))
              }
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="地区编码"
              value={keyInfoDraft.regionCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, regionCode: event.target.value }))}
            />
            <Input
              placeholder="行业编码"
              value={keyInfoDraft.industryCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, industryCode: event.target.value }))}
            />
            <Input
              placeholder="标段编号"
              value={keyInfoDraft.sectionCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, sectionCode: event.target.value }))}
            />
          </Space.Compact>
          <Input
            placeholder="公告链接"
            value={keyInfoDraft.noticeUrl}
            onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, noticeUrl: event.target.value }))}
          />
          <Space.Compact style={{ width: "100%" }}>
            <DatePicker
              showTime
              style={{ width: "50%" }}
              placeholder="项目投标截止时间"
              value={keyInfoDraft.bidDeadlineAt ? dayjs(keyInfoDraft.bidDeadlineAt) : null}
              onChange={(value) =>
                setKeyInfoDraft((draft) => ({ ...draft, bidDeadlineAt: value ? value.toISOString() : null }))
              }
            />
            <DatePicker
              showTime
              style={{ width: "50%" }}
              placeholder="标段投标截止时间"
              value={keyInfoDraft.sectionBidDeadlineAt ? dayjs(keyInfoDraft.sectionBidDeadlineAt) : null}
              onChange={(value) =>
                setKeyInfoDraft((draft) => ({
                  ...draft,
                  sectionBidDeadlineAt: value ? value.toISOString() : null
                }))
              }
            />
          </Space.Compact>
          <TextArea
            placeholder="修改/确认原因"
            value={keyInfoDraft.reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, reason: event.target.value }))}
          />
        </Space>
      </Modal>
      <Modal
        title="从原文新增合规条目"
        open={Boolean(sourceSelectionDraft)}
        width={760}
        okText="保存并查找相似片段"
        cancelText="取消"
        confirmLoading={savingSourceItem}
        onOk={handleCreateSourceItem}
        onCancel={() => setSourceSelectionDraft(null)}
      >
        {sourceSelectionDraft && (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              message={`来源：#${sourceSelectionDraft.chunk.chunk_index}${sourceSelectionDraft.chunk.page_no ? ` · P${sourceSelectionDraft.chunk.page_no}` : ""}`}
              description={sourceSelectionDraft.chunk.heading_path ?? "未识别章节路径"}
            />
            <TextArea
              value={sourceSelectionDraft.selectedText}
              autoSize={{ minRows: 4, maxRows: 8 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, selectedText: event.target.value } : draft)
              }
            />
            <Space.Compact style={{ width: "100%" }}>
              <Select
                value={sourceSelectionDraft.itemType}
                style={{ width: "34%" }}
                options={Object.entries(itemTypeLabels).map(([value, label]) => ({ value, label }))}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, itemType: value } : draft)
                }
              />
              <Select
                value={sourceSelectionDraft.riskLevel}
                style={{ width: "33%" }}
                options={Object.entries(riskLabels).map(([value, label]) => ({ value, label: `风险：${label}` }))}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, riskLevel: value } : draft)
                }
              />
              <Select
                value={sourceSelectionDraft.isMandatory ? "mandatory" : "normal"}
                style={{ width: "33%" }}
                options={[
                  { value: "mandatory", label: "强制处理" },
                  { value: "normal", label: "普通响应" }
                ]}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, isMandatory: value === "mandatory" } : draft)
                }
              />
            </Space.Compact>
            <TextArea
              placeholder="处理建议"
              value={sourceSelectionDraft.responseSuggestion}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, responseSuggestion: event.target.value } : draft)
              }
            />
            <TextArea
              placeholder="新增原因"
              value={sourceSelectionDraft.reason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, reason: event.target.value } : draft)
              }
            />
          </Space>
        )}
      </Modal>
      <Modal
        title="新增企业资料"
        open={materialModalOpen}
        width={720}
        okText="新增资料"
        cancelText="取消"
        confirmLoading={savingEnterprise}
        onOk={handleCreateEnterpriseMaterial}
        onCancel={() => setMaterialModalOpen(false)}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space.Compact style={{ width: "100%" }}>
            <Select
              value={newMaterialDraft.materialType}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, materialType: value }))}
              options={Object.entries(materialTypeLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 180 }}
            />
            <Input
              placeholder="资料名称，例如：市政公用工程施工总承包二级资质"
              value={newMaterialDraft.name}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, name: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="发证机关/建设单位"
              value={newMaterialDraft.issuingAuthority}
              onChange={(event) =>
                setNewMaterialDraft((draft) => ({ ...draft, issuingAuthority: event.target.value }))
              }
            />
            <Input
              placeholder="证书编号"
              value={newMaterialDraft.certificateNo}
              onChange={(event) =>
                setNewMaterialDraft((draft) => ({ ...draft, certificateNo: event.target.value }))
              }
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="人员姓名"
              value={newMaterialDraft.holderName}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, holderName: event.target.value }))}
            />
            <Input
              placeholder="业绩项目名称"
              value={newMaterialDraft.projectName}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, projectName: event.target.value }))}
            />
            <Input
              placeholder="金额"
              value={newMaterialDraft.amount}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, amount: event.target.value }))}
            />
          </Space.Compact>
          <Space wrap>
            <DatePicker
              placeholder="有效期至"
              value={newMaterialDraft.validUntil ? dayjs(newMaterialDraft.validUntil) : null}
              onChange={(value) =>
                setNewMaterialDraft((draft) => ({ ...draft, validUntil: value ? value.format("YYYY-MM-DD") : null }))
              }
            />
            <Select
              value={newMaterialDraft.dataLevel}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, dataLevel: value }))}
              options={Object.entries(dataLevelLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 140 }}
            />
            <Select
              value={newMaterialDraft.verificationStatus}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, verificationStatus: value }))}
              options={Object.entries(verificationStatusLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 140 }}
            />
          </Space>
          <TextArea
            placeholder="证据摘录，例如：证书载明资质类别、等级和有效期"
            value={newMaterialDraft.evidenceText}
            autoSize={{ minRows: 3, maxRows: 5 }}
            onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, evidenceText: event.target.value }))}
          />
          <Alert
            type="info"
            showIcon
            message="第一版先保存结构化字段。原始文件上传和自动抽取接口已在后端预留，后续会接到资料详情页。"
          />
        </Space>
      </Modal>
      <Modal
        title="编辑合规矩阵项"
        open={Boolean(editDraft)}
        okText="保存修改"
        cancelText="取消"
        confirmLoading={savingMatrixAction}
        onOk={handleSaveEditDraft}
        onCancel={() => setEditDraft(null)}
      >
        {editDraft && (
          <Space direction="vertical" size={14} style={{ width: "100%" }}>
            <Text>{truncateText(editDraft.row.requirement, 72)}</Text>
            <Space wrap>
              <div className="modal-field">
                <Text type="secondary">状态</Text>
                <Select
                  value={editDraft.status}
                  onChange={(value) => setEditDraft((draft) => (draft ? { ...draft, status: value } : draft))}
                  options={Object.entries(statusLabels)
                    .filter(([value]) => value !== "confirmed")
                    .map(([value, label]) => ({ value, label }))}
                  style={{ width: 160 }}
                />
              </div>
              <div className="modal-field">
                <Text type="secondary">风险</Text>
                <Select
                  value={editDraft.riskLevel}
                  onChange={(value) => setEditDraft((draft) => (draft ? { ...draft, riskLevel: value } : draft))}
                  options={Object.entries(riskLabels).map(([value, label]) => ({ value, label }))}
                  style={{ width: 120 }}
                />
              </div>
              <div className="modal-field compact">
                <Text type="secondary">强制项</Text>
                <Switch
                  checked={editDraft.isMandatory}
                  onChange={(checked) =>
                    setEditDraft((draft) => (draft ? { ...draft, isMandatory: checked } : draft))
                  }
                />
              </div>
            </Space>
            <div className="modal-field full">
              <Text type="secondary">响应建议</Text>
              <TextArea
                value={editDraft.responseSuggestion}
                autoSize={{ minRows: 3, maxRows: 6 }}
                onChange={(event) =>
                  setEditDraft((draft) =>
                    draft ? { ...draft, responseSuggestion: event.target.value } : draft
                  )
                }
              />
            </div>
            <div className="modal-field full">
              <Text type="secondary">修改原因</Text>
              <TextArea
                value={editDraft.reason}
                placeholder="必填，例如：根据公告原文补充风险等级或材料状态"
                autoSize={{ minRows: 2, maxRows: 4 }}
                onChange={(event) =>
                  setEditDraft((draft) => (draft ? { ...draft, reason: event.target.value } : draft))
                }
              />
            </div>
          </Space>
        )}
      </Modal>
      <ContextPackPreviewDrawer
        open={contextPackPreviewOpen}
        source={contextPackSource}
        loading={loadingContextPack}
        onClose={() => setContextPackPreviewOpen(false)}
        onAction={handleContextPackCheckAction}
        actionLabel={contextPackCheckActionText}
      />
      <Drawer
        title="查看/修正解析分块"
        open={revisionDrawerOpen}
        width={860}
        onClose={() => {
          setRevisionDrawerOpen(false);
          setRevisionDocument(null);
          setRevisionChunks([]);
          setRevisionReason("");
          setRevisionSearch("");
        }}
        extra={
          <Space>
            {revisionDocument?.current_version && (
              <Tag color={revisionDocument.current_version.parser_name === "manual-editor" ? "gold" : "blue"}>
                {revisionDocument.current_version.version_label}
              </Tag>
            )}
            <Button
              type="primary"
              loading={publishingRevision}
              disabled={!revisionChunks.length}
              onClick={handlePublishManualRevision}
            >
              发布修正版
            </Button>
          </Space>
        }
      >
        <Spin spinning={loadingRevisionChunks}>
          <Space direction="vertical" size={14} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              message="发布后会生成新的解析版本，不会自动覆盖合规矩阵；需要在文件列表中手动重新生成矩阵。"
            />
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索解析分块、章节路径或页码，例如：资格、检测报告、P12"
              value={revisionSearch}
              onChange={(event) => setRevisionSearch(event.target.value)}
            />
            <TextArea
              placeholder="修正原因，例如：人工补正 OCR 漏字和章节识别"
              value={revisionReason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) => setRevisionReason(event.target.value)}
            />
            {filteredRevisionChunks.map((chunk) => (
              <div className="revision-chunk" key={chunk.id}>
                <Space.Compact style={{ width: "100%" }}>
                  <Input
                    type="number"
                    min={1}
                    placeholder="页码"
                    value={chunk.page_no ?? ""}
                    onChange={(event) =>
                      updateRevisionChunk(chunk.id, {
                        page_no: event.target.value ? Number(event.target.value) : null
                      })
                    }
                    style={{ width: 110 }}
                  />
                  <Input
                    placeholder="章节路径"
                    value={chunk.heading_path ?? ""}
                    onChange={(event) => updateRevisionChunk(chunk.id, { heading_path: event.target.value || null })}
                  />
                </Space.Compact>
                <TextArea
                  value={chunk.content_text}
                  autoSize={{ minRows: 4, maxRows: 10 }}
                  onChange={(event) => updateRevisionChunk(chunk.id, { content_text: event.target.value })}
                />
                {chunk.table_json && (
                  <pre className="revision-table-json">{JSON.stringify(chunk.table_json, null, 2)}</pre>
                )}
              </div>
            ))}
            {!!revisionChunks.length && !filteredRevisionChunks.length && !loadingRevisionChunks && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的解析分块" />
            )}
            {!revisionChunks.length && !loadingRevisionChunks && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前版本暂无解析分块" />
            )}
          </Space>
        </Spin>
      </Drawer>
      <Drawer
        title="绑定企业资料证据"
        open={Boolean(evidenceDrawer)}
        width={720}
        onClose={() => {
          setEvidenceDrawer(null);
          setEvidenceBindings([]);
          setMaterialSearchResults([]);
        }}
      >
        {evidenceDrawer && (
          <div className="evidence-drawer">
            <Alert
              type="info"
              showIcon
              message="绑定不会自动确认矩阵项；资格项会自动重跑预评估，并使旧参标建议失效。"
            />
            <div className="evidence-requirement">
              <Text type="secondary">当前条款</Text>
              <p>{evidenceDrawer.requirement}</p>
            </div>
            <div className="evidence-section-title">
              <Title level={5}>已绑定资料</Title>
              <Space size={6} wrap>
                <Tag color={evidenceBindings.length ? "blue" : "default"}>
                  {evidenceBindings.length} 项
                </Tag>
                {evidenceDrawer.enterpriseEvidenceNotRequired && (
                  <Tag color="green">无需绑定证据</Tag>
                )}
                {!evidenceDrawer.enterpriseEvidenceNotRequired && !evidenceBindings.length && (
                  <Button
                    size="small"
                    loading={waivingEvidenceItemId === evidenceDrawer.key}
                    onClick={() => handleWaiveEvidenceRequirement(evidenceDrawer)}
                  >
                    无需绑定证据
                  </Button>
                )}
              </Space>
            </div>
            <Table<ComplianceEvidenceBinding>
              size="small"
              rowKey="id"
              pagination={LARGE_TABLE_PAGINATION}
              dataSource={evidenceBindings}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未绑定企业资料" /> }}
              columns={[
                {
                  title: "资料",
                  dataIndex: "material_name",
                  width: 210,
                  render: (value: string | null, record) => (
                    <Space direction="vertical" size={2}>
                      <Text strong>{value ?? "未命名资料"}</Text>
                      <Space size={4} wrap>
                        <Tag>{materialTypeLabels[record.material_type ?? "other"] ?? record.material_type}</Tag>
                        <Tag color={record.material_verification_status === "confirmed" ? "green" : "orange"}>
                          {verificationStatusLabels[record.material_verification_status ?? "draft"] ??
                            record.material_verification_status}
                        </Tag>
                      </Space>
                    </Space>
                  )
                },
                {
                  title: "证据摘录",
                  dataIndex: "evidence_text",
                  render: (value: string) => <Text className="evidence-snippet">{value}</Text>
                },
                {
                  title: "操作",
                  dataIndex: "action",
                  width: 90,
                  render: (_: unknown, record) => (
                    <Button
                      size="small"
                      danger
                      loading={unbindingId === record.id}
                      onClick={() => handleUnbindEvidence(record)}
                    >
                      解除
                    </Button>
                  )
                }
              ]}
            />
            <div className="evidence-section-title">
              <Title level={5}>检索企业资料</Title>
            </div>
            <Input.Search
              value={materialSearchQuery}
              placeholder="输入条款关键词、证书名称、人员或业绩名称"
              enterButton="检索"
              loading={loadingMaterialSearch}
              onChange={(event) => setMaterialSearchQuery(event.target.value)}
              onSearch={(value) => runMaterialSearch(value.trim() || evidenceDrawer.requirement)}
            />
            <Table<EnterpriseMaterialSearchResult>
              size="small"
              rowKey="id"
              pagination={LARGE_TABLE_PAGINATION}
              loading={loadingMaterialSearch}
              dataSource={materialSearchResults}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无匹配资料；请更换关键词或先到企业资料库补充资料"
                  />
                )
              }}
              columns={[
                {
                  title: "候选资料",
                  dataIndex: "name",
                  width: 230,
                  render: (value: string, record) => (
                    <Space direction="vertical" size={2}>
                      <Text strong>{value}</Text>
                      <Space size={4} wrap>
                        <Tag>{materialTypeLabels[record.material_type] ?? record.material_type}</Tag>
                        <Tag color={record.verification_status === "confirmed" ? "green" : "orange"}>
                          {verificationStatusLabels[record.verification_status] ?? record.verification_status}
                        </Tag>
                      </Space>
                    </Space>
                  )
                },
                {
                  title: "匹配证据",
                  dataIndex: "snippet",
                  render: (value: string | null, record) => (
                    <Space direction="vertical" size={4}>
                      <Text className="evidence-snippet">{value ?? record.evidence_text ?? record.name}</Text>
                      <Text type="secondary">匹配度 {Math.round(record.confidence_score * 100)}%</Text>
                      {record.recommend_reason && (
                        <Text type="secondary" className="recommend-reason">
                          推荐原因：{record.recommend_reason}
                        </Text>
                      )}
                      {record.material_status_hint && <Tag>{record.material_status_hint}</Tag>}
                      {record.matched_terms?.length ? (
                        <Space size={4} wrap>
                          {record.matched_terms.slice(0, 4).map((term) => (
                            <Tag key={term} color="blue">
                              {term}
                            </Tag>
                          ))}
                        </Space>
                      ) : null}
                    </Space>
                  )
                },
                {
                  title: "操作",
                  dataIndex: "action",
                  width: 110,
                  render: (_: unknown, record) => {
                    const bound = evidenceBindings.some(
                      (binding) => binding.enterprise_material_id === record.id
                    );
                    const blocked = record.verification_status === "conflict" || record.verification_status === "expired";
                    const busy = Boolean(bindingMaterialId);
                    const disabledReason = bound
                      ? "该资料已绑定到当前条款"
                      : blocked
                        ? "冲突或过期资料不能绑定"
                        : busy
                          ? "正在绑定其他资料"
                          : null;
                    return (
                      <Tooltip title={disabledReason}>
                        <span>
                          <Button
                            size="small"
                            type="primary"
                            disabled={bound || blocked || (busy && bindingMaterialId !== record.id)}
                            loading={bindingMaterialId === record.id}
                            onClick={() => handleBindEvidence(record)}
                          >
                            {bound ? "已绑定" : blocked ? "不可绑定" : "绑定"}
                          </Button>
                        </span>
                      </Tooltip>
                    );
                  }
                }
              ]}
            />
          </div>
        )}
      </Drawer>
      <Drawer title="证据来源原文" open={Boolean(sourceDrawer)} width={560} onClose={() => setSourceDrawer(null)}>
        {sourceDrawer && (
          <div className="source-drawer">
            <Space size={8} wrap>
              <Tag color={riskColor(sourceDrawer.risk)}>风险：{sourceDrawer.risk}</Tag>
              <Tag color={sourceDrawer.mandatory ? "red" : "default"}>
                {sourceDrawer.mandatory ? "强制项" : "非强制项"}
              </Tag>
              <Tag color={sourceDrawer.raw.source_content_text ? "blue" : "default"}>
                {sourceDrawer.raw.source_content_text ? "已回链原文" : "无原文片段"}
              </Tag>
            </Space>
            <Title level={5}>{sourceDrawer.source}</Title>
            <div className="source-meta-grid">
              <div>
                <Text type="secondary">来源文件</Text>
                <strong>{sourceDrawer.raw.source_document_title ?? "招标文件"}</strong>
              </div>
              <div>
                <Text type="secondary">解析版本</Text>
                <strong>{sourceDrawer.raw.source_version_label ?? "未记录"}</strong>
              </div>
              <div>
                <Text type="secondary">页码</Text>
                <strong>{sourceDrawer.raw.source_page_no ? `P${sourceDrawer.raw.source_page_no}` : "未记录"}</strong>
              </div>
              <div>
                <Text type="secondary">分块</Text>
                <strong>{sourceDrawer.raw.source_chunk_index ?? "未记录"}</strong>
              </div>
            </div>
            <div className="source-section">
              <Text type="secondary">章节路径</Text>
              <p>{sourceDrawer.raw.source_heading_path ?? "未识别章节路径"}</p>
            </div>
            <div className="source-section">
              <Text type="secondary">原文摘录</Text>
              <p>{sourceDrawer.raw.source_quote ?? sourceDrawer.raw.source_content_text ?? sourceDrawer.raw.evidence_text ?? sourceDrawer.requirement}</p>
            </div>
            {(sourceDrawer.raw.classification_reason || sourceDrawer.raw.split_reason || sourceDrawer.raw.review_hint) && (
              <div className="source-section">
                <Text type="secondary">AI/规则复核提示</Text>
                <p>{sourceDrawer.raw.review_hint ?? sourceDrawer.raw.classification_reason ?? "暂无复核提示"}</p>
                {sourceDrawer.raw.split_reason && <p>{sourceDrawer.raw.split_reason}</p>}
              </div>
            )}
            <div className="source-section">
              <Text type="secondary">规则命中解释</Text>
              <p>
                {explanationText(sourceDrawer.raw.rule_explanation, "rule_name")}：
                {explanationText(sourceDrawer.raw.rule_explanation, "rule_reason")}
              </p>
              <Space size={6} wrap>
                <Tag>{explanationText(sourceDrawer.raw.rule_explanation, "rule_code")}</Tag>
                {explanationKeywords(sourceDrawer.raw.rule_explanation).map((keyword) => (
                  <Tag color="blue" key={keyword}>
                    {keyword}
                  </Tag>
                ))}
              </Space>
            </div>
            <div className="source-section">
              <Text type="secondary">风险解释</Text>
              <p>{explanationText(sourceDrawer.raw.rule_explanation, "risk_reason")}</p>
            </div>
            <div className="source-section">
              <Text type="secondary">批量确认限制</Text>
              <p>{explanationText(sourceDrawer.raw.rule_explanation, "batch_confirm_reason")}</p>
            </div>
            <div className="source-meta-box">
              <Text type="secondary">定位元数据</Text>
              <p>BBox：{sourceMetaText(sourceDrawer.raw.source_bbox_json)}</p>
              <p>表格：{sourceMetaText(sourceDrawer.raw.source_table_json)}</p>
            </div>
            <Button type="primary" onClick={() => appendLog(`查看证据来源：${sourceDrawer.source}`)}>
              确认已核验
            </Button>
          </div>
        )}
      </Drawer>
    </>
  );
}
