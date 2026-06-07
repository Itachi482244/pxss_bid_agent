import dayjs from "dayjs";
import { describe, expect, it } from "vitest";

import type { DraftBlock, ProjectSummary } from "../api/bid";
import {
  classifyProjectGroup,
  computeDashboardStats,
  computeDraftBlockFilterCounts,
  filterHomeProjects,
  matchesDraftBlockFilter
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
