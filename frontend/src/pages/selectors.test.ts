import dayjs from "dayjs";
import { describe, expect, it } from "vitest";

import type { DraftBlock, EnterpriseMaterial, ProjectSummary } from "../api/bid";
import {
  classifyProjectGroup,
  computeDashboardStats,
  computeDraftBlockFilterCounts,
  filterHomeProjects,
  materialExtractionMeta,
  matchesDraftBlockFilter,
  sectionQualityStatusColor,
  sectionQualityStatusLabel
} from "./selectors";

function makeProject(partial: Partial<ProjectSummary>): ProjectSummary {
  return {
    name: "项目",
    purchaser: "",
    agency: "",
    status: "in_progress",
    pending_confirm_count: 0,
    high_risk_count: 0,
    bid_deadline_at: null,
    budget_amount: null,
    ...partial
  } as ProjectSummary;
}

function makeBlock(reviewStatus: string): DraftBlock {
  return { review_status: reviewStatus } as DraftBlock;
}

function makeMaterial(partial: Partial<EnterpriseMaterial>): EnterpriseMaterial {
  return {
    id: "m1",
    tenant_id: "t1",
    material_type: "qualification",
    name: "资质",
    issuing_authority: null,
    certificate_no: null,
    holder_name: null,
    project_name: null,
    amount: null,
    valid_from: null,
    valid_until: null,
    data_level: "internal",
    verification_status: "pending_confirm",
    structured_fields: null,
    evidence_text: null,
    file_name: null,
    content_type: null,
    file_size: null,
    sha256: null,
    created_by: "u1",
    updated_by: "u1",
    created_at: "2026-06-07T00:00:00Z",
    updated_at: "2026-06-07T00:00:00Z",
    ...partial
  };
}

describe("classifyProjectGroup", () => {
  it("归类终态为 done", () => {
    expect(classifyProjectGroup(makeProject({ status: "exported" }))).toBe("done");
    expect(classifyProjectGroup(makeProject({ status: "archived" }))).toBe("done");
  });

  it("待人工动作归 needs_me", () => {
    expect(classifyProjectGroup(makeProject({ status: "pending_confirm" }))).toBe("needs_me");
    expect(classifyProjectGroup(makeProject({ status: "need_materials" }))).toBe("needs_me");
    expect(classifyProjectGroup(makeProject({ status: "in_progress", pending_confirm_count: 2 }))).toBe(
      "needs_me"
    );
  });

  it("其余归 in_progress", () => {
    expect(classifyProjectGroup(makeProject({ status: "in_progress" }))).toBe("in_progress");
  });
});

describe("matchesDraftBlockFilter", () => {
  it("all 命中所有块", () => {
    expect(matchesDraftBlockFilter(makeBlock("approved"), "all")).toBe(true);
  });

  it("精确匹配 needs_confirm / needs_evidence", () => {
    expect(matchesDraftBlockFilter(makeBlock("needs_confirm"), "needs_confirm")).toBe(true);
    expect(matchesDraftBlockFilter(makeBlock("needs_evidence"), "needs_confirm")).toBe(false);
    expect(matchesDraftBlockFilter(makeBlock("needs_evidence"), "needs_evidence")).toBe(true);
  });

  it("pending=未通过且非待确认/待补证", () => {
    expect(matchesDraftBlockFilter(makeBlock("pending_review"), "pending")).toBe(true);
    expect(matchesDraftBlockFilter(makeBlock("approved"), "pending")).toBe(false);
    expect(matchesDraftBlockFilter(makeBlock("needs_confirm"), "pending")).toBe(false);
    expect(matchesDraftBlockFilter(makeBlock("needs_evidence"), "pending")).toBe(false);
  });
});

describe("sectionQualityStatusLabel", () => {
  it("复用 pass/warn/block 三态并输出面向用户文案", () => {
    expect(sectionQualityStatusLabel("pass")).toBe("可继续");
    expect(sectionQualityStatusLabel("warn")).toBe("需复核");
    expect(sectionQualityStatusLabel("block")).toBe("阻断");
    expect(sectionQualityStatusLabel("unknown")).toBe("可继续");
  });

  it("状态颜色与三态严重度一致", () => {
    expect(sectionQualityStatusColor("pass")).toBe("green");
    expect(sectionQualityStatusColor("warn")).toBe("gold");
    expect(sectionQualityStatusColor("block")).toBe("red");
  });
});

describe("filterHomeProjects", () => {
  const projects = [
    makeProject({ name: "净化机房改造", status: "in_progress", purchaser: "甲单位" }),
    makeProject({ name: "燃气管网EPC", status: "pending_confirm", agency: "乙代理" }),
    makeProject({ name: "老旧小区改造", status: "exported" })
  ];

  it("按分组过滤", () => {
    expect(filterHomeProjects(projects, "in_progress", "").map((p) => p.name)).toEqual(["净化机房改造"]);
    expect(filterHomeProjects(projects, "done", "").map((p) => p.name)).toEqual(["老旧小区改造"]);
  });

  it("关键词跨名称/采购人/代理机构、大小写不敏感", () => {
    expect(filterHomeProjects(projects, "needs_me", "乙代理").map((p) => p.name)).toEqual(["燃气管网EPC"]);
    expect(filterHomeProjects(projects, "in_progress", "净化").map((p) => p.name)).toEqual(["净化机房改造"]);
    expect(filterHomeProjects(projects, "in_progress", "epc")).toEqual([]);
  });
});

