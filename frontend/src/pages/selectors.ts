import dayjs, { type Dayjs } from "dayjs";

import type {
  DraftBlock,
  EnterpriseMaterial,
  PreflightCheckItem,
  ProjectSummary,
  SectionQualityCheck,
  SectionQualitySummary
} from "../api/bid";

// 首页项目分组（互斥取一）。
export type ProjectGroup = "needs_me" | "in_progress" | "done";

// 草稿块过滤维度。
export type DraftBlockFilter = "all" | "needs_confirm" | "needs_evidence" | "pending";

export type SectionQualityStatus = "pass" | "warn" | "block";

export function sectionQualityStatusLabel(status: string): string {
  if (status === "block") return "阻断";
  if (status === "warn") return "需复核";
  return "可继续";
}

export function sectionQualityStatusColor(status: string): string {
  if (status === "block") return "red";
  if (status === "warn") return "gold";
  return "green";
}

export type ProjectTodoSource = "quality" | "preflight";

export interface ProjectTodoAction {
  key: string;
  source: ProjectTodoSource;
  sourceLabel: string;
  code: string;
  title: string;
  status: SectionQualityStatus;
  count: number;
  message: string;
  actionLabel: string;
  target: string | null;
  priority: number;
}

const todoStatusRank: Record<SectionQualityStatus, number> = {
  block: 0,
  warn: 1,
  pass: 2
};

function normalizeTodoStatus(status: string): SectionQualityStatus {
  if (status === "block" || status === "warn") return status;
  return "pass";
}

const preflightTodoPriorityByCode: Record<string, number> = {
  high_risk: 0,
  matrix_version: 10,
  technical: 30,
  mandatory_evidence: 40,
  draft_block_review: 50,
  draft_exists: 50,
  draft_facts: 50,
  qualification: 60,
  qualification_decision: 60,
  deadline: 70,
  approvals: 80
};

const qualityTodoPriorityByCategory: Record<string, number> = {
  source: 10,
  pricing: 20,
  export: 20,
  coverage: 30,
  draft: 50,
  context_pack: 60
};

function fallbackTodoPriority(code: string, target: string | null, title: string) {
  const haystack = `${code}:${target ?? ""}:${title}`;
  if (/disqualifying|high_risk|废标|高风险/.test(haystack)) return 0;
  if (/source\.no_tender_text|directory\.unavailable|matrix_version/.test(haystack)) return 10;
  if (/submission|export|pricing\.blocking|正式|导出|报价/.test(haystack)) return 20;
  if (/coverage\.gaps|technical|scoring|评分|技术响应/.test(haystack)) return 30;
  if (/mandatory_evidence|needs_evidence|evidence|缺证据|材料/.test(haystack)) return 40;
  if (/draft_facts|draft_block|draft_coverage|facts|草稿|事实/.test(haystack)) return 50;
  if (/context_pack|qualification_decision|qualification|资格|参标/.test(haystack)) return 60;
  if (/deadline|日期|截止/.test(haystack)) return 70;
  if (/approval|审批/.test(haystack)) return 80;
  return 90;
}

function qualityTodoPriority(check: SectionQualityCheck) {
  if (/disqualifying|high_risk/.test(check.code)) return 0;
  if (check.code === "directory.unavailable") return 10;
  return (
    qualityTodoPriorityByCategory[check.category] ??
    fallbackTodoPriority(check.code, check.target, check.title)
  );
}

function preflightTodoPriority(item: PreflightCheckItem) {
  return preflightTodoPriorityByCode[item.code] ?? fallbackTodoPriority(item.code, item.target, item.title);
}

function qualityTodoAction(check: SectionQualityCheck): ProjectTodoAction {
  const status = normalizeTodoStatus(check.status);
  return {
    key: `quality:${check.code}`,
    source: "quality",
    sourceLabel: "质量体检",
    code: check.code,
    title: check.title,
    status,
    count: check.count,
    message: check.message,
    actionLabel: check.action_label || "查看处理项",
    target: check.target,
    priority: qualityTodoPriority(check)
  };
}

