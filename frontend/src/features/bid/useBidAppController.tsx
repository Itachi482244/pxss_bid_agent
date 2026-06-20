import {
  AuditOutlined,
  BarChartOutlined,
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
  notification,
  Pagination,
  Popover,
  Progress,
  Segmented,
  Select,
  Space,
  Spin,
  Statistic,
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
  updateBusinessDraftContextPackDirectives,
  type AuthorDirectiveInput,
  autoResolveComplianceMatrix,
  createComplianceItemFromSource,
  createEnterpriseMaterialsHistoryExtractTask,
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
  exportTenderFormatDocx,
  generateBusinessDraftFromContextPackAsync,
  generateBusinessDraftChapters,
  generateComplianceMatrix,
  getDocumentExtractionQualityReport,
  getComplianceEvidenceFeedbackReport,
  getComplianceEvidenceRetrievalEvaluation,
  getPreflightCheck,
  getMatrixReview,
  generateQualificationDecision,
  getEnterpriseProfile,
  getEnterpriseMaterialIndexHealth,
  getProject,
  getQualificationDecision,
  getSectionQualitySummary,
  getTask,
  listApprovalTasks,
  listBusinessDraftBlocks,
  listBusinessDraftChapters,
  listBusinessDraftContextPacks,
  listTasks,
  listEnterpriseMaterials,
  listComplianceEvidenceBindings,
  listComplianceEvidenceCandidates,
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
  rejectComplianceEvidenceCandidate,
  rebuildEnterpriseMaterialIndex,
  publishDocumentManualRevision,
  previewBusinessDraftContextPack,
  deriveBusinessDraftDirectory,
  getChatModelConfig,
  uploadEnterpriseMaterialFile,
  unbindComplianceEvidence,
  unlinkDuplicateGroupItem,
  updateProject,
  updateSection,
  updateEnterpriseMaterial,
  saveChatModelConfig,
  testChatModelConfig,
  upsertEnterpriseProfile,
  uploadDocument,
  waiveComplianceEvidenceRequirement,
  splitDuplicateGroupItem,
  updateBusinessDraftBlock,
  updateBusinessDraftChapter,
  updateComplianceItem
} from "../../api/bid";
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
  ComplianceEvidenceFeedbackReport,
  ComplianceEvidenceRetrievalEvaluation,
  ComplianceItemFromSourceResult,
  ComplianceItem,
  DocumentChunk,
  DocumentExtractionQualityReport,
  DocumentSemanticSection,
  DraftBlock,
  DraftCoverageReview,
  EnterpriseMaterial,
  EnterpriseMaterialHistoryExtractResult,
  EnterpriseMaterialIndexHealth,
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
  SectionQualityCheck,
  SectionQualityMaterial,
  SectionQualitySummary,
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
  AsyncTask,
  OutlineChapterInput,
  TenderFormatDocxExportMode
} from "../../api/bid";
import { ContextPackPreviewDrawer } from "../../components/ContextPackPreviewDrawer";
import { EvidenceCandidatePanel } from "../../components/EvidenceCandidatePanel";
import {
  buildProjectTodoActions,
  classifyProjectGroup,
  computeDashboardStats,
  computeDraftBlockFilterCounts,
  filterHomeProjects,
  materialExtractionMeta,
  matchesDraftBlockFilter,
  sectionQualityStatusColor,
  sectionQualityStatusLabel,
  type DraftBlockFilter,
  type ProjectGroup,
  type ProjectTodoAction
} from "../../pages/selectors";
import { OutlineEditorModal, type OutlineSeedChapter } from "../../components/OutlineEditorModal";
import { plainTerm } from "../../i18n/glossary";
import {
  DirectiveEditorModal,
  type DirectiveScopeOption
} from "../../components/DirectiveEditorModal";
import { useEnterpriseMaterials } from "./hooks/useEnterpriseMaterials";
import { useMatrixReview } from "./hooks/useMatrixReview";
import { useProjects } from "./hooks/useProjects";
import { useWorkspaceData } from "./hooks/useWorkspaceData";

const { Header, Content } = Layout;
const { Text, Title } = Typography;
const { TextArea } = Input;

export type MatrixRow = {
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

export type ProjectCreateMode = "file" | "url";
export type WorkflowStepKey =
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
export type MatrixReviewFilter = "all" | "unconfirmed" | "high" | "mandatory" | "missing_evidence";

function errorMessage(error: unknown, fallback: string) {
  if (error && typeof error === "object") {
    const candidate = error as {
      message?: string;
      code?: string;
      response?: { status?: number; data?: { detail?: unknown } | unknown };
    };
    const responseData = candidate.response?.data;
    const detail = responseData && typeof responseData === "object" && "detail" in responseData
      ? (responseData as { detail?: unknown }).detail
      : undefined;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) return String((item as { msg?: unknown }).msg ?? "");
          return String(item);
        })
        .filter(Boolean)
        .join("；");
    }
    if (candidate.message === "Network Error" || candidate.code === "ERR_NETWORK") {
      return "无法连接后端服务，请确认 FastAPI 已在 http://localhost:8000 启动。";
    }
    if (candidate.response?.status && candidate.response.status >= 500 && !detail) {
      return "后端服务异常或未启动，请确认 FastAPI 已在 http://localhost:8000 启动并通过 /health 检查。";
    }
    if (candidate.message?.trim()) return candidate.message;
  }
  return fallback;
}

function isHttpNotFound(error: unknown) {
  if (!error || typeof error !== "object") return false;
  const response = (error as { response?: { status?: number } }).response;
  return response?.status === 404;
}

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

function evidenceCandidateKey(itemKey: string, materialId: string) {
  return `${itemKey}:${materialId}`;
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
// 质检阻断时，每个标段自动唤起 Agent 自处理的最大次数；超出后转人工。
const AUTO_RESOLVE_AUTO_ATTEMPT_LIMIT = 1;
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

const projectGroupLabels: Record<ProjectGroup, string> = {
  needs_me: "待我处理",
  in_progress: "进行中",
  done: "已完成"
};

const projectGroupOrder: ProjectGroup[] = ["needs_me", "in_progress", "done"];

type ProjectNextStep = { text: string; tab?: string; actionable: boolean };

type MatrixAutoResolveRound = {
  round: number;
  strategy: "targeted" | "replan_regen" | string;
  reason?: string;
  resolved?: boolean;
  reextracted_sections?: string[];
  regen_status?: string;
};

type MatrixAutoResolveRemainingIssue = {
  severity: string;
  code: string;
  section_title?: string | null;
  section_id?: string | null;
  message: string;
};

type MatrixAutoResolveResult = {
  resolved: boolean;
  rounds: MatrixAutoResolveRound[];
  round_count: number;
  remaining_count: number;
  remaining_issues: MatrixAutoResolveRemainingIssue[];
  quality_status?: string;
};

// MVP1.4 决策：不改后端，"下一步"从 ProjectSummary 既有字段前端推导。
function deriveProjectNextStep(project: ProjectSummary): ProjectNextStep {
  switch (project.status) {
    case "pending_files":
      return { text: "上传招标文件", tab: "documents", actionable: true };
    case "parsing":
      return { text: "解析中，请稍候", actionable: false };
    case "exported":
      return { text: "已导出，可归档", actionable: false };
    case "archived":
      return { text: "已归档", actionable: false };
    default:
      break;
  }
  if (project.status === "pending_confirm" || project.pending_confirm_count > 0) {
    return { text: `确认合规清单项（${project.pending_confirm_count}）`, tab: "matrix", actionable: true };
  }
  if (project.status === "need_materials") {
    return { text: "补充缺失证据", tab: "evidence", actionable: true };
  }
  if (project.status === "confirmed") {
    if (project.high_risk_count > 0) return { text: "复核高风险项", tab: "matrix", actionable: true };
    return { text: "生成 / 审阅草稿", tab: "chapter", actionable: true };
  }
  if (project.status === "draft") {
    return { text: "完善项目信息", tab: "matrix", actionable: true };
  }
  return { text: "查看项目", tab: "matrix", actionable: true };
}

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
  needs_confirm: plainTerm("needs_confirm"),
  approved: "已通过",
  rejected: "已退回"
};

const draftBlockStatusColors: Record<string, string> = {
  pending: "gold",
  covered: "blue",
  needs_evidence: "red",
  needs_fact: "orange",
  needs_confirm: "purple",
  approved: "green",
  rejected: "red"
};