describe("computeDraftBlockFilterCounts", () => {
  it("各维度独立计数", () => {
    const blocks = [
      makeBlock("needs_confirm"),
      makeBlock("needs_evidence"),
      makeBlock("pending_review"),
      makeBlock("approved")
    ];
    expect(computeDraftBlockFilterCounts(blocks)).toEqual({
      all: 4,
      needs_confirm: 1,
      needs_evidence: 1,
      pending: 1
    });
  });

  it("空集全 0", () => {
    expect(computeDraftBlockFilterCounts([])).toEqual({
      all: 0,
      needs_confirm: 0,
      needs_evidence: 0,
      pending: 0
    });
  });
});

describe("computeDashboardStats", () => {
  const now = dayjs("2026-06-07T00:00:00+08:00");

  it("聚合分组/状态分布/预算合计", () => {
    const projects = [
      makeProject({ status: "in_progress", budget_amount: "100" }),
      makeProject({ status: "pending_confirm", pending_confirm_count: 3, high_risk_count: 1, budget_amount: "50" }),
      makeProject({ status: "exported", budget_amount: "10" })
    ];
    const stats = computeDashboardStats(projects, now);
    expect(stats.total).toBe(3);
    expect(stats.groupCounts).toEqual({ needs_me: 1, in_progress: 1, done: 1 });
    expect(stats.activeCount).toBe(2);
    expect(stats.pendingConfirmTotal).toBe(3);
    expect(stats.highRiskTotal).toBe(1);
    expect(stats.budgetTotal).toBe(160);
    expect(stats.statusDistribution).toEqual(
      expect.arrayContaining([
        ["in_progress", 1],
        ["pending_confirm", 1],
        ["exported", 1]
      ])
    );
  });

  it("dueSoon: 仅统计 0~14 天内、非终态项目", () => {
    const projects = [
      makeProject({ status: "in_progress", bid_deadline_at: now.add(5, "day").toISOString() }),
      makeProject({ status: "in_progress", bid_deadline_at: now.add(20, "day").toISOString() }),
      makeProject({ status: "in_progress", bid_deadline_at: now.subtract(1, "day").toISOString() }),
      makeProject({ status: "exported", bid_deadline_at: now.add(3, "day").toISOString() })
    ];
    expect(computeDashboardStats(projects, now).dueSoonCount).toBe(1);
  });
});

describe("materialExtractionMeta", () => {
  it("提取历史文件来源、位置、置信度和复核标记", () => {
    const meta = materialExtractionMeta(
      makeMaterial({
        structured_fields: {
          source: "history_file_extract",
          source_file_name: "历史投标资料.docx",
          source_locations: [{ page_no: 3, block_index: 7 }],
          source_images: [{ page_no: 3, object_key: "source-pages/page-0003.png" }],
          extraction_confidence: 0.83,
          extraction_method: "local_rules",
          needs_human_confirm: true
        }
      })
    );

    expect(meta).toEqual({
      isHistoryExtracted: true,
      sourceFileName: "历史投标资料.docx",
      sourceFileCount: 1,
      sourceFileSummary: "历史投标资料.docx",
      sourceLocationText: "P3 · 块 7",
      sourceImageCount: 1,
      confidence: 0.83,
      needsHumanConfirm: true,
      extractionMethod: "local_rules"
    });
  });

  it("展示跨文件合并后的来源数量和最近来源", () => {
    const meta = materialExtractionMeta(
      makeMaterial({
        structured_fields: {
          source: "history_file_extract",
          source_file_name: "新版营业执照.docx",
          source_files: [
            { source_file_name: "旧版营业执照.docx" },
            { source_file_name: "新版营业执照.docx" }
          ],
          source_locations: [{ block_index: 1 }]
        }
      })
    );

    expect(meta.sourceFileName).toBe("新版营业执照.docx");
    expect(meta.sourceFileCount).toBe(2);
    expect(meta.sourceFileSummary).toBe("2 个历史文件");
    expect(meta.sourceLocationText).toBe("块 1");
  });

  it("普通手工资料保持温和默认值", () => {
    const meta = materialExtractionMeta(makeMaterial({ verification_status: "confirmed", file_name: "资质.pdf" }));
    expect(meta.isHistoryExtracted).toBe(false);
    expect(meta.sourceFileName).toBe("资质.pdf");
    expect(meta.sourceFileCount).toBe(1);
    expect(meta.sourceFileSummary).toBe("资质.pdf");
    expect(meta.needsHumanConfirm).toBe(false);
  });
});
