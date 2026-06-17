import { describe, expect, it } from "vitest";

import type { EnterpriseMaterialSearchResult } from "../../api/bid";
import { buildEvidenceCandidateExplanation } from "./evidenceCandidateExplanation";

function makeCandidate(partial: Partial<EnterpriseMaterialSearchResult>): EnterpriseMaterialSearchResult {
  return {
    id: "m1",
    tenant_id: "t1",
    material_type: "qualification",
    name: "安全生产许可证",
    issuing_authority: null,
    certificate_no: "AQ-2026-001",
    holder_name: null,
    project_name: null,
    amount: null,
    valid_from: null,
    valid_until: null,
    data_level: "internal",
    verification_status: "confirmed",
    structured_fields: null,
    evidence_text: "许可范围包含建筑施工。",
    file_name: "安全生产许可证.pdf",
    content_type: "application/pdf",
    file_size: 1024,
    sha256: null,
    created_by: "u1",
    updated_by: "u1",
    created_at: "2026-06-17T00:00:00Z",
    updated_at: "2026-06-17T00:00:00Z",
    snippet: "许可范围包含建筑施工。",
    confidence_score: 0.82,
    base_score: 0.67,
    rerank_score: 0.91,
    rerank_provider: "infinity_rerank",
    rerank_model: "BAAI/bge-reranker-base",
    rerank_used: true,
    rerank_fallback_used: false,
    rerank_error: null,
    chunk_id: "c1",
    data_level_allowed: true,
    recommend_reason: "证书名称与条款中的安全生产许可证一致。",
    matched_terms: ["安全生产许可证"],
    material_status_hint: null,
    ...partial
  };
}

const target = {
  requirement: "投标人须提供有效的安全生产许可证。",
  chapter: "资格审查资料",
  risk: "高风险",
  mandatory: true
};

describe("buildEvidenceCandidateExplanation", () => {
  it("为已确认候选生成推荐理由、来源、风险和覆盖条款四要素", () => {
    const explanation = buildEvidenceCandidateExplanation(makeCandidate({}), target, {
      verificationStatusLabels: { confirmed: "已确认" }
    });

    expect(explanation.recommendationReason).toBe("证书名称与条款中的安全生产许可证一致。");
    expect(explanation.sourceReference).toContain("资料库：安全生产许可证");
    expect(explanation.sourceReference).toContain("文件：安全生产许可证.pdf");
    expect(explanation.sourceReference).toContain("证书号：AQ-2026-001");
    expect(explanation.riskNote).toContain("资料已确认");
    expect(explanation.riskTone).toBe("success");
    expect(explanation.coverageText).toContain("投标人须提供有效的安全生产许可证");
    expect(explanation.coverageText).toContain("强制项");
  });

  it("无推荐原因时使用命中词和分数兜底", () => {
    const explanation = buildEvidenceCandidateExplanation(
      makeCandidate({
        recommend_reason: null,
        matched_terms: ["业绩", "合同"],
        evidence_text: null,
        snippet: "近三年同类项目合同扫描件\n{\"project\":\"A\"}",
        name: "同类业绩合同 7D3087E3"
      }),
      { requirement: "提供近三年同类业绩合同。" }
    );

    expect(explanation.recommendationReason).toBe("命中条款关键词：业绩、合同");
    expect(explanation.sourceReference).toContain("资料库：同类业绩合同");
    expect(explanation.sourceReference).toContain("片段：近三年同类项目合同扫描件");
    expect(explanation.coverageText).toContain("提供近三年同类业绩合同");
  });

  it("受限资料标为高风险解释", () => {
    const explanation = buildEvidenceCandidateExplanation(
      makeCandidate({
        data_level: "restricted",
        data_level_allowed: false
      }),
      target
    );

    expect(explanation.riskTone).toBe("danger");
    expect(explanation.riskNote).toContain("受限/机密");
    expect(explanation.riskNote).toContain("不能直接进入投标响应");
  });

  it("低相关候选提示人工核对", () => {
    const explanation = buildEvidenceCandidateExplanation(
      makeCandidate({
        confidence_score: 0.22,
        rerank_score: null,
        rerank_used: false
      }),
      target
    );

    expect(explanation.riskTone).toBe("warning");
    expect(explanation.riskNote).toContain("语义相关度较低");
  });
});