function preflightTodoAction(item: PreflightCheckItem): ProjectTodoAction {
  const status = normalizeTodoStatus(item.status);
  return {
    key: `preflight:${item.code}`,
    source: "preflight",
    sourceLabel: "提交前核验",
    code: item.code,
    title: item.title,
    status,
    count: item.count,
    message: item.message,
    actionLabel: item.action_label || "查看处理项",
    target: item.target,
    priority: preflightTodoPriority(item)
  };
}

export function buildProjectTodoActions(
  qualitySummary: SectionQualitySummary | null | undefined,
  preflightChecks: PreflightCheckItem[]
): ProjectTodoAction[] {
  const actions = [
    ...(qualitySummary?.checks ?? []).filter((check) => check.status !== "pass").map(qualityTodoAction),
    ...preflightChecks.filter((item) => item.status !== "pass").map(preflightTodoAction)
  ];

  return actions.sort((left, right) => {
    const statusDiff = todoStatusRank[left.status] - todoStatusRank[right.status];
    if (statusDiff !== 0) return statusDiff;
    if (left.priority !== right.priority) return left.priority - right.priority;
    if (right.count !== left.count) return right.count - left.count;
    return left.key.localeCompare(right.key);
  });
}

// 项目分组：终态归"已完成"，需要人工动作归"待我处理"，其余归"进行中"。
export function classifyProjectGroup(project: ProjectSummary): ProjectGroup {
  if (project.status === "exported" || project.status === "archived") return "done";
  if (
    project.status === "pending_confirm" ||
    project.status === "need_materials" ||
    project.pending_confirm_count > 0
  ) {
    return "needs_me";
  }
  return "in_progress";
}

// "待覆盖"=尚未人工通过且非"待确认/待补证"的块。
export function matchesDraftBlockFilter(block: DraftBlock, filter: DraftBlockFilter): boolean {
  if (filter === "all") return true;
  if (filter === "needs_confirm") return block.review_status === "needs_confirm";
  if (filter === "needs_evidence") return block.review_status === "needs_evidence";
  return (
    block.review_status !== "approved" &&
    block.review_status !== "needs_confirm" &&
    block.review_status !== "needs_evidence"
  );
}

// 首页分组 + 关键词过滤（关键词匹配名称/采购人/代理机构，大小写不敏感）。
export function filterHomeProjects(
  projects: ProjectSummary[],
  group: ProjectGroup,
  search: string
): ProjectSummary[] {
  const keyword = search.trim().toLowerCase();
  return projects.filter((project) => {
    if (classifyProjectGroup(project) !== group) return false;
    if (!keyword) return true;
    const haystack = [project.name, project.purchaser, project.agency]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(keyword);
  });
}

export type DraftBlockFilterCounts = Record<DraftBlockFilter, number>;

// 各过滤项计数（用于过滤条角标）。
export function computeDraftBlockFilterCounts(blocks: DraftBlock[]): DraftBlockFilterCounts {
  const counts: DraftBlockFilterCounts = { all: 0, needs_confirm: 0, needs_evidence: 0, pending: 0 };
  for (const block of blocks) {
    counts.all += 1;
    if (matchesDraftBlockFilter(block, "needs_confirm")) counts.needs_confirm += 1;
    if (matchesDraftBlockFilter(block, "needs_evidence")) counts.needs_evidence += 1;
    if (matchesDraftBlockFilter(block, "pending")) counts.pending += 1;
  }
  return counts;
}

export interface DashboardStats {
  total: number;
  activeCount: number;
  groupCounts: Record<ProjectGroup, number>;
  statusDistribution: [string, number][];
  pendingConfirmTotal: number;
  highRiskTotal: number;
  dueSoonCount: number;
  budgetTotal: number;
}

