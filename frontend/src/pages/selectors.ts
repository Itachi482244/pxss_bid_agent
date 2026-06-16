import dayjs, { type Dayjs } from "dayjs";

import type { DraftBlock, EnterpriseMaterial, ProjectSummary } from "../api/bid";

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
