import dayjs from "dayjs";
import { describe, expect, it } from "vitest";

import type {
  DraftBlock,
  EnterpriseMaterial,
  PreflightCheckItem,
  ProjectSummary,
  SectionQualityCheck,
  SectionQualitySummary
} from "../api/bid";
import {
  buildProjectTodoActions,
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

function makeQualityCheck(partial: Partial<SectionQualityCheck>): SectionQualityCheck {
  return {
    code: "coverage.gaps",
    title: "覆盖缺口",
    status: "warn",
    message: "仍有覆盖缺口",
    category: "coverage",
    count: 1,
    action_label: "查看缺口",
    target: "chapter",
    details: [],
    ...partial
  };
}

function makeQualitySummary(checks: SectionQualityCheck[]): SectionQualitySummary {
  return {
    project_id: "p1",
    section_id: "s1",
    status: checks.some((check) => check.status === "block")
      ? "block"
      : checks.some((check) => check.status === "warn")
        ? "warn"
        : "pass",
    status_label: "需处理",
    summary: "质量体检摘要",
    generated_at: "2026-06-16T00:00:00Z",
    checks,
    suggested_actions: [],
    coverage_summary: {},
    pricing_summary: {},
    material_summary: {},
    export_preview: {
      review_allowed: true,
      submission_allowed: false,
      export_modes: ["review", "submission"],
      chapter_count: 0,
      scoring_index_count: 0,
      technical_response_count: 0,
      placeholder_count: 0
    },
    context_pack_status: null,
    draft_summary: {},
    source: {}
  };
}

function makePreflightCheckItem(partial: Partial<PreflightCheckItem>): PreflightCheckItem {
  return {
    code: "high_risk",
    title: "高风险",
    status: "block",
    count: 1,
    message: "还有高风险项未确认",
    action_label: "打开审阅台",
    target: "review",
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

describe("buildProjectTodoActions", () => {
  it("合并质量体检和提交前核验，并排除已通过项", () => {
    const actions = buildProjectTodoActions(
      makeQualitySummary([
        makeQualityCheck({
          code: "coverage.disqualifying_gaps",
          title: "L1 合规格式",
          status: "block",
          count: 2,
          message: "2 项核心资格/废标项尚未满足",
          action_label: "补齐资格材料",
          target: "evidence"
        }),
        makeQualityCheck({ code: "pricing.ready", title: "报价校验", status: "pass" })
      ]),
      [
        makePreflightCheckItem({ code: "mandatory_evidence", title: "强制证据", status: "warn", count: 3 }),
        makePreflightCheckItem({ code: "draft_exists", title: "商务草稿", status: "pass" })
      ]
    );

    expect(actions.map((item) => item.key)).toEqual([
      "quality:coverage.disqualifying_gaps",
      "preflight:mandatory_evidence"
    ]);
    expect(actions[0]).toMatchObject({
      source: "quality",
      sourceLabel: "质量体检",
      actionLabel: "补齐资格材料",
      target: "evidence"
    });
  });

  it("阻断项优先于复核项，废标/高风险优先于报价和导出问题", () => {
    const actions = buildProjectTodoActions(
      makeQualitySummary([
        makeQualityCheck({
          code: "pricing.blocking_issues",
          title: "L3 报价校验",
          status: "block",
          count: 5,
          message: "报价存在正式稿阻断问题",
          target: "chapter"
        }),
        makeQualityCheck({
          code: "coverage.disqualifying_gaps",
          title: "废标风险缺口",
          status: "block",
          count: 1,
          message: "核心资格尚未满足",
          target: "evidence"
        }),
        makeQualityCheck({
          code: "export_materials.not_embeddable",
          title: "导出材料嵌入",
          status: "warn",
          count: 8,
          message: "材料暂无可嵌入图片/PDF",
          target: "evidence"
        })
      ]),
      [makePreflightCheckItem({ code: "high_risk", title: "高风险", status: "block", count: 2 })]
    );

    expect(actions.slice(0, 2).map((item) => item.key)).toEqual([
      "preflight:high_risk",
      "quality:coverage.disqualifying_gaps"
    ]);
    expect(actions.slice(2).map((item) => item.key)).toEqual([
      "quality:pricing.blocking_issues",
      "quality:export_materials.not_embeddable"
    ]);
  });

  it("同状态同业务优先级时按数量降序，再按 key 稳定排序", () => {
    const actions = buildProjectTodoActions(
      makeQualitySummary([
        makeQualityCheck({
          code: "draft_blocks.pending",
          title: "草稿审阅",
          status: "warn",
          count: 2,
          message: "草稿块待处理"
        }),
        makeQualityCheck({
          code: "draft_facts.pending",
          title: "草稿事实校验",
          status: "warn",
          count: 4,
          message: "事实待核验"
        })
      ]),
      []
    );

    expect(actions.map((item) => item.key)).toEqual(["quality:draft_facts.pending", "quality:draft_blocks.pending"]);
  });

  it("优先使用结构化 category/code 排序，标题关键词只作未知项兜底", () => {
    const actions = buildProjectTodoActions(
      makeQualitySummary([
        makeQualityCheck({
          code: "custom.general_notice",
          title: "附件标题提到废标/报价/导出但只是普通提醒",
          category: "draft",
          status: "warn",
          count: 1,
          message: "标题关键词不应把 draft 类待办提到最高优先级"
        }),
        makeQualityCheck({
          code: "pricing.pending",
          title: "L3 报价校验",
          category: "pricing",
          status: "warn",
          count: 1,
          message: "报价待补字段"
        })
      ]),
      [
        makePreflightCheckItem({
          code: "unknown_followup",
          title: "标题提到废标但 preflight code 未登记",
          status: "warn",
          count: 1,
          message: "未知 code 仍允许用标题兜底"
        })
      ]
    );

    expect(actions.map((item) => item.key)).toEqual([
      "preflight:unknown_followup",
      "quality:pricing.pending",
      "quality:custom.general_notice"
    ]);
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