export interface MaterialExtractionMeta {
  isHistoryExtracted: boolean;
  sourceFileName: string | null;
  sourceFileCount: number;
  sourceFileSummary: string | null;
  sourceLocationText: string | null;
  sourceImageCount: number;
  confidence: number | null;
  needsHumanConfirm: boolean;
  extractionMethod: string | null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asNumber(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

export function materialExtractionMeta(material: EnterpriseMaterial): MaterialExtractionMeta {
  const fields = asRecord(material.structured_fields);
  const source = String(fields.source ?? "");
  const locations = Array.isArray(fields.source_locations) ? fields.source_locations : [];
  const sourceImages = Array.isArray(fields.source_images) ? fields.source_images : [];
  const sourceFiles = Array.isArray(fields.source_files) ? fields.source_files.map(asRecord) : [];
  const sourceFileNames = sourceFiles
    .map((item) => asString(item.source_file_name) ?? asString(item.file_name))
    .filter((item): item is string => Boolean(item));
  const fallbackSourceFileName = asString(fields.source_file_name) ?? material.file_name;
  const sourceFileName = fallbackSourceFileName ?? sourceFileNames[0] ?? null;
  const sourceFileCount = sourceFileNames.length || (sourceFileName ? 1 : 0);
  const firstLocation = asRecord(locations[0]);
  const pageNo = firstLocation.page_no;
  const blockIndex = firstLocation.block_index;
  const locationParts = [
    typeof pageNo === "number" || typeof pageNo === "string" ? `P${pageNo}` : null,
    typeof blockIndex === "number" || typeof blockIndex === "string" ? `块 ${blockIndex}` : null
  ].filter(Boolean);
  return {
    isHistoryExtracted: source === "history_file_extract",
    sourceFileName,
    sourceFileCount,
    sourceFileSummary: sourceFileCount > 1 ? `${sourceFileCount} 个历史文件` : sourceFileName,
    sourceLocationText: locationParts.length ? locationParts.join(" · ") : null,
    sourceImageCount: sourceImages.length,
    confidence: asNumber(fields.extraction_confidence),
    needsHumanConfirm: Boolean(fields.needs_human_confirm) || material.verification_status === "pending_confirm",
    extractionMethod: typeof fields.extraction_method === "string" ? fields.extraction_method : null
  };
}

// 管理层宏观看板：纯前端聚合现有项目数据（不依赖后端聚合）。
// referenceDate 注入"现在"，便于确定性测试截止日临近逻辑。
export function computeDashboardStats(
  projects: ProjectSummary[],
  referenceDate: Dayjs = dayjs()
): DashboardStats {
  const statusDistribution = new Map<string, number>();
  let pendingConfirmTotal = 0;
  let highRiskTotal = 0;
  let dueSoonCount = 0;
  let budgetTotal = 0;
  const groupCounts: Record<ProjectGroup, number> = { needs_me: 0, in_progress: 0, done: 0 };
  for (const project of projects) {
    statusDistribution.set(project.status, (statusDistribution.get(project.status) ?? 0) + 1);
    groupCounts[classifyProjectGroup(project)] += 1;
    pendingConfirmTotal += project.pending_confirm_count ?? 0;
    highRiskTotal += project.high_risk_count ?? 0;
    if (
      project.bid_deadline_at &&
      classifyProjectGroup(project) !== "done" &&
      dayjs(project.bid_deadline_at).diff(referenceDate, "day") <= 14 &&
      dayjs(project.bid_deadline_at).diff(referenceDate, "day") >= 0
    ) {
      dueSoonCount += 1;
    }
    const budget = Number(project.budget_amount ?? 0);
    if (Number.isFinite(budget)) budgetTotal += budget;
  }
  const activeCount = groupCounts.needs_me + groupCounts.in_progress;
  return {
    total: projects.length,
    activeCount,
    groupCounts,
    statusDistribution: Array.from(statusDistribution.entries()).sort((a, b) => b[1] - a[1]),
    pendingConfirmTotal,
    highRiskTotal,
    dueSoonCount,
    budgetTotal
  };
}