// P1：草稿块状态过滤（标签为白话；value 仍映射后端 review_status，不改语义）
const draftBlockFilterLabels: Record<DraftBlockFilter, string> = {
  all: "全部",
  needs_confirm: plainTerm("needs_confirm"),
  needs_evidence: "待补证",
  pending: "待覆盖"
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

// P1：异步任务"预计剩余时间"——按已用时与进度线性外推；进度过低时不臆测，返回阶段说明语义。
function asyncTaskEtaText(task: AsyncTask | null, taskId: string | null) {
  if (!taskId || !task) return "";
  if (isAsyncTaskTerminalStatus(task.status)) return "";
  const startedAt = dayjs(task.created_at);
  if (!startedAt.isValid()) return "";
  const elapsedMs = dayjs().diff(startedAt);
  const progress = Math.max(0, Math.min(100, Math.round(task.progress || 0)));
  if (progress < 5 || elapsedMs < 3000) return "正在排队/启动";
  const totalMs = (elapsedMs / progress) * 100;
  const remainMs = Math.max(0, totalMs - elapsedMs);
  const remainSec = Math.round(remainMs / 1000);
  if (remainSec <= 0) return "即将完成";
  if (remainSec < 60) return `预计还需约 ${remainSec} 秒`;
  return `预计还需约 ${Math.ceil(remainSec / 60)} 分钟`;
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

function outputRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function historyExtractResultFromTask(task: AsyncTask): EnterpriseMaterialHistoryExtractResult | null {
  const output = task.output_json;
  if (!output || !Array.isArray(output.materials)) return null;
  return {
    materials: output.materials as EnterpriseMaterial[],
    source_file_name: typeof output.source_file_name === "string" ? output.source_file_name : "",
    source_file_size: summaryNumber(output, "source_file_size"),
    source_sha256: typeof output.source_sha256 === "string" ? output.source_sha256 : "",
    parser_summary: outputRecord(output.parser_summary),
    extraction_method: typeof output.extraction_method === "string" ? output.extraction_method : "",
    warning_messages: Array.isArray(output.warning_messages)
      ? output.warning_messages.filter((item): item is string => typeof item === "string")
      : [],
    draft_count: summaryNumber(output, "draft_count"),
    text_block_count: summaryNumber(output, "text_block_count")
  };
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

function historyExtractTaskStageTitle(task: AsyncTask | null) {
  if (!task) return "历史资料抽取排队中";
  if (task.status === "succeeded") return "历史资料已抽取";
  if (task.status === "failed") return "历史资料抽取失败";
  const output = task.output_json ?? null;
  const stage = taskOutputText(task, "stage");
  const completedPages = summaryNumber(output, "ocr_completed_pages");
  const totalPages = summaryNumber(output, "ocr_total_pages");
  const sourceName = taskOutputText(task, "source_file_name");
  const stageLabel =
    stage === "reading_file"
      ? "读取历史文件"
      : stage === "extracting_text"
        ? "解析文本/准备 OCR"
        : stage === "ocr"
          ? "逐页 OCR 识别"
          : stage === "writing_materials"
            ? "写入待确认资料"
            : "历史资料抽取中";
  const pageText = completedPages && totalPages ? `第 ${completedPages}/${totalPages} 页` : "";
  return [stageLabel, pageText, sourceName].filter(Boolean).join(" · ");
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
    "business_draft.context_pack_created": "生成投标素材包",
    "business_draft.context_pack_generated": "按投标素材包生成草稿",
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


export function useBidAppController() {
  const [assistantCollapsed, setAssistantCollapsed] = useState(true);
  const [projectNavCollapsed, setProjectNavCollapsed] = useState(true);
  const [viewMode, setViewMode] = useState<"home" | "workspace" | "enterprise" | "settings" | "dashboard">("home");
  const [selectedSectionId, setSelectedSectionId] = useState<string>();
  const [selectedTreeKey, setSelectedTreeKey] = useState("");
  const [activeTab, setActiveTab] = useState<WorkflowStepKey>("matrix");
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
  const [qualityChunks, setQualityChunks] = useState<ReviewChunk[]>([]);
  const [loadingQualityChunks, setLoadingQualityChunks] = useState(false);
  const [activeReviewItemId, setActiveReviewItemId] = useState("");
  const [locatingReviewItemId, setLocatingReviewItemId] = useState("");
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
  const historyExtractTerminalTaskRef = useRef<Set<string>>(new Set());
  const [materialSearchQuery, setMaterialSearchQuery] = useState("");
  const [materialSearchResults, setMaterialSearchResults] = useState<EnterpriseMaterialSearchResult[]>([]);
  const [loadingMaterialSearch, setLoadingMaterialSearch] = useState(false);
  const [evidenceCandidates, setEvidenceCandidates] = useState<EnterpriseMaterialSearchResult[]>([]);
  const [loadingEvidenceCandidates, setLoadingEvidenceCandidates] = useState(false);
  const [candidateIncludeUnconfirmed, setCandidateIncludeUnconfirmed] = useState(false);
  const [candidateIncludeRestricted, setCandidateIncludeRestricted] = useState(false);
  const [bindingMaterialId, setBindingMaterialId] = useState("");
  const [rejectingCandidateId, setRejectingCandidateId] = useState("");
  const [rejectedEvidenceCandidateKeys, setRejectedEvidenceCandidateKeys] = useState<Set<string>>(new Set());
  const [unbindingId, setUnbindingId] = useState("");
  const [editDraft, setEditDraft] = useState<EditMatrixDraft | null>(null);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [projectCreateMode, setProjectCreateMode] = useState<ProjectCreateMode>("file");
  const [projectImportDraft, setProjectImportDraft] = useState<ProjectImportDraft | null>(null);
  const [projectImportError, setProjectImportError] = useState("");
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

  const [projectDeleteTargets, setProjectDeleteTargets] = useState<ProjectSummary[]>([]);
  const [homeProjectGroup, setHomeProjectGroup] = useState<ProjectGroup>("needs_me");
  const [homeProjectSearch, setHomeProjectSearch] = useState("");
  const [homeProjectPage, setHomeProjectPage] = useState(1);
  const [homeProjectPageSize, setHomeProjectPageSize] = useState(8);
  const [preflightCheck, setPreflightCheck] = useState<PreflightCheck | null>(null);
  const [preflightExpanded, setPreflightExpanded] = useState(false);
  const [todoExpanded, setTodoExpanded] = useState(false);
  const [qualificationEvaluations, setQualificationEvaluations] = useState<QualificationEvaluation[]>([]);
  const [qualificationDecision, setQualificationDecision] = useState<QualificationDecision | null>(null);
  const [businessDraftChapters, setBusinessDraftChapters] = useState<BusinessDraftChapter[]>([]);
  const [businessDraftContextPacks, setBusinessDraftContextPacks] = useState<BusinessDraftContextPack[]>([]);
  const [contextPackPreview, setContextPackPreview] = useState<BusinessDraftContextPackPreview | null>(null);
  const [contextPackPreviewOpen, setContextPackPreviewOpen] = useState(false);
  const [outlineEditorOpen, setOutlineEditorOpen] = useState(false);
  const [outlineSeed, setOutlineSeed] = useState<OutlineSeedChapter[]>([]);
  const [editedOutline, setEditedOutline] = useState<OutlineChapterInput[] | null>(null);
  const [directiveEditorOpen, setDirectiveEditorOpen] = useState(false);
  const [editedDirectives, setEditedDirectives] = useState<AuthorDirectiveInput[] | null>(null);
  const [draftBlocks, setDraftBlocks] = useState<DraftBlock[]>([]);
  const [activeDraftBlockId, setActiveDraftBlockId] = useState("");
  // P1：草稿块审阅效率——状态过滤、已查看标记（受保护批量确认依据）、降噪展开
  const [draftBlockFilter, setDraftBlockFilter] = useState<DraftBlockFilter>("all");
  const [viewedDraftBlockIds, setViewedDraftBlockIds] = useState<Set<string>>(new Set());
  const [expandedDraftBlockIds, setExpandedDraftBlockIds] = useState<Set<string>>(new Set());
  const [mandatoryReviewOpen, setMandatoryReviewOpen] = useState(false);
  const [mandatoryReviewIndex, setMandatoryReviewIndex] = useState(0);
  const [coverageReview, setCoverageReview] = useState<DraftCoverageReview | null>(null);
  const [selectedDraftChapterId, setSelectedDraftChapterId] = useState("");
  const [draftEditorValue, setDraftEditorValue] = useState("");
  const [approvalTasks, setApprovalTasks] = useState<ApprovalTask[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [evidenceFeedbackReport, setEvidenceFeedbackReport] =
    useState<ComplianceEvidenceFeedbackReport | null>(null);
  const [evidenceRetrievalEvaluation, setEvidenceRetrievalEvaluation] =
    useState<ComplianceEvidenceRetrievalEvaluation | null>(null);
  const [loadingEvidenceQuality, setLoadingEvidenceQuality] = useState(false);
  const [savingMatrixAction, setSavingMatrixAction] = useState(false);
  const [loadingBusinessDraft, setLoadingBusinessDraft] = useState(false);
  const [businessDraftGenerationTaskId, setBusinessDraftGenerationTaskId] = useState<string | null>(null);
  const [businessDraftGenerationTask, setBusinessDraftGenerationTask] = useState<AsyncTask | null>(null);
  const [loadingContextPack, setLoadingContextPack] = useState(false);
  const [savingBusinessDraft, setSavingBusinessDraft] = useState(false);
  const [exportingWord, setExportingWord] = useState(false);
  const [exportingTenderFormatMode, setExportingTenderFormatMode] =
    useState<TenderFormatDocxExportMode | "">("");
  const [sectionQualitySummary, setSectionQualitySummary] = useState<SectionQualitySummary | null>(null);
  const [loadingSectionQuality, setLoadingSectionQuality] = useState(false);
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
  const [autoResolveActive, setAutoResolveActive] = useState(false);
  const [autoResolveResult, setAutoResolveResult] = useState<MatrixAutoResolveResult | null>(null);
  const autoResolveInFlightRef = useRef(false);
  const autoResolveAutoAttemptsRef = useRef<Record<string, number>>({});
  // 记录上一次的推荐（当前阻塞）步骤 key，用于「步骤通过后自动前进到下一个阻塞步骤」。
  const prevRecommendedStepKeyRef = useRef<string | null>(null);
  const suppressNextWorkflowAdvanceFromRef = useRef<WorkflowStepKey | null>(null);
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
  const [extractingHistoryMaterial, setExtractingHistoryMaterial] = useState(false);
  const [historyExtractTaskId, setHistoryExtractTaskId] = useState<string | null>(null);
  const [historyExtractTask, setHistoryExtractTask] = useState<AsyncTask | null>(null);
  const [historyExtractResult, setHistoryExtractResult] = useState<EnterpriseMaterialHistoryExtractResult | null>(null);
  const [confirmingMaterialId, setConfirmingMaterialId] = useState("");
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

  const {
    applyProjectList,
    loadingProjects,
    projects,
    reloadProjects,
    selectedProjectId,
    selectedProjectRowKeys,
    setLoadingProjects,
    setProjects,
    setSelectedProjectId,
    setSelectedProjectRowKeys
  } = useProjects({ formatError: errorMessage, onError: setApiError });

  const {
    complianceItems,
    documents,
    exportFiles,
    loadingMatrix,
    loadingWorkspace,
    projectDetail,
    reloadDocumentsAndExports,
    reloadMatrix,
    reloadWorkspaceSummary,
    sections,
    setComplianceItems,
    setDocuments,
    setExportFiles,
    setLoadingMatrix,
    setLoadingWorkspace,
    setProjectDetail,
    setSections
  } = useWorkspaceData({
    formatError: errorMessage,
    matrixFetchLimit: COMPLIANCE_ITEM_FETCH_LIMIT,
    onError: setApiError,
    selectedProjectId,
    selectedSectionId,
    setSelectedRowKeys,
    setSelectedSectionId
  });

  const {
    enterpriseMaterials,
    enterpriseProfile,
    loadingEnterprise,
    loadingMaterialIndexHealth,
    materialIndexHealth,
    profileDraft,
    rebuildingMaterialIndex,
    reloadEnterprise,
    reloadMaterialIndexHealth,
    savingEnterprise,
    setEnterpriseMaterials,
    setEnterpriseProfile,
    setLoadingEnterprise,
    setLoadingMaterialIndexHealth,
    setMaterialIndexHealth,
    setProfileDraft,
    setRebuildingMaterialIndex,
    setSavingEnterprise
  } = useEnterpriseMaterials({ formatError: errorMessage, onError: setApiError });

  const {
    loadingReviewChunks,
    reloadMatrixReview,
    reviewChunks,
    reviewDuplicateGroups,
    reviewHighlights,
    reviewOpenXmlDocument,
    reviewUncoveredChunks,
    setLoadingReviewChunks,
    setReviewChunks,
    setReviewDuplicateGroups,
    setReviewHighlights,
    setReviewOpenXmlDocument,
    setReviewUncoveredChunks
  } = useMatrixReview({
    activeTab,
    selectedProjectId,
    selectedSectionId,
    setComplianceItems
  });

  useEffect(() => {
    return () => {
      if (locateReviewTimerRef.current !== null) {
        window.clearTimeout(locateReviewTimerRef.current);
      }
    };
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
      setApiError(errorMessage(error, "模型配置加载失败"));
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
    setQualificationEvaluations([]);
    setQualificationDecision(null);
    setBusinessDraftChapters([]);
    setBusinessDraftContextPacks([]);
    setDraftBlocks([]);
    setContextPackPreview(null);
    setContextPackPreviewOpen(false);
    setEditedOutline(null);
    setOutlineEditorOpen(false);
    setApprovalTasks([]);
    setPreflightCheck(null);
    setEvidenceFeedbackReport(null);
    setEvidenceRetrievalEvaluation(null);
    setCoverageReview(null);
    setSelectedDraftChapterId("");
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
    if (selectedSectionId && !selectedTreeKey) {
      setSelectedTreeKey(`section:${selectedSectionId}`);
    }
  }, [selectedSectionId, selectedTreeKey]);

  const currentProject = projectDetail ?? projects.find((project) => project.id === selectedProjectId);
  const currentSection = sections.find((section) => section.id === selectedSectionId);
  const sectionLockedForEdit =
    currentSection?.assist_stage === "confirmed" || currentSection?.assist_stage === "generated";
  const sectionEditLockReason = sectionLockedForEdit
    ? "该标段已确认锁定或已生成标书。需要修改矩阵、证据、资格或草稿时，请先在最终确认页撤回。"
    : "";
  const warnSectionLockedForEdit = useCallback(() => {
    if (!sectionLockedForEdit) return false;
    Modal.warning({
      title: "需先撤回确认",
      content: sectionEditLockReason
    });
    return true;
  }, [sectionEditLockReason, sectionLockedForEdit]);
  const dispatchAgentReviewRefresh = useCallback(() => {
    window.dispatchEvent(new Event("pxss-agent-review-refresh"));
  }, []);
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
  // P1：按状态过滤后的可见块 + 各过滤项计数（用于过滤条角标）
  const visibleChapterBlocks = useMemo(
    () => selectedChapterBlocks.filter((block) => matchesDraftBlockFilter(block, draftBlockFilter)),
    [selectedChapterBlocks, draftBlockFilter]
  );
  const draftBlockFilterCounts = useMemo(
    () => computeDraftBlockFilterCounts(selectedChapterBlocks),
    [selectedChapterBlocks]
  );
  // P1：本章"必须原样写入的内容"（needs_confirm）逐条查看流的队列
  const chapterMandatoryBlocks = useMemo(
    () => selectedChapterBlocks.filter((block) => block.review_status === "needs_confirm"),
    [selectedChapterBlocks]
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
    setTodoExpanded(false);
  }, [selectedProjectId, selectedSectionId, preflightCheck?.status, sectionQualitySummary?.status]);

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
  const projectTodoActions = useMemo(
    () => buildProjectTodoActions(sectionQualitySummary, preflightChecksForDisplay),
    [preflightChecksForDisplay, sectionQualitySummary]
  );
  const projectTodoStatusForDisplay = useMemo(() => {
    if (projectTodoActions.some((item) => item.status === "block")) return "block";
    if (projectTodoActions.some((item) => item.status === "warn")) return "warn";
    return "pass";
  }, [projectTodoActions]);
  const visibleProjectTodoActions = useMemo(
    () => (todoExpanded ? projectTodoActions : projectTodoActions.slice(0, 3)),
    [projectTodoActions, todoExpanded]
  );
  const hiddenProjectTodoActionCount = Math.max(0, projectTodoActions.length - visibleProjectTodoActions.length);
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
            message: "已确认不建议参标；投标素材包只能作为风险快照。",
            action: "查看资格结论"
          }
        : qualificationDecision?.recommendation === "conditional_go"
          ? {
              status: "warn",
              message: "有条件 Go，确认投标素材包前请复核待补事项。",
              action: "查看资格结论"
            }
          : {
              status: "pass",
              message: "资格结论已确认，可确认投标素材包。",
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
      ? "请先预览并核对完整投标素材包。"
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
    "基于已确认投标素材包生成结构化商务/资格草稿；需先确认参标建议且投标素材包无硬阻塞项。";
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
  const historyExtractActive = isAsyncTaskActive(historyExtractTask, historyExtractTaskId);
  const historyExtractProgress = asyncTaskProgress(historyExtractTask, historyExtractTaskId);
  const historyExtractStatusText = asyncTaskStatusText(historyExtractTask, historyExtractTaskId);
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
        description: "预览技术要求、评分项和待确认项，行业专项能力另行处理。",
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
            ? "暂无技术项"
            : "未开始",
        actionText: "查看技术响应",
	        reason: technicalRows.length
	          ? `已识别 ${technicalRows.length} 条技术响应或评分相关要求。`
	          : knownMatrixCount
	            ? "当前矩阵暂无明确技术响应项；产品选型和技术标生成需要后续专项能力支持。"
	            : "需要先生成合规矩阵。",
	        disabled: !canOpenMatrixDerived,
	        disabledReason: canOpenMatrixDerived ? null : extractionBlocked ? extractionBlockReason : "请先生成合规矩阵。"
	      },
      {
        key: "qualification",
        title: "资格预评估",
        description: "基于合规清单和企业画像生成参标建议。",
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
        title: "投标素材包",
        description: "生成和确认商务/资格草稿的投标素材包，作为草稿生成输入。",
        status: contextPackStatus,
        statusText: activeContextPack
          ? preflightLabel(activeContextPack.readiness_status)
          : contextPackPreview
            ? "已预览"
            : "未生成",
        actionText: activeContextPack ? "查看投标素材包" : "生成/确认投标素材包",
	        reason: activeContextPack
	          ? "投标素材包已生成；可以继续生成草稿、校验事实并导出 Word。"
            : qualificationDecisionConfirmed && qualificationDecisionIsNoGo
              ? "参标建议为不建议参标；如仍需构建投标素材包，需要先记录风险接受说明。"
		          : qualificationDecisionConfirmed
		            ? "参标建议已确认，可以预览并确认投标素材包。"
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
        title: "草稿导出",
        description: "基于已确认投标素材包生成草稿、校验事实并导出 Word。",
        status: "not_started",
        statusText: "待处理",
        actionText: "进入草稿导出",
	        reason: "基于已确认投标素材包生成草稿、校验事实，并在导出前完成审批确认。",
	        disabled: !canOpenApproval,
	        disabledReason: canOpenApproval ? null : "请先确认投标素材包并完成草稿生成。"
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
      group("draft", "投标素材包", "chapter", ["chapter"])
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

  const projectGroupCounts = useMemo(() => {
    const counts: Record<ProjectGroup, number> = { needs_me: 0, in_progress: 0, done: 0 };
    projects.forEach((project) => {
      counts[classifyProjectGroup(project)] += 1;
    });
    return counts;
  }, [projects]);

  const filteredHomeProjects = useMemo(
    () => filterHomeProjects(projects, homeProjectGroup, homeProjectSearch),
    [projects, homeProjectGroup, homeProjectSearch]
  );

  useEffect(() => {
    setHomeProjectPage(1);
  }, [homeProjectGroup, homeProjectSearch]);

  // P1-6：管理层宏观看板——纯前端聚合现有项目数据（不改后端）；缺数据源指标明确标注"暂无数据"。
  const dashboardStats = useMemo(() => computeDashboardStats(projects), [projects]);

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

  const reloadAuditLogs = useCallback(async () => {
    if (!selectedProjectId) return;
    const data = await listAuditLogs(selectedProjectId);
    setAuditLogs(data);
  }, [selectedProjectId]);

  const reloadEvidenceQualityReports = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) {
      setEvidenceFeedbackReport(null);
      setEvidenceRetrievalEvaluation(null);
      return;
    }
    setLoadingEvidenceQuality(true);
    try {
      const [feedbackResult, evaluationResult] = await Promise.allSettled([
        getComplianceEvidenceFeedbackReport(selectedProjectId, selectedSectionId),
        getComplianceEvidenceRetrievalEvaluation(selectedProjectId, selectedSectionId, { top_k: 5 })
      ]);
      setEvidenceFeedbackReport(feedbackResult.status === "fulfilled" ? feedbackResult.value : null);
      setEvidenceRetrievalEvaluation(evaluationResult.status === "fulfilled" ? evaluationResult.value : null);
      if (feedbackResult.status === "rejected" || evaluationResult.status === "rejected") {
        appendLog("证据质量报表加载失败，可稍后刷新");
      }
    } finally {
      setLoadingEvidenceQuality(false);
    }
  }, [appendLog, selectedProjectId, selectedSectionId]);

  useEffect(() => {
    void reloadEvidenceQualityReports().catch(() => {
      setEvidenceFeedbackReport(null);
      setEvidenceRetrievalEvaluation(null);
      setLoadingEvidenceQuality(false);
    });
  }, [reloadEvidenceQualityReports]);

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

  const reloadSectionQualitySummary = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!selectedProjectId || !selectedSectionId) {
        setSectionQualitySummary(null);
        return null;
      }
      setLoadingSectionQuality(true);
      try {
        const data = await getSectionQualitySummary(selectedProjectId, selectedSectionId);
        setSectionQualitySummary(data);
        return data;
      } catch (error) {
        setSectionQualitySummary(null);
        if (!options?.silent) setApiError(errorMessage(error, "标书质量体检加载失败"));
        return null;
      } finally {
        setLoadingSectionQuality(false);
      }
    },
    [selectedProjectId, selectedSectionId]
  );

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) {
      setSectionQualitySummary(null);
      return;
    }
    void reloadSectionQualitySummary({ silent: true });
  }, [reloadSectionQualitySummary, selectedProjectId, selectedSectionId]);

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
      reloadPreflightCheck(),
      reloadSectionQualitySummary({ silent: true }),
      reloadEvidenceQualityReports()
    ]);
  }, [
    reloadApprovalTasks,
    reloadAuditLogs,
    reloadBusinessDraftChapters,
    reloadBusinessDraftContext,
    reloadDocumentsAndExports,
    reloadEvidenceQualityReports,
    reloadPreflightCheck,
    reloadSectionQualitySummary,
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

    const clearCurrentImportProcessing = () => {
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
    };

    const handleTaskPollError = (error: unknown) => {
      if (!active) return;
      if (isHttpNotFound(error)) {
        appendLog("后台任务记录已不存在，已停止自动刷新");
        clearCurrentImportProcessing();
        return;
      }
      setApiError(error instanceof Error ? error.message : "后台任务状态刷新失败");
    };

    const pollTasks = async () => {
      const [parseTask, matrixTask] = await Promise.all([
        importProcessing.parseTaskId ? getTask(importProcessing.parseTaskId) : Promise.resolve(null),
        importProcessing.matrixTaskId ? getTask(importProcessing.matrixTaskId) : Promise.resolve(null)
      ]);
      if (!active) return;

      const staleTask = [parseTask, matrixTask].find((task) => isAsyncTaskStale(task));
      if (staleTask) {
        appendLog(`后台任务 ${staleTask.id.slice(0, 8)} 长时间未更新，已停止自动刷新`);
        clearCurrentImportProcessing();
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
          reloadSectionQualitySummary({ silent: true }),
          reloadAuditLogs()
        ]);
      }

      const parseTerminal = isAsyncTaskTerminal(parseTask, importProcessing.parseTaskId);
      const matrixTerminal = isAsyncTaskTerminal(matrixTask, importProcessing.matrixTaskId);
      if (parseTerminal && matrixTerminal && !clearTimer) {
        clearTimer = window.setTimeout(() => {
          clearCurrentImportProcessing();
        }, 8000);
      }
    };

    void pollTasks().catch(handleTaskPollError);
    const intervalId = window.setInterval(() => {
      void pollTasks().catch(handleTaskPollError);
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
    reloadSectionQualitySummary,
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
        notification.success({
          message: "草稿已生成",
          description: `已生成 ${summaryNumber(task.output_json, "chapter_count")} 章、${summaryNumber(task.output_json, "block_count")} 个段落，请继续审阅待补证据与待补事实。`,
          placement: "topRight",
          duration: 6
        });
      } else {
        const message = task.error_message || "商务草稿生成任务失败";
        setApiError(message);
        appendLog(`商务草稿生成失败：${truncateText(message, 48)}`);
        notification.error({
          message: "草稿生成失败",
          description: truncateText(message, 80),
          placement: "topRight",
          duration: 8
        });
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

  useEffect(() => {
    if (!historyExtractTaskId) return;
    let active = true;
    let clearTimer: number | null = null;

    const pollHistoryExtractTask = async () => {
      const task = await getTask(historyExtractTaskId);
      if (!active) return;
      setHistoryExtractTask(task);

      if (!isAsyncTaskTerminalStatus(task.status)) return;
      const terminalKey = `${task.id}:${task.status}`;
      if (historyExtractTerminalTaskRef.current.has(terminalKey)) return;
      historyExtractTerminalTaskRef.current.add(terminalKey);

      if (task.status === "succeeded") {
        const result = historyExtractResultFromTask(task);
        if (!result) {
          const message = "历史资料抽取完成，但结果结构异常";
          setApiError(message);
          appendLog(message);
          notification.error({
            message: "历史资料抽取结果异常",
            description: message,
            placement: "topRight",
            duration: 8
          });
        } else {
          setHistoryExtractResult(result);
          setEnterpriseMaterials((items) => {
            const existingIds = new Set(items.map((item) => item.id));
            const newItems = result.materials.filter((item) => !existingIds.has(item.id));
            return [...newItems, ...items];
          });
          setContextPackPreview(null);
          setContextPackPreviewOpen(false);
          await reloadAuditLogs();
          appendLog(`历史资料抽取完成：${result.source_file_name}，生成 ${result.draft_count} 条待确认资料`);
          notification.success({
            message: "历史资料已抽取",
            description:
              result.draft_count > 0
                ? `已生成 ${result.draft_count} 条待确认草稿，请逐条核对来源后确认。`
                : "未识别到可入库资料，可换一份文件或手工新增。",
            placement: "topRight",
            duration: 6
          });
        }
      } else {
        const message = task.error_message || "历史资料抽取任务失败";
        setApiError(message);
        appendLog(`历史资料抽取失败：${truncateText(message, 48)}`);
        notification.error({
          message: "历史资料抽取失败",
          description: truncateText(message, 80),
          placement: "topRight",
          duration: 8
        });
      }

      clearTimer = window.setTimeout(() => {
        if (!active) return;
        setHistoryExtractTaskId(null);
        setHistoryExtractTask(null);
      }, 8000);
    };

    void pollHistoryExtractTask().catch((error: unknown) => {
      setApiError(error instanceof Error ? error.message : "历史资料任务状态刷新失败");
    });
    const intervalId = window.setInterval(() => {
      void pollHistoryExtractTask().catch((error: unknown) => {
        setApiError(error instanceof Error ? error.message : "历史资料任务状态刷新失败");
      });
    }, 1500);

    return () => {
      active = false;
      window.clearInterval(intervalId);
      if (clearTimer) window.clearTimeout(clearTimer);
    };
  }, [appendLog, historyExtractTaskId, reloadAuditLogs]);

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

  const fetchEvidenceCandidates = useCallback(
    async (
      itemKey: string,
      options: { includeUnconfirmed: boolean; includeRestricted: boolean }
    ) => {
      if (!selectedProjectId || !selectedSectionId) return;
      setLoadingEvidenceCandidates(true);
      try {
        const candidates = await listComplianceEvidenceCandidates(
          selectedProjectId,
          selectedSectionId,
          itemKey,
          {
            include_unconfirmed: options.includeUnconfirmed,
            include_restricted: options.includeRestricted,
            limit: 10
          }
        );
        setEvidenceCandidates(
          candidates.filter((candidate) => !rejectedEvidenceCandidateKeys.has(evidenceCandidateKey(itemKey, candidate.id)))
        );
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "候选证据推荐失败");
      } finally {
        setLoadingEvidenceCandidates(false);
      }
    },
    [rejectedEvidenceCandidateKeys, selectedProjectId, selectedSectionId]
  );

  const openEvidenceBindingDrawer = useCallback(
    async (row: MatrixRow) => {
      if (!selectedProjectId || !selectedSectionId) return;
      setOpeningEvidenceItemId(row.key);
      setEvidenceDrawer(row);
      setEvidenceBindings([]);
      setMaterialSearchResults([]);
      setEvidenceCandidates([]);
      setCandidateIncludeUnconfirmed(false);
      setCandidateIncludeRestricted(false);
      setMaterialSearchQuery(row.requirement);
      setLoadingMaterialSearch(true);
      setLoadingEvidenceCandidates(true);
      try {
        const [bindings, results, candidates] = await Promise.all([
          listComplianceEvidenceBindings(selectedProjectId, selectedSectionId, row.key),
          searchEnterpriseMaterials({ query: row.requirement, limit: 12 }),
          listComplianceEvidenceCandidates(selectedProjectId, selectedSectionId, row.key, {
            include_unconfirmed: false,
            include_restricted: false,
            limit: 10
          })
        ]);
        setEvidenceBindings(bindings);
        setMaterialSearchResults(results);
        setEvidenceCandidates(
          candidates.filter((candidate) => !rejectedEvidenceCandidateKeys.has(evidenceCandidateKey(row.key, candidate.id)))
        );
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "证据绑定信息加载失败");
      } finally {
        setLoadingMaterialSearch(false);
        setLoadingEvidenceCandidates(false);
        setOpeningEvidenceItemId((current) => (current === row.key ? "" : current));
      }
    },
    [rejectedEvidenceCandidateKeys, selectedProjectId, selectedSectionId]
  );

  const reloadEvidenceBindings = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId || !evidenceDrawer) return;
    const bindings = await listComplianceEvidenceBindings(selectedProjectId, selectedSectionId, evidenceDrawer.key);
    setEvidenceBindings(bindings);
  }, [evidenceDrawer, selectedProjectId, selectedSectionId]);

  const reloadEvidenceCandidates = useCallback(async () => {
    if (!evidenceDrawer) return;
    await fetchEvidenceCandidates(evidenceDrawer.key, {
      includeUnconfirmed: candidateIncludeUnconfirmed,
      includeRestricted: candidateIncludeRestricted
    });
  }, [candidateIncludeRestricted, candidateIncludeUnconfirmed, evidenceDrawer, fetchEvidenceCandidates]);

  const handleToggleCandidateUnconfirmed = useCallback(
    (checked: boolean) => {
      setCandidateIncludeUnconfirmed(checked);
      if (evidenceDrawer) {
        void fetchEvidenceCandidates(evidenceDrawer.key, {
          includeUnconfirmed: checked,
          includeRestricted: candidateIncludeRestricted
        });
      }
    },
    [candidateIncludeRestricted, evidenceDrawer, fetchEvidenceCandidates]
  );

  const handleToggleCandidateRestricted = useCallback(
    (checked: boolean) => {
      setCandidateIncludeRestricted(checked);
      if (evidenceDrawer) {
        void fetchEvidenceCandidates(evidenceDrawer.key, {
          includeUnconfirmed: candidateIncludeUnconfirmed,
          includeRestricted: checked
        });
      }
    },
    [candidateIncludeUnconfirmed, evidenceDrawer, fetchEvidenceCandidates]
  );

  const handleBindEvidence = useCallback(
    async (material: EnterpriseMaterialSearchResult) => {
      if (!selectedProjectId || !selectedSectionId || !evidenceDrawer) return;
      if (warnSectionLockedForEdit()) return;
      if (bindingMaterialId) return;
      if (material.verification_status === "conflict" || material.verification_status === "expired") {
        Modal.warning({ title: "该资料暂不可绑定", content: "冲突或过期资料不能作为响应证据绑定。" });
        return;
      }
      if (material.data_level === "restricted" || material.data_level === "confidential") {
        Modal.warning({
          title: "该资料暂不可绑定",
          content: "受限或机密资料不能直接进入可引用证据。请先在企业资料库完成脱敏，或调整为可用于投标响应的数据等级。"
        });
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
            await Promise.all([
              reloadApprovalTasks(),
              reloadAuditLogs(),
              reloadPreflightCheck(),
              reloadEvidenceQualityReports()
            ]);
          } finally {
            setEvaluatingQualification(false);
            setGeneratingDecision(false);
          }
        } else {
          await Promise.all([reloadEvidenceBindings(), refreshAfterMatrixMutation()]);
        }
        await reloadEvidenceCandidates().catch(() => undefined);
        dispatchAgentReviewRefresh();
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
      dispatchAgentReviewRefresh,
      evidenceDrawer,
      evidenceBindings,
      generateQualificationDecision,
      qualificationNeedsMaterialByItemId,
      refreshAfterMatrixMutation,
      reloadEvidenceBindings,
      reloadEvidenceCandidates,
      reloadEvidenceQualityReports,
      reloadApprovalTasks,
      reloadAuditLogs,
      reloadMatrix,
      reloadMatrixReview,
      reloadPreflightCheck,
      reloadQualificationEvaluations,
      selectedProjectId,
      selectedSectionId,
      warnSectionLockedForEdit
    ]
  );

  const handleRejectEvidenceCandidate = useCallback(
    (material: EnterpriseMaterialSearchResult) => {
      if (!selectedProjectId || !selectedSectionId || !evidenceDrawer || rejectingCandidateId) return;
      if (warnSectionLockedForEdit()) return;
      let reason = material.verification_status === "confirmed"
        ? "候选证据与当前条款不匹配"
        : "候选资料尚未确认或存在风险，暂不采用";
      Modal.confirm({
        title: "不采用该候选证据",
        content: (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Text strong>{material.name}</Text>
            <Text type="secondary">
              该原因会写入审计日志，用于后续统计误推荐类型和优化召回质量。
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
        okText: "记录不采用",
        cancelText: "取消",
        onOk: async () => {
          if (!reason.trim()) {
            Modal.warning({ title: "需要填写不采用原因" });
            throw new Error("reason required");
          }
          const candidateKey = evidenceCandidateKey(evidenceDrawer.key, material.id);
          setRejectingCandidateId(material.id);
          try {
            await rejectComplianceEvidenceCandidate(
              selectedProjectId,
              selectedSectionId,
              evidenceDrawer.key,
              material.id,
              { reason: reason.trim() }
            );
            setRejectedEvidenceCandidateKeys((current) => {
              const next = new Set(current);
              next.add(candidateKey);
              return next;
            });
            setEvidenceCandidates((current) => current.filter((candidate) => candidate.id !== material.id));
            appendLog(`不采用候选证据：${truncateText(material.name, 18)}`);
            await Promise.all([reloadAuditLogs(), reloadEvidenceQualityReports()]);
          } catch (error) {
            setApiError(error instanceof Error ? error.message : "候选证据反馈保存失败");
            throw error;
          } finally {
            setRejectingCandidateId("");
          }
        }
      });
    },
    [
      appendLog,
      evidenceDrawer,
      rejectingCandidateId,
      reloadAuditLogs,
      reloadEvidenceQualityReports,
      selectedProjectId,
      selectedSectionId,
      warnSectionLockedForEdit
    ]
  );

  const handleWaiveEvidenceRequirement = useCallback(
    (row: MatrixRow) => {
      if (!selectedProjectId || !selectedSectionId) return;
      if (warnSectionLockedForEdit()) return;
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
            dispatchAgentReviewRefresh();
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
      dispatchAgentReviewRefresh,
      evidenceDrawer?.key,
      refreshMatrixRelatedPanels,
      reloadMatrix,
      reloadMatrixReview,
      selectedProjectId,
      selectedSectionId,
      warnSectionLockedForEdit,
      waiveComplianceEvidenceRequirement
    ]
  );

  const handleUnbindEvidence = useCallback(
    (binding: ComplianceEvidenceBinding) => {
      if (warnSectionLockedForEdit()) return;
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
            dispatchAgentReviewRefresh();
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
      dispatchAgentReviewRefresh,
      evidenceDrawer,
      refreshAfterMatrixMutation,
      reloadEvidenceBindings,
      selectedProjectId,
      selectedSectionId,
      warnSectionLockedForEdit
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
    await unlinkDuplicateGroupItem(selectedProjectId, selectedSectionId, row.key, {
      reason: "人工判断该条与关联组存在差异，解除联动"
    });
    appendLog(`解除联动：${truncateText(row.requirement, 18)}`);
    await refreshAfterMatrixMutation();
  };

  const handleSplitDuplicateGroup = async (row: MatrixRow) => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
        profile_id: "engineering_construction_business_v1",
        outline: editedOutline ?? undefined,
        directives: editedDirectives ?? undefined
      });
      const outline = preview.outline_plan_json as { sections?: unknown[] };
      setContextPackPreview(preview);
      setContextPackPreviewOpen(true);
      appendLog(
        `预览投标素材包：${outline.sections?.length ?? 0} 个章节计划${editedOutline ? "（已编辑目录）" : ""}${editedDirectives && editedDirectives.length ? `（${editedDirectives.length} 条指令）` : ""}`
      );
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "投标素材包预览失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const outlineSectionsFromPreview = (
    preview: BusinessDraftContextPackPreview
  ): OutlineSeedChapter[] => {
    const outline = preview.outline_plan_json as { sections?: Record<string, unknown>[] };
    return (outline.sections ?? []).map((section) => ({
      section_type: String(section.section_type ?? ""),
      title: String(section.title ?? section.section_type ?? ""),
      custom: Boolean(section.custom)
    }));
  };

  const handleOpenOutlineEditor = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const preview = await previewBusinessDraftContextPack(selectedProjectId, selectedSectionId, {
        profile_id: "engineering_construction_business_v1",
        outline: editedOutline ?? undefined,
        directives: editedDirectives ?? undefined
      });
      setContextPackPreview(preview);
      setOutlineSeed(outlineSectionsFromPreview(preview));
      setOutlineEditorOpen(true);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "加载章节目录失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const handleImportDirectoryFromTender = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const derived = await deriveBusinessDraftDirectory(
        selectedProjectId,
        selectedSectionId,
        "engineering_construction_business_v1"
      );
      if (!derived.available) {
        const reasonMap: Record<string, string> = {
          no_tender_document: "未找到招标文件，请先上传招标文件",
          tender_not_parsed: "招标文件尚未完成解析，请先解析招标文件",
          no_chunks: "招标文件没有解析内容，请重新解析"
        };
        setApiError(reasonMap[derived.reason ?? ""] ?? "无法从招标文件推导目录");
        return;
      }
      const outline: OutlineChapterInput[] = derived.chapters.map((chapter) => ({
        section_type: chapter.section_type,
        title: chapter.title,
        custom: chapter.custom
      }));
      if (outline.length === 0) {
        setApiError("招标文件中未识别到「投标文件格式/响应文件组成」章节，建议手工编辑目录");
        return;
      }
      setEditedOutline(outline);
      const methodLabel =
        ({
          tender: "招标 / 投标文件",
          consultation: "竞争性磋商 / 响应文件",
          inquiry: "询价",
          unknown: "未识别"
        } as Record<string, string>)[derived.procurement_method ?? "unknown"] ??
        derived.procurement_method ??
        "未识别";
      appendLog(
        `已从招标文件推导目录：${outline.length} 章（采购方式：${methodLabel}）。请确认后再生成。`
      );
      const preview = await previewBusinessDraftContextPack(selectedProjectId, selectedSectionId, {
        profile_id: "engineering_construction_business_v1",
        outline,
        directives: editedDirectives ?? undefined
      });
      setContextPackPreview(preview);
      setOutlineSeed(outlineSectionsFromPreview(preview));
      setOutlineEditorOpen(true);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "从招标文件导入目录失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const handleApplyOutline = async (outline: OutlineChapterInput[]) => {
    setEditedOutline(outline);
    setOutlineEditorOpen(false);
    if (!selectedProjectId || !selectedSectionId) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const preview = await previewBusinessDraftContextPack(selectedProjectId, selectedSectionId, {
        profile_id: "engineering_construction_business_v1",
        outline,
        directives: editedDirectives ?? undefined
      });
      setContextPackPreview(preview);
      setContextPackPreviewOpen(true);
      appendLog(`已应用编辑后的目录：${outline.length} 个章节`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "应用目录失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const handleResetOutline = () => {
    setEditedOutline(null);
    appendLog("已重置章节目录为模板默认");
  };

  const directiveScopeOptions = useMemo<DirectiveScopeOption[]>(() => {
    const sections =
      activeContextPack?.section_context_packs.map((pack) => ({
        section_type: pack.section_type,
        title: pack.title
      })) ??
      ((contextPackPreview?.outline_plan_json as { sections?: Record<string, unknown>[] })?.sections ?? []).map(
        (section) => ({
          section_type: String(section.section_type ?? ""),
          title: String(section.title ?? section.section_type ?? "")
        })
      );
    const seen = new Set<string>();
    const options: DirectiveScopeOption[] = [];
    for (const section of sections) {
      if (!section.section_type || seen.has(section.section_type)) continue;
      seen.add(section.section_type);
      options.push({ value: section.section_type, label: `${section.title}（${section.section_type}）` });
    }
    return options;
  }, [activeContextPack, contextPackPreview]);

  const directiveSeed = useMemo<AuthorDirectiveInput[]>(() => {
    if (editedDirectives) return editedDirectives;
    const fromPack = (activeContextPack?.context_json?.author_directives as
      | Array<{ scope?: unknown; directive_type?: unknown; text?: unknown }>
      | undefined) ?? [];
    return fromPack.map((directive) => ({
      scope: String(directive.scope ?? "pack"),
      directive_type: (directive.directive_type as AuthorDirectiveInput["directive_type"]) ?? "style",
      text: String(directive.text ?? "")
    }));
  }, [editedDirectives, activeContextPack]);

  const activePackDirectiveCount = useMemo(() => {
    const fromPack = activeContextPack?.context_json?.author_directives;
    return Array.isArray(fromPack) ? fromPack.length : 0;
  }, [activeContextPack]);

  const handleApplyDirectives = async (directives: AuthorDirectiveInput[]) => {
    setDirectiveEditorOpen(false);
    if (!selectedProjectId || !selectedSectionId) return;
    if (warnSectionLockedForEdit()) return;
    // When a pack is already confirmed, editing directives triggers a lightweight rebuild.
    if (activeContextPack) {
      setLoadingContextPack(true);
      setApiError("");
      try {
        const rebuilt = await updateBusinessDraftContextPackDirectives(
          selectedProjectId,
          selectedSectionId,
          activeContextPack.id,
          directives
        );
        setBusinessDraftContextPacks([rebuilt]);
        setEditedDirectives(null);
        setCoverageReview(null);
        appendLog(
          `指令已更新（快速重新生成）：${directives.length} 条，沿用已核实的事实，请重新生成草稿以应用新指令`
        );
        await reloadAuditLogs();
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "指令更新失败");
      } finally {
        setLoadingContextPack(false);
      }
      return;
    }
    // No confirmed pack yet: stage directives for the next preview/confirm.
    setEditedDirectives(directives.length ? directives : null);
    appendLog(`已暂存生成指令：${directives.length} 条，将随预览/确认投标素材包应用`);
  };

  const handleResetDirectives = () => {
    if (warnSectionLockedForEdit()) return;
    setEditedDirectives(null);
    appendLog("已清空暂存的生成指令");
  };

  const handleCreateContextPack = async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (warnSectionLockedForEdit()) return;
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
        profile_id: "engineering_construction_business_v1",
        outline: editedOutline ?? undefined,
        directives: editedDirectives ?? undefined
      });
      setBusinessDraftContextPacks([contextPack]);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      setEditedOutline(null);
      setEditedDirectives(null);
      setCoverageReview(null);
      appendLog(`确认投标素材包：${contextPack.section_context_packs.length} 个章节上下文`);
      await reloadAuditLogs();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "投标素材包生成失败");
    } finally {
      setLoadingContextPack(false);
    }
  };

  const openContextPackDraftGenerationConfirm = () => {
    if (!activeContextPack || !selectedProjectId || !selectedSectionId) return;
    if (warnSectionLockedForEdit()) return;
    const isBlocked = activeContextPack.readiness_status === "block" || qualificationDecisionIsNoGo;
    Modal.confirm({
      title: isBlocked ? "生成内部草稿" : "按投标素材包生成草稿",
      content: isBlocked
        ? "当前投标素材包或资格结论仍存在阻塞项。本次只生成带待补占位的内部草稿，不代表可提交版本。"
        : "将按已确认的投标素材包生成结构化章节和可追溯 block，生成后会执行覆盖检查。",
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
          setApiError(error instanceof Error ? error.message : "投标素材包草稿生成失败");
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
    if (warnSectionLockedForEdit()) return;
    setLoadingContextPack(true);
    setApiError("");
    try {
      const review = await runBusinessDraftContextPackCoverageReview(
        selectedProjectId,
        selectedSectionId,
        activeContextPack.id
      );
      setCoverageReview(review);
      appendLog(`执行投标素材包覆盖检查：${review.status}`);
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
    if (warnSectionLockedForEdit()) return;
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

  // P1：标记某草稿块为"已查看"——受保护批量确认的前置依据
  const markDraftBlockViewed = useCallback((blockId: string) => {
    setViewedDraftBlockIds((prev) => {
      if (prev.has(blockId)) return prev;
      const next = new Set(prev);
      next.add(blockId);
      return next;
    });
  }, []);

  const toggleDraftBlockExpanded = useCallback((blockId: string) => {
    setExpandedDraftBlockIds((prev) => {
      const next = new Set(prev);
      if (next.has(blockId)) next.delete(blockId);
      else next.add(blockId);
      return next;
    });
  }, []);

  // P1：受保护批量确认——仅"已查看"的待确认指定内容可确认；未查看项阻止并提示
  const handleBatchConfirmMandatory = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const targets = chapterMandatoryBlocks;
    if (!targets.length) {
      Modal.info({ title: "无待确认的指定内容", content: "本章当前没有需要确认的指定内容。" });
      return;
    }
    const unviewed = targets.filter((block) => !viewedDraftBlockIds.has(block.id));
    if (unviewed.length > 0) {
      Modal.warning({
        title: "存在未查看项，无法批量确认",
        content: `还有 ${unviewed.length} 处指定内容尚未逐条查看。请先点击「逐条查看」浏览全部内容后再批量确认。`
      });
      appendLog(`拦截批量确认：${unviewed.length} 处指定内容未查看`);
      return;
    }
    Modal.confirm({
      title: `批量确认 ${targets.length} 处指定内容`,
      content: "这些内容会原样写入标书。确认即表示你已逐条核对其措辞与事实无误。",
      okText: "全部确认",
      cancelText: "取消",
      onOk: async () => {
        setSavingBusinessDraft(true);
        setApiError("");
        try {
          for (const block of targets) {
            const updated = await updateBusinessDraftBlock(selectedProjectId, selectedSectionId, block.id, {
              review_status: "approved",
              content_text: null,
              reason: "批量确认已逐条查看的指定内容"
            });
            setDraftBlocks((blocks) => blocks.map((item) => (item.id === updated.id ? updated : item)));
          }
          appendLog(`批量确认 ${targets.length} 处指定内容`);
          await reloadAuditLogs();
          notification.success({
            message: "指定内容已确认",
            description: `已确认 ${targets.length} 处必须原样写入的内容。`,
            placement: "topRight"
          });
        } catch (error) {
          setApiError(error instanceof Error ? error.message : "批量确认指定内容失败");
        } finally {
          setSavingBusinessDraft(false);
        }
      }
    });
  }, [
    appendLog,
    chapterMandatoryBlocks,
    reloadAuditLogs,
    selectedProjectId,
    selectedSectionId,
    viewedDraftBlockIds
  ]);

  // P1：逐条查看聚焦流入口——从第一个未查看的指定内容开始
  const openMandatoryReview = useCallback(() => {
    if (!chapterMandatoryBlocks.length) {
      Modal.info({ title: "无待确认的指定内容", content: "本章当前没有需要逐条查看的指定内容。" });
      return;
    }
    const firstUnviewed = chapterMandatoryBlocks.findIndex((block) => !viewedDraftBlockIds.has(block.id));
    setMandatoryReviewIndex(firstUnviewed >= 0 ? firstUnviewed : 0);
    setMandatoryReviewOpen(true);
  }, [chapterMandatoryBlocks, viewedDraftBlockIds]);

  // P1：逐条查看流打开/翻页时，把当前展示的指定内容标记为"已查看"
  useEffect(() => {
    if (!mandatoryReviewOpen) return;
    const block = chapterMandatoryBlocks[mandatoryReviewIndex];
    if (block) markDraftBlockViewed(block.id);
  }, [mandatoryReviewOpen, mandatoryReviewIndex, chapterMandatoryBlocks, markDraftBlockViewed]);

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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
    setGeneratingDecision(true);
    try {
      const decision = await generateQualificationDecision(selectedProjectId, selectedSectionId);
      suppressNextWorkflowAdvanceFromRef.current = "qualification";
      setQualificationDecision(decision);
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog(`生成参标建议：${decisionLabels[decision.recommendation] ?? decision.recommendation}`);
      await Promise.all([reloadApprovalTasks(), reloadAuditLogs(), reloadQualificationEvaluations()]);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "参标建议生成失败");
    } finally {
      setGeneratingDecision(false);
    }
  };

  const confirmNoGoRiskAcceptance = (onContinue: () => void) => {
    if (!qualificationDecision) return;
    let reason = "";
    Modal.confirm({
      title: "参标建议为不建议参标，仍继续？",
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
        appendLog(`不建议参标·风险接受：${truncateText(reason.trim(), 36)}`);
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
        appendLog("请先确认投标素材包并完成草稿生成，再进入导出审批。");
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

  const handleProjectTodoAction = (item: ProjectTodoAction) => {
    if (item.source === "preflight") {
      const preflightItem = preflightChecksForDisplay.find((check) => check.code === item.code);
      if (preflightItem) {
        handlePreflightCheckAction(preflightItem);
        return;
      }
    }
    if (!isWorkflowStepKey(item.target)) {
      appendLog("该质量待办暂未绑定处理页面");
      return;
    }
    activateWorkflowStep(item.target);
  };

  const handleConfirmQualificationDecision = () => {
    if (!selectedProjectId || !selectedSectionId || !qualificationDecision) return;
    if (warnSectionLockedForEdit()) return;
    let reason = "人工确认参标建议";
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
        appendLog("确认参标建议");
        await Promise.all([reloadApprovalTasks(), reloadAuditLogs()]);
      }
    });
  };

  const handleConfirmQualificationEvaluation = (evaluation: QualificationEvaluation) => {
    if (warnSectionLockedForEdit()) return;
    let reason = "人工确认资格预评估结果";
    Modal.confirm({
      title: "确认评估结果",
      content: (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Text>{truncateText(evaluation.requirement_text, 64)}</Text>
          <Text type="secondary">确认动作会写入审计日志，后续参标建议会优先读取人工确认状态。</Text>
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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

  const tenderFormatExportModeLabel = (exportMode: TenderFormatDocxExportMode) =>
    exportMode === "submission" ? "正式版" : "审阅版";

  const renderTenderFormatExportConfirmation = (
    exportMode: TenderFormatDocxExportMode,
    summary: SectionQualitySummary
  ) => {
    const blockers = summary.checks.filter((check) => check.status === "block");
    const warnings = summary.checks.filter((check) => check.status === "warn");
    const materials = Array.isArray(summary.material_summary.materials)
      ? summary.material_summary.materials
      : [];
    const selectedCount = summaryNumber(summary.material_summary, "selected_count");
    const embeddableCount = summaryNumber(summary.material_summary, "embeddable_count");
    const scoringIndexCount = summaryNumber(summary.export_preview, "scoring_index_count");
    const placeholderCount = summaryNumber(summary.export_preview, "placeholder_count");
    const pagerefNote =
      typeof summary.export_preview.pageref_note === "string"
        ? summary.export_preview.pageref_note
        : "评分索引页码由 Word/LibreOffice 分页引擎更新。";
    const alertType =
      exportMode === "submission" && summary.status === "block"
        ? "error"
        : summary.status === "pass"
          ? "success"
          : "warning";

    return (
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Alert
          type={alertType}
          showIcon
          message={`标书质量体检：${summary.status_label || sectionQualityStatusLabel(summary.status)}`}
          description={summary.summary}
        />
        <div className="export-confirm-grid">
          <div>
            <Text type="secondary">导出模式</Text>
            <strong>{tenderFormatExportModeLabel(exportMode)}</strong>
          </div>
          <div>
            <Text type="secondary">嵌入材料</Text>
            <strong>
              {embeddableCount}/{selectedCount}
            </strong>
          </div>
          <div>
            <Text type="secondary">评分索引</Text>
            <strong>{scoringIndexCount} 项</strong>
          </div>
          <div>
            <Text type="secondary">剩余占位</Text>
            <strong>{placeholderCount}</strong>
          </div>
        </div>

        <div className="export-confirm-section">
          <Text strong>将嵌入/引用的材料</Text>
          <div className="export-confirm-list">
            {materials.length ? (
              materials.slice(0, 6).map((material: SectionQualityMaterial) => (
                <div key={material.material_id}>
                  <span>{material.material_name}</span>
                  <Tag color={material.embeddable ? "green" : "gold"}>
                    {material.embeddable ? "可嵌入" : "待检查"}
                  </Tag>
                </div>
              ))
            ) : (
              <Text type="secondary">本次未识别到可嵌入的证照/证明材料。</Text>
            )}
            {materials.length > 6 && <Text type="secondary">还有 {materials.length - 6} 项材料会在导出诊断中列出。</Text>}
          </div>
        </div>

        <div className="export-confirm-section">
          <Text strong>阻断项</Text>
          {blockers.length ? (
            <div className="export-confirm-list">
              {blockers.slice(0, 5).map((check: SectionQualityCheck) => (
                <div key={check.code}>
                  <span>{check.title}</span>
                  <Tag color="red">{check.count || "阻断"}</Tag>
                  <Text type="secondary">{check.message}</Text>
                </div>
              ))}
            </div>
          ) : (
            <Text type="secondary">未发现正式稿硬阻断。</Text>
          )}
        </div>

        <div className="export-confirm-section">
          <Text strong>可接受风险</Text>
          {warnings.length ? (
            <div className="export-confirm-list">
              {warnings.slice(0, 5).map((check: SectionQualityCheck) => (
                <div key={check.code}>
                  <span>{check.title}</span>
                  <Tag color="gold">{check.count || "复核"}</Tag>
                  <Text type="secondary">{check.message}</Text>
                </div>
              ))}
            </div>
          ) : (
            <Text type="secondary">没有待复核项。</Text>
          )}
        </div>

        <Alert type="info" showIcon message="PAGEREF 更新提示" description={pagerefNote} />
      </Space>
    );
  };

  const confirmTenderFormatExport = (
    exportMode: TenderFormatDocxExportMode,
    summary: SectionQualitySummary
  ) =>
    new Promise<boolean>((resolve) => {
      const submissionBlocked = exportMode === "submission" && summary.status === "block";
      Modal.confirm({
        title: submissionBlocked ? "正式版导出被阻断" : `导出前确认：${tenderFormatExportModeLabel(exportMode)}`,
        width: 760,
        content: renderTenderFormatExportConfirmation(exportMode, summary),
        okText: submissionBlocked ? "处理阻断后再导出" : `确认导出${tenderFormatExportModeLabel(exportMode)}`,
        cancelText: "取消",
        okButtonProps: {
          disabled: submissionBlocked,
          danger: submissionBlocked
        },
        onOk: () => {
          resolve(!submissionBlocked);
        },
        onCancel: () => {
          resolve(false);
        }
      });
    });

  const handleExportTenderFormatDocx = async (exportMode: TenderFormatDocxExportMode) => {
    if (!selectedProjectId || !selectedSectionId) return;
    setExportingTenderFormatMode(exportMode);
    try {
      const qualitySummary = await reloadSectionQualitySummary();
      if (!qualitySummary) return;
      const confirmed = await confirmTenderFormatExport(exportMode, qualitySummary);
      if (!confirmed) return;
      const exportFile = await exportTenderFormatDocx(selectedProjectId, selectedSectionId, {
        export_mode: exportMode
      });
      appendLog(`导出格式标装配 ${exportMode === "review" ? "审阅版" : "正式版"}：${exportFile.file_name}`);
      await Promise.all([
        reloadDocumentsAndExports(),
        reloadAuditLogs(),
        reloadPreflightCheck(),
        reloadSectionQualitySummary({ silent: true })
      ]);
      window.open(`/api/v1/projects/${selectedProjectId}/export-files/${exportFile.id}/download`, "_blank");
    } catch (error) {
      setApiError(errorMessage(error, "格式标装配导出失败"));
      void reloadSectionQualitySummary({ silent: true });
    } finally {
      setExportingTenderFormatMode("");
    }
  };

  const handleDecideApprovalTask = (task: ApprovalTask, action: "approve" | "reject") => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (warnSectionLockedForEdit()) return;
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
      appendLog("查看技术响应预览；产品选型、图纸和技术标章节仍需专项能力支持");
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
    appendLog(`流程助手记录只读请求：${prompt}；当前仅用于流程导航，不写入项目数据`);
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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
    if (warnSectionLockedForEdit()) return;
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

  const openWorkspace = (tab: string = "matrix") => {
    const safeTab = isWorkflowStepKey(tab) ? tab : "matrix";
    setViewMode("workspace");
    setActiveTab(safeTab);
    const workspaceTabs = new Set<WorkflowStepKey>(["approval", "chapter", "evidence", "review", "documents", "tasks", "quality", "qualification"]);
    setWorkspaceNode(workspaceTabs.has(safeTab) ? safeTab : "matrix");
  };

  const openProjectWorkspace = (projectId: string, tab: string = "matrix") => {
    const safeTab = isWorkflowStepKey(tab) ? tab : "matrix";
    const sameProject = projectId === selectedProjectId;
    const sectionId = sameProject ? selectedSectionId ?? sections[0]?.id : undefined;
    setSelectedProjectId(projectId);
    setSelectedSectionId(sectionId);
    setViewMode("workspace");
    setActiveTab(safeTab);
    setSelectedTreeKey(sectionId ? `section:${sectionId}:${safeTab}` : "");
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
    setProjectImportError("");
    setImportUrl("");
    setImportUrlSite("");
  };

  const openCreateProjectModal = (mode: ProjectCreateMode = "file") => {
    resetNewProjectDraft();
    setProjectCreateMode(mode);
    setNewProjectOpen(true);
  };

  const applyImportDraft = (draft: ProjectImportDraft) => {
    setProjectImportDraft(draft);
    setProjectImportError("");
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
    setProjectImportError("");
    setApiError("");
    createProjectImportDraftFromFile(file)
      .then((draft) => {
        applyImportDraft(draft);
        appendLog(`从文件识别项目信息：${draft.source.original_filename}`);
      })
      .catch((error: unknown) => {
        const message = errorMessage(error, "文件导入识别失败");
        setProjectImportError(message);
        setApiError(message);
        notification.error({
          message: "招标文件导入失败",
          description: message,
          placement: "topRight"
        });
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
    setProjectImportError("");
    setApiError("");
    try {
      const draft = await createProjectImportDraftFromUrl({
        source_url: importUrl.trim(),
        source_site: importUrlSite || null,
        title: "公告导入项目"
      });
      applyImportDraft(draft);
      appendLog("从网页或公告链接识别项目信息");
    } catch (error) {
      const message = errorMessage(error, "网页导入识别失败");
      setProjectImportError(message);
      setApiError(message);
      notification.error({
        message: "网页导入失败",
        description: message,
        placement: "topRight"
      });
    } finally {
      setImportingProjectDraft(false);
    }
  };

  const handleBatchConfirm = () => {
    if (warnSectionLockedForEdit()) return;
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
    if (!projectImportDraft) {
      Modal.warning({ title: projectCreateMode === "file" ? "请先上传招标文件并完成识别" : "请先完成导入识别" });
      return;
    }
    setSavingProject(true);
    try {
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

  const handleConfirmProjectDeletion = async () => {
    const projectIds = projectDeleteTargets.map((project) => project.id);
    if (!projectIds.length) return;
    await executeProjectDeletion(projectIds);
    setProjectDeleteTargets([]);
  };

  const confirmDeleteProjects = (projectIds: string[]) => {
    const targetProjects = projects.filter((project) => projectIds.includes(project.id));
    if (!targetProjects.length) return;
    setProjectDeleteTargets(targetProjects);
  };

  const handleUploadDocument: UploadProps["customRequest"] = async (options) => {
    if (!(options.file instanceof File)) {
      const message = "请选择要上传的 Word/PDF 文件。";
      options.onError?.(new Error(message));
      Modal.warning({ title: "文件无效", content: message });
      return;
    }
    if (!selectedProjectId || !selectedSectionId) {
      const message = "请先选择项目和标段，再上传招标文件。";
      options.onError?.(new Error(message));
      setApiError(message);
      Modal.warning({ title: "无法上传招标文件", content: message });
      return;
    }
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
      const message = errorMessage(error, "文件上传或解析失败");
      setApiError(message);
      notification.error({
        message: "文件上传或解析失败",
        description: message,
        placement: "topRight"
      });
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

  const runAutoResolveMatrix = async (options?: { source?: ProjectDocument | null; auto?: boolean }) => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (autoResolveInFlightRef.current) return;
    const projectId = selectedProjectId;
    const sectionId = selectedSectionId;
    const source = options?.source ?? null;
    const auto = options?.auto ?? false;
    const version = source?.current_version;
    autoResolveInFlightRef.current = true;
    setAutoResolveActive(true);
    setAutoResolveResult(null);
    try {
      let task = await autoResolveComplianceMatrix(projectId, sectionId, {
        document_id: source?.id,
        document_version_id: version?.id,
        async_processing: true
      });
      appendLog(`${auto ? "自动触发" : "手动触发"} Agent 自处理任务：${task.id.slice(0, 8)}`);
      const deadline = Date.now() + 15 * 60 * 1000;
      while (!isAsyncTaskTerminalStatus(task.status) && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 2500));
        try {
          task = await getTask(task.id);
        } catch {
          // 单次轮询失败忽略，下次重试
        }
      }
      if (task.status === "failed") {
        throw new Error(task.error_message || "自动处理失败");
      }
      const output = (task.output_json ?? {}) as Partial<MatrixAutoResolveResult>;
      const result: MatrixAutoResolveResult = {
        resolved: Boolean(output.resolved),
        rounds: Array.isArray(output.rounds) ? (output.rounds as MatrixAutoResolveRound[]) : [],
        round_count: typeof output.round_count === "number" ? output.round_count : 0,
        remaining_count: typeof output.remaining_count === "number" ? output.remaining_count : 0,
        remaining_issues: Array.isArray(output.remaining_issues)
          ? (output.remaining_issues as MatrixAutoResolveRemainingIssue[])
          : [],
        quality_status: output.quality_status
      };
      setAutoResolveResult(result);
      const [items] = await Promise.all([
        listComplianceItems(projectId, sectionId, { limit: COMPLIANCE_ITEM_FETCH_LIMIT }),
        reloadExtractionQuality(),
        reloadDocumentsAndExports(),
        reloadAuditLogs(),
        getPreflightCheck(projectId, sectionId).then(setPreflightCheck).catch(() => undefined),
        activeTab === "review" ? reloadMatrixReview() : Promise.resolve()
      ]);
      setComplianceItems(items);
      if (result.resolved) {
        Modal.success({
          title: "Agent 已自动处理完成，质量门禁通过",
          content: `共 ${result.round_count} 轮自动处理，已无阻断项，可继续进入合规矩阵。`
        });
      } else if (!auto) {
        // 仅手动再试给出弹窗提示；自动模式失败时由页面内“转人工”区域承接，避免打断。
        Modal.warning({
          title: "Agent 已尽力处理，仍有阻断项需人工确认",
          content: `共 ${result.round_count} 轮自动处理，仍剩 ${result.remaining_count} 处阻断。请在下方逐条核对或手动处理。`
        });
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "自动处理失败");
      await reloadExtractionQuality();
    } finally {
      setAutoResolveActive(false);
      autoResolveInFlightRef.current = false;
    }
  };

  // 用户手动“再试一次”：直接跑一轮，不计入自动预算。
  const handleAutoResolveMatrix = (source?: ProjectDocument | null) => {
    void runAutoResolveMatrix({ source, auto: false });
  };

  // Loop engineering：当前标段存在阻断报告即自动唤起 Agent 处理，并把界面切到质检页，
  // 让用户实时看到处理过程；每个标段最多自动尝试 AUTO_RESOLVE_AUTO_ATTEMPT_LIMIT 次
  //（每次后端再内部复检至多 2 轮），超出后停手并把控制权交还用户手动处理。
  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    if (!extractionBlocked) return;
    if (importProcessingInProgress) return;
    if (autoResolveActive || autoResolveInFlightRef.current) return;
    const sectionId = selectedSectionId;
    const attempts = autoResolveAutoAttemptsRef.current[sectionId] ?? 0;
    if (attempts >= AUTO_RESOLVE_AUTO_ATTEMPT_LIMIT) return;
    autoResolveAutoAttemptsRef.current[sectionId] = attempts + 1;
    // Agent 开始自动处理时自动跳到质检界面（如果还不在该页）。
    if (activeTab !== "quality") {
      activateWorkflowStep("quality");
    }
    void runAutoResolveMatrix({ auto: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, extractionBlocked, importProcessingInProgress, selectedProjectId, selectedSectionId, autoResolveActive]);

  // 引导式推进：当用户正停在「当前阻塞步骤」上、且该步骤被解决（推荐步骤前移）时，
  // 自动跳到新的阻塞步骤。仅在用户处于刚被清除的那一步时推进，避免在别处浏览时被打断。
  useEffect(() => {
    const prevKey = prevRecommendedStepKeyRef.current;
    const nextKey = recommendedStep?.key ?? null;
    prevRecommendedStepKeyRef.current = nextKey;
    if (!nextKey || !prevKey || prevKey === nextKey) {
      if (suppressNextWorkflowAdvanceFromRef.current === prevKey) {
        suppressNextWorkflowAdvanceFromRef.current = null;
      }
      return;
    }
    if (suppressNextWorkflowAdvanceFromRef.current === prevKey) {
      suppressNextWorkflowAdvanceFromRef.current = null;
      return;
    }
    // Agent 自动处理进行中时不抢跳，等其完成（完成后会重算推荐步骤再前进）。
    if (autoResolveActive || autoResolveInFlightRef.current) return;
    if (activeTab !== prevKey || activeTab === nextKey) return;
    // 仅当用户所停的上一步确实已完成（done）才前进，避免数据刷新时推荐步骤瞬时抖动导致误跳。
    const prevStep = workflowSteps.find((step) => step.key === prevKey);
    if (prevStep?.status !== "done") return;
    activateWorkflowStep(nextKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recommendedStep, activeTab, autoResolveActive, workflowSteps]);

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

  const handleHistoryMaterialUpload: UploadProps["customRequest"] = async (options) => {
    if (!(options.file instanceof File)) return;
    setExtractingHistoryMaterial(true);
    setHistoryExtractResult(null);
    setHistoryExtractTaskId(null);
    setHistoryExtractTask(null);
    try {
      const task = await createEnterpriseMaterialsHistoryExtractTask({
        file: options.file,
        dataLevel: "internal"
      });
      setHistoryExtractTaskId(task.id);
      setHistoryExtractTask(task);
      options.onSuccess?.(task, options.file);
      appendLog(`历史资料抽取任务已创建：${taskShortId(task.id)}`);
      notification.info({
        message: "历史资料开始抽取",
        description: "系统会在后台逐页 OCR/整理资料，完成后自动刷新企业资料表。",
        placement: "topRight",
        duration: 5
      });
    } catch (error) {
      options.onError?.(error as Error);
      setApiError(error instanceof Error ? error.message : "历史资料抽取失败");
    } finally {
      setExtractingHistoryMaterial(false);
    }
  };

  const handleConfirmExtractedMaterial = async (material: EnterpriseMaterial) => {
    setConfirmingMaterialId(material.id);
    try {
      const updated = await updateEnterpriseMaterial(material.id, {
        verification_status: "confirmed",
        reason: "人工核对历史资料抽取结果并确认入库"
      });
      setEnterpriseMaterials((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setContextPackPreview(null);
      setContextPackPreviewOpen(false);
      appendLog(`确认历史资料草稿：${updated.name}`);
      notification.success({ message: "资料已确认", description: "已进入企业资料库，可参与后续检索和证据推荐。" });
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业资料确认失败");
    } finally {
      setConfirmingMaterialId("");
    }
  };

  const handleRebuildMaterialIndex = async () => {
    setRebuildingMaterialIndex(true);
    try {
      const result = await rebuildEnterpriseMaterialIndex();
      setMaterialIndexHealth(result.health);
      await reloadEnterprise();
      appendLog(`重建企业资料索引：${result.rebuilt_material_count} 条资料，${result.rebuilt_chunk_count} 个切片`);
      notification.success({
        message: "企业资料索引已重建",
        description: `${result.rebuilt_material_count} 条已确认资料进入 ${result.embedding_model} / ${result.embedding_dimensions} 维检索索引。`
      });
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "企业资料索引重建失败");
    } finally {
      setRebuildingMaterialIndex(false);
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

  const app = {
    actionLogs,
    activateProjectWorkspace,
    activateReviewHighlight,
    activateWorkflowStep,
    activeContextPack,
    activeDraftBlockId,
    activePackDirectiveCount,
    activeReviewItemId,
    activeTab,
    Alert,
    allMatrixReviewRows,
    apiError,
    appendLog,
    applyChatModelConfig,
    applyImportDraft,
    applyProjectList,
    applySimilarCandidates,
    approvalBusyId,
    approvalStatusLabels,
    approvalTasks,
    approvalTaskTypeLabels,
    assignComplianceItem,
    assistantCollapsed,
    assistantMessages,
    ASYNC_TASK_STALE_AFTER_MS,
    asyncTaskEtaText,
    asyncTaskProgress,
    asyncTaskStatusColors,
    asyncTaskStatusLabels,
    asyncTaskStatusText,
    auditActionText,
    auditContentText,
    auditLogs,
    AuditOutlined,
    Avatar,
    Badge,
    BarChartOutlined,
    BellOutlined,
    bindComplianceEvidence,
    bindingMaterialId,
    blockingContextPackChecks,
    blockingQualificationEvaluations,
    blockingSummary,
    blockToReviewChunk,
    BranchesOutlined,
    buildCurrentConfirmationQueue,
    buildMatrixReviewRows,
    buildMatrixTableRows,
    bulkAssignComplianceItems,
    bulkConfirmComplianceItems,
    businessDraftChapters,
    businessDraftContextPacks,
    businessDraftGenerationActive,
    businessDraftGenerationProgress,
    businessDraftGenerationStatusText,
    businessDraftGenerationTask,
    businessDraftGenerationTaskId,
    businessDraftTerminalTaskRef,
    Button,
    canConfirmContextPack,
    candidateIncludeRestricted,
    candidateIncludeUnconfirmed,
    canGenerateContextPackDraft,
    chapterMandatoryBlocks,
    chapterStatusLabels,
    chatModelConfig,
    Checkbox,
    CheckCircleOutlined,
    classifyProjectGroup,
    ClockCircleOutlined,
    CloseOutlined,
    CloudUploadOutlined,
    CommentOutlined,
    COMPLIANCE_ITEM_FETCH_LIMIT,
    complianceItems,
    computeDashboardStats,
    computeDraftBlockFilterCounts,
    confirmComplianceItem,
    confirmContextPackDraftGeneration,
    confirmDeleteProjects,
    confirmDraftGeneration,
    confirmDuplicateGroup,
    confirmExport,
    confirmingMaterialId,
    confirmNoGoRiskAcceptance,
    confirmProjectImportDraft,
    confirmQualificationDecision,
    confirmQualificationEvaluation,
    confirmSubmit,
    Content,
    contextPackCheckActionText,
    contextPackChecks,
    contextPackConfirmDisabledReason,
    contextPackDraftGenerationAvailable,
    contextPackDraftGenerationTip,
    contextPackHardBlockers,
    contextPackOutlineSections,
    contextPackPreview,
    contextPackPreviewChecks,
    ContextPackPreviewDrawer,
    contextPackPreviewOpen,
    contextPackProjectFields,
    contextPackQualificationGate,
    contextPackReadinessSummary,
    contextPackSource,
    contextTitle,
    coverageReview,
    createApprovalTask,
    createBusinessDraftContextPack,
    createComplianceItemFromSource,
    createEnterpriseMaterial,
    createEnterpriseMaterialsHistoryExtractTask,
    createParseTask,
    createProject,
    createProjectImportDraftFromFile,
    createProjectImportDraftFromUrl,
    currentImportProcessing,
    currentProject,
    currentSection,
    dashboardStats,
    dataLevelLabels,
    DatePicker,
    dayjs,
    decideApprovalTask,
    decisionColors,
    decisionLabels,
    DeleteOutlined,
    deleteProject,
    deletingProjects,
    deriveProjectNextStep,
    DirectiveEditorModal,
    directiveEditorOpen,
    directiveScopeOptions,
    directiveSeed,
    displayedLogs,
    displayedMatrixRows,
    documentBusy,
    documents,
    DownloadOutlined,
    draftBlockFilter,
    draftBlockFilterCounts,
    draftBlockFilterLabels,
    draftBlockLinkIds,
    draftBlocks,
    draftBlocksByComplianceItemId,
    draftBlockStatusColors,
    draftBlockStatusLabels,
    draftEditorValue,
    Drawer,
    duplicateGroupByItemId,
    editDraft,
    editedDirectives,
    editedOutline,
    effectiveReviewHighlights,
    Empty,
    enterpriseMaterials,
    enterpriseProfile,
    errorMessage,
    evaluatingQualification,
    evidenceBindings,
    EvidenceCandidatePanel,
    evidenceCandidates,
    evidenceDrawer,
    evidenceFeedbackReport,
    evidenceRetrievalEvaluation,
    evidenceRows,
    executeProjectDeletion,
    expandedDraftBlockIds,
    explanationKeywords,
    explanationText,
    exportBusinessDraftWord,
    exportComplianceMatrixExcel,
    exportFiles,
    exportingExcel,
    exportingTenderFormatMode,
    exportingWord,
    extractDocumentSemanticSectionCompliance,
    extractingHistoryMaterial,
    extractionBlocked,
    extractionBlockReason,
    extractionQualityIssueCount,
    extractionQualityIssues,
    extractionQualityReport,
    factCheckLabels,
    fetchEvidenceCandidates,
    FileDoneOutlined,
    FileSearchOutlined,
    FileTextOutlined,
    filteredHomeProjects,
    filteredRevisionChunks,
    filterHomeProjects,
    findNextUnresolvedMatrixRow,
    focusAutoConfirmationRow,
    focusDraftBlock,
    focusQualityAssistant,
    focusReviewChunk,
    focusReviewRow,
    FolderOpenOutlined,
    formatDateTime,
    formatShortTime,
    Fragment,
    generateBusinessDraftChapters,
    generateBusinessDraftFromContextPackAsync,
    generateComplianceMatrix,
    generateQualificationDecision,
    generatingDecision,
    getChatModelConfig,
    getDocumentExtractionQualityReport,
    getEnterpriseMaterialIndexHealth,
    getEnterpriseProfile,
    getMatrixReview,
    getPreflightCheck,
    getProject,
    getQualificationDecision,
    getTask,
    handleApplyDirectives,
    handleApplyOutline,
    handleApplySimilarCandidates,
    handleAssignItem,
    handleAssistantMessageAction,
    handleBatchAssign,
    handleBatchConfirm,
    handleBatchConfirmMandatory,
    handleBindEvidence,
    handleConfirmDuplicateGroup,
    handleConfirmExtractedMaterial,
    handleConfirmItem,
    handleConfirmProjectDeletion,
    handleConfirmQualificationDecision,
    handleConfirmQualificationEvaluation,
    handleContextPackCheckAction,
    handleCreateContextPack,
    handleCreateEnterpriseMaterial,
    handleCreateProject,
    handleCreateSourceItem,
    handleDecideApprovalTask,
    handleExportBusinessWord,
    handleExportBusinessWordConfirmed,
    handleExportExcel,
    handleExportTenderFormatDocx,
    handleExtractSemanticSection,
    handleAutoResolveMatrix,
    autoResolveActive,
    autoResolveResult,
    handleGenerateMatrix,
    handleGenerateQualificationDecision,
    handleHistoryMaterialUpload,
    handleImportDirectoryFromTender,
    handleImportDraftFile,
    handleImportDraftUrl,
    handleOpenOutlineEditor,
    handleOpenRevisionDrawer,
    handlePreflightCheckAction,
    handleProjectTodoAction,
    handlePreviewContextPack,
    handlePublicUrlAcquisition,
    handlePublishManualRevision,
    handleQuickPrompt,
    handleRejectEvidenceCandidate,
    handleRebuildMaterialIndex,
    handleReparseDocument,
    handleReplanSemanticSections,
    handleResetDirectives,
    handleResetOutline,
    handleReviewBlockMouseUp,
    handleReviewChunkMouseUp,
    handleRunContextPackCoverageReview,
    handleRunDraftFactCheck,
    handleRunQualificationEvaluation,
    handleSaveBusinessDraftChapter,
    handleSaveEditDraft,
    handleSaveEnterpriseProfile,
    handleSaveKeyInfo,
    handleSaveModelConfig,
    handleSplitDuplicateGroup,
    handleTestModelConfig,
    handleToggleCandidateRestricted,
    handleToggleCandidateUnconfirmed,
    handleUnbindEvidence,
    handleUnlinkDuplicateGroup,
    handleUpdateDraftBlockStatus,
    handleUploadDocument,
    handleWaiveEvidenceRequirement,
    Header,
    hiddenPreflightCheckCount,
    hiddenProjectTodoActionCount,
    highlightedRowKey,
    HighlightOutlined,
    historyExtractActive,
    historyExtractProgress,
    historyExtractResult,
    historyExtractResultFromTask,
    historyExtractStatusText,
    historyExtractTask,
    historyExtractTaskId,
    historyExtractTaskStageTitle,
    historyExtractTerminalTaskRef,
    homeProjectGroup,
    homeProjectPage,
    homeProjectPageSize,
    homeProjectSearch,
    homeTodoRows,
    IMPORT_PROCESSING_STORAGE_KEY,
    importingProjectDraft,
    importProcessing,
    importProcessingDone,
    importProcessingFailed,
    importProcessingHasActiveTask,
    importProcessingInProgress,
    importProcessingMatrixFailed,
    importProcessingOpenTask,
    importProcessingParseFailed,
    importProcessingPercent,
    importProcessingProgress,
    importProcessingQualityBlocked,
    importProcessingStageMessage,
    importProcessingStageTitle,
    importProcessingVisible,
    importUrl,
    importUrlSite,
    Input,
    isAsyncTaskActive,
    isAsyncTaskStale,
    isAsyncTaskTerminal,
    isAsyncTaskTerminalStatus,
    isHttpNotFound,
    isHttpNotFoundError,
    isMatrixComplete,
    isMatrixItemResolved,
    isQualityGateTaskError,
    isUsableParseStatus,
    isWorkflowStepKey,
    itemTypeLabels,
    keyInfoDraft,
    keyInfoModalOpen,
    knownConfirmedMatrixCount,
    knownHighRiskCount,
    knownMatrixCount,
    knownPendingMatrixCount,
    knownUnresolvedHighRiskCount,
    LARGE_TABLE_PAGINATION,
    Layout,
    LinkOutlined,
    listApprovalTasks,
    listAuditLogs,
    listBusinessDraftBlocks,
    listBusinessDraftChapters,
    listBusinessDraftContextPacks,
    listComplianceEvidenceBindings,
    listComplianceEvidenceCandidates,
    listComplianceItems,
    listDocumentChunks,
    listDocuments,
    listDocumentSemanticSections,
    listEnterpriseMaterials,
    listExportFiles,
    listProjects,
    listQualificationEvaluations,
    listSections,
    listSimilarCandidates,
    listTasks,
    loadImportProcessingState,
    loadingBusinessDraft,
    loadingContextPack,
    loadingEnterprise,
    loadingEvidenceCandidates,
    loadingEvidenceQuality,
    loadingMaterialIndexHealth,
    loadingMaterialSearch,
    loadingMatrix,
    loadingModelConfig,
    loadingProjects,
    loadingSectionQuality,
    loadingQualityChunks,
    loadingReviewChunks,
    loadingRevisionChunks,
    loadingSimilarCandidates,
    loadingWorkspace,
    locateDraftBlockForRow,
    locateMatrixRow,
    locateReviewTimerRef,
    locatingReviewItemId,
    makeMaterialFileUploadRequest,
    mandatoryFilter,
    mandatoryReviewIndex,
    mandatoryReviewOpen,
    mapMatrixRow,
    markDraftBlockViewed,
    matchesDraftBlockFilter,
    materialExtractionMeta,
    materialIndexHealth,
    materialModalOpen,
    materialSearchQuery,
    materialSearchResults,
    materialTypeLabels,
    matrixForkJoinCompleted,
    matrixForkJoinPending,
    matrixForkJoinPendingSections,
    matrixForkJoinTotal,
    matrixForkJoinWorkers,
    matrixReviewFilter,
    matrixReviewRows,
    matrixRows,
    matrixRowsById,
    matrixTaskActive,
    matrixTaskOutput,
    matrixTaskStageTitle,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    missingKeyInfo,
    missingQualificationEvaluations,
    Modal,
    modelConfigDraft,
    modelConfigPayload,
    modelConfigTestResult,
    MVP13_DRAFT_WORKFLOW_AVAILABLE,
    mvp13DraftWorkflowAvailable,
    mvp13PreflightCodes,
    newMaterialDraft,
    newProjectDraft,
    newProjectOpen,
    notification,
    notSatisfiedQualificationEvaluations,
    openContextPackDraftGenerationConfirm,
    openCreateProjectModal,
    openEditDraft,
    openEditDraftBlock,
    openEvidenceBindingDrawer,
    openingEvidenceItemId,
    openKeyInfoModal,
    openMandatoryReview,
    openProjectWorkspace,
    openQualificationEvidenceWork,
    openSimilarCandidates,
    openSourceCreateDraft,
    openWorkspace,
    OutlineEditorModal,
    outlineEditorOpen,
    outlineSectionsFromPreview,
    outlineSeed,
    outputRecord,
    ownerFilter,
    ownerOptions,
    pagedMatrixReviewRows,
    Pagination,
    paragraphCss,
    parseTaskActive,
    plainTerm,
    PlusOutlined,
    Popover,
    preflightActionText,
    preflightCheck,
    preflightChecksForDisplay,
    preflightColor,
    preflightExpanded,
    preflightLabel,
    preflightStatusForDisplay,
    preflightWorkflowTargets,
    previewBusinessDraftContextPack,
    primaryBlockingPreflightCheck,
    primaryBlockingPreflightTarget,
    prioritySortEnabled,
    profileDraft,
    Progress,
    projectCreateMode,
    projectDeleteTargets,
    projectDetail,
    projectGroupCounts,
    projectGroupLabels,
    projectGroupOrder,
    projectTodoActions,
    projectTodoStatusForDisplay,
    projectImportDraft,
    projectImportError,
    projectNavCollapsed,
    projects,
    projectStatusLabels,
    projectTreeData,
    publicUrl,
    publicUrlSite,
    publishDocumentManualRevision,
    publishingRevision,
    qualificationDecision,
    qualificationDecisionConfirmed,
    qualificationDecisionIsNoGo,
    qualificationDecisionNeedsConfirmation,
    qualificationEvaluations,
    qualificationNeedsMaterialByItemId,
    qualificationStatusLabels,
    qualificationTypeLabels,
    qualityChunks,
    qualityDisplayChunks,
    qualityGateTaskErrorCodes,
    qualityIssueActionText,
    qualityIssueSearchTerms,
    qualityIssueSeverityColor,
    qualityIssueSourceChunk,
    qualityIssueSourceExcerpt,
    quickPrompts,
    rawMatrixTaskActive,
    rawParseTaskActive,
    rebuildEnterpriseMaterialIndex,
    rebuildingMaterialIndex,
    recommendedPreflightCheck,
    recommendedStep,
    rejectingCandidateId,
    refreshAfterMatrixMutation,
    refreshMatrixRelatedPanels,
    reloadApprovalTasks,
    reloadAuditLogs,
    reloadBusinessDraftChapters,
    reloadBusinessDraftContext,
    reloadChatModelConfig,
    reloadDocumentsAndExports,
    reloadEnterprise,
    reloadEvidenceBindings,
    reloadEvidenceCandidates,
    reloadEvidenceQualityReports,
    reloadExtractionQuality,
    reloadMaterialIndexHealth,
    reloadMatrix,
    reloadMatrixReview,
    reloadPreflightCheck,
    reloadSectionQualitySummary,
    reloadProjects,
    reloadQualificationDecision,
    reloadQualificationEvaluations,
    reloadWorkspaceSummary,
    renderDiffSegments,
    renderHighlightedText,
    renderReviewParagraph,
    replanDocumentSemanticSections,
    requestPublicUrlAcquisition,
    resetNewMaterialDraft,
    resetNewProjectDraft,
    reviewBlockCss,
    reviewChunkById,
    reviewChunks,
    reviewDisplayChunks,
    reviewDocument,
    reviewDuplicateGroups,
    reviewFallbackChunks,
    reviewHighlightByChunkId,
    reviewHighlights,
    reviewItemPaneRef,
    reviewOpenXmlDocument,
    reviewProgress,
    reviewQueuePage,
    reviewQueuePageSize,
    reviewSourcePaneRef,
    reviewUncoveredChunks,
    revisionChunks,
    revisionDocument,
    revisionDrawerOpen,
    revisionReason,
    revisionSearch,
    riskColor,
    riskFilter,
    riskLabels,
    RobotOutlined,
    runBusinessDraftContextPackCoverageReview,
    runBusinessDraftFactChecks,
    runCss,
    runMaterialSearch,
    runQualificationEvaluation,
    runWorkflowPrimaryAction,
    SafetyCertificateOutlined,
    saveChatModelConfig,
    saveImportProcessingState,
    savingBusinessDraft,
    savingEnterprise,
    savingMatrixAction,
    savingModelConfig,
    savingProject,
    savingSourceItem,
    scrollElementIntoContainer,
    searchEnterpriseMaterials,
    SearchOutlined,
    sectionExtractingId,
    sectionPlanLoading,
    sectionQualityStatusColor,
    sectionQualityStatusLabel,
    sectionQualitySummary,
    sections,
    Segmented,
    Select,
    selectedChapterBlocks,
    selectedDraftChapter,
    selectedDraftChapterId,
    selectedDraftDiff,
    selectedProjectId,
    selectedProjectRowKeys,
    selectedRowKeys,
    selectedSectionId,
    selectedTreeKey,
    semanticSections,
    SendOutlined,
    setActionLogs,
    setActiveDraftBlockId,
    setActiveReviewItemId,
    setActiveTab,
    setApiError,
    setApprovalBusyId,
    setApprovalTasks,
    setAssistantCollapsed,
    setAuditLogs,
    setBindingMaterialId,
    setBusinessDraftChapters,
    setBusinessDraftContextPacks,
    setBusinessDraftGenerationTask,
    setBusinessDraftGenerationTaskId,
    setCandidateIncludeRestricted,
    setCandidateIncludeUnconfirmed,
    setChatModelConfig,
    setComplianceItems,
    setConfirmingMaterialId,
    setContextPackPreview,
    setContextPackPreviewOpen,
    setCoverageReview,
    setDeletingProjects,
    setDirectiveEditorOpen,
    setDocumentBusy,
    setDocuments,
    setDraftBlockFilter,
    setDraftBlocks,
    setDraftEditorValue,
    setEditDraft,
    setEditedDirectives,
    setEditedOutline,
    setEnterpriseMaterials,
    setEnterpriseProfile,
    setEvaluatingQualification,
    setEvidenceBindings,
    setEvidenceCandidates,
    setEvidenceDrawer,
    setExpandedDraftBlockIds,
    setExportFiles,
    setExportingExcel,
    setExportingTenderFormatMode,
    setExportingWord,
    setExtractingHistoryMaterial,
    setExtractionQualityReport,
    setGeneratingDecision,
    setHighlightedRowKey,
    setHistoryExtractResult,
    setHistoryExtractTask,
    setHistoryExtractTaskId,
    setHomeProjectGroup,
    setHomeProjectPage,
    setHomeProjectPageSize,
    setHomeProjectSearch,
    setImportingProjectDraft,
    setImportProcessing,
    setImportUrl,
    setImportUrlSite,
    setKeyInfoDraft,
    setKeyInfoModalOpen,
    setLoadingBusinessDraft,
    setLoadingContextPack,
    setLoadingEnterprise,
    setLoadingEvidenceCandidates,
    setLoadingMaterialIndexHealth,
    setLoadingMaterialSearch,
    setLoadingMatrix,
    setLoadingModelConfig,
    setLoadingProjects,
    setLoadingQualityChunks,
    setLoadingReviewChunks,
    setLoadingRevisionChunks,
    setLoadingSimilarCandidates,
    setLoadingWorkspace,
    setLocatingReviewItemId,
    setMandatoryFilter,
    setMandatoryReviewIndex,
    setMandatoryReviewOpen,
    setMaterialIndexHealth,
    setMaterialModalOpen,
    setMaterialSearchQuery,
    setMaterialSearchResults,
    setMatrixReviewFilter,
    setModelConfigDraft,
    setModelConfigTestResult,
    setNewMaterialDraft,
    setNewProjectDraft,
    setNewProjectOpen,
    setOpeningEvidenceItemId,
    setOutlineEditorOpen,
    setOutlineSeed,
    setOwnerFilter,
    setPreflightCheck,
    setPreflightExpanded,
    setTodoExpanded,
    setPrioritySortEnabled,
    setProfileDraft,
    setProjectCreateMode,
    setProjectDeleteTargets,
    setProjectDetail,
    setProjectImportDraft,
    setProjectImportError,
    setProjectNavCollapsed,
    setProjects,
    setPublicUrl,
    setPublicUrlSite,
    setPublishingRevision,
    setQualificationDecision,
    setQualificationEvaluations,
    setQualityChunks,
    setRebuildingMaterialIndex,
    setReviewChunks,
    setReviewDuplicateGroups,
    setReviewHighlights,
    setReviewOpenXmlDocument,
    setReviewQueuePage,
    setReviewQueuePageSize,
    setReviewUncoveredChunks,
    setRevisionChunks,
    setRevisionDocument,
    setRevisionDrawerOpen,
    setRevisionReason,
    setRevisionSearch,
    setRiskFilter,
    setSavingBusinessDraft,
    setSavingEnterprise,
    setSavingMatrixAction,
    setSavingModelConfig,
    setSavingProject,
    setSavingSourceItem,
    setSectionExtractingId,
    setSectionPlanLoading,
    setSections,
    setSelectedDraftChapterId,
    setSelectedProjectId,
    setSelectedProjectRowKeys,
    setSelectedRowKeys,
    setSelectedSectionId,
    setSelectedTreeKey,
    setSemanticSections,
    setSimilarActions,
    setSimilarBaseRow,
    setSimilarCandidates,
    setSimilarDrawerOpen,
    setSourceCreateMode,
    setSourceDrawer,
    setSourceSelectionDraft,
    setStatusFilter,
    setTestingModelConfig,
    SettingOutlined,
    setUnbindingId,
    setViewedDraftBlockIds,
    setViewMode,
    setWaivingEvidenceItemId,
    setWorkspaceNode,
    similarActions,
    similarBaseRow,
    similarCandidates,
    similarDrawerOpen,
    simpleWorkflowSteps,
    sourceCreateMode,
    sourceDrawer,
    sourceMetaText,
    sourceSelectionDraft,
    Space,
    Spin,
    splitDuplicateGroupItem,
    Statistic,
    statusColor,
    statusFilter,
    statusLabels,
    summaryNumber,
    Switch,
    Table,
    Tabs,
    Tag,
    taskOutputText,
    taskProgressMessage,
    taskShortId,
    taskTimeRange,
    TeamOutlined,
    technicalRows,
    terminalTaskRefreshKeysRef,
    testChatModelConfig,
    testingModelConfig,
    Text,
    TextArea,
    Title,
    toggleDraftBlockExpanded,
    todoExpanded,
    Tooltip,
    Tree,
    truncateText,
    Typography,
    unapprovedDraftBlockCount,
    unbindComplianceEvidence,
    unbindingId,
    uncoveredChunkMap,
    unlinkDuplicateGroupItem,
    unresolvedHighRiskRows,
    unresolvedMatrixRows,
    updateBusinessDraftBlock,
    updateBusinessDraftChapter,
    updateBusinessDraftContextPackDirectives,
    updateComplianceItem,
    updateEnterpriseMaterial,
    updateProject,
    updateRevisionChunk,
    updateSection,
    Upload,
    uploadDocument,
    uploadEnterpriseMaterialFile,
    upsertEnterpriseProfile,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    verificationStatusLabels,
    viewedDraftBlockIds,
    viewMode,
    visibleChapterBlocks,
    visiblePreflightChecks,
    visibleProjectTodoActions,
    waiveComplianceEvidenceRequirement,
    waivingEvidenceItemId,
    WarningOutlined,
    workflowStatusColor,
    workflowStepForContextPackCheck,
    workflowStepForPreflightCheck,
    workflowStepKeys,
    workflowSteps
  };
  return app;
}

export type BidAppController = ReturnType<typeof useBidAppController>;
