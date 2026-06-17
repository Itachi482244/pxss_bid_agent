import type { EnterpriseMaterialSearchResult } from "../../api/bid";
import { formatEvidenceSnippet, stripGeneratedIdSuffix } from "./evidenceText";

export interface EvidenceCandidateTarget {
  requirement: string;
  chapter?: string | null;
  risk?: string | null;
  mandatory?: boolean;
}

export interface EvidenceCandidateExplanation {
  recommendationReason: string;
  sourceReference: string;
  riskNote: string;
  coverageText: string;
  riskTone: "success" | "warning" | "danger";
  matchedTerms: string[];
}

export interface EvidenceCandidateExplanationOptions {
  verificationStatusLabels?: Record<string, string>;
}

const LOW_RELEVANCE_THRESHOLD = 0.3;

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function compact(text: string | null | undefined): string {
  return String(text ?? "").replace(/\s+/g, " ").trim();
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

function verificationLabel(
  value: string,
  labels: Record<string, string> | undefined
): string {
  return labels?.[value] ?? value;
}

function relevanceScore(item: EnterpriseMaterialSearchResult): number {
  return item.rerank_used && !item.rerank_fallback_used && item.rerank_score != null
    ? item.rerank_score
    : item.confidence_score;
}

function recommendationReason(item: EnterpriseMaterialSearchResult): string {
  const reason = compact(item.recommend_reason);
  if (reason) return reason;
  if (item.matched_terms.length) {
    return `命中条款关键词：${item.matched_terms.slice(0, 4).join("、")}`;
  }
  if (item.rerank_used && item.rerank_score != null) {
    return `语义重排认为该材料与条款相近，重排分 ${percent(item.rerank_score)}。`;
  }
  return `按条款语义召回，匹配度 ${percent(item.confidence_score)}。`;
}

function sourceReference(item: EnterpriseMaterialSearchResult): string {
  const parts = [`资料库：${stripGeneratedIdSuffix(item.name)}`];
  if (item.file_name) parts.push(`文件：${item.file_name}`);
  if (item.certificate_no) parts.push(`证书号：${item.certificate_no}`);
  if (item.project_name) parts.push(`项目：${item.project_name}`);
  const snippet = truncate(compact(formatEvidenceSnippet(item)), 72);
  if (snippet) parts.push(`片段：${snippet}`);
  return parts.join("；");
}

function coverageText(target: EvidenceCandidateTarget): string {
  const requirement = truncate(stripGeneratedIdSuffix(target.requirement), 88);
  const parts = [`采纳后会绑定到当前条款：${requirement}`];
  if (target.chapter) parts.push(`章节：${target.chapter}`);
  if (target.mandatory) parts.push("强制项");
  if (target.risk) parts.push(`风险：${target.risk}`);
  return parts.join("；");
}

function riskNote(
  item: EnterpriseMaterialSearchResult,
  options: EvidenceCandidateExplanationOptions
): Pick<EvidenceCandidateExplanation, "riskNote" | "riskTone"> {
  const statusLabel = verificationLabel(item.verification_status, options.verificationStatusLabels);
  if (!item.data_level_allowed || item.data_level === "restricted" || item.data_level === "confidential") {
    return {
      riskNote: "资料为受限/机密或当前数据等级不允许，需先脱敏或调整权限，不能直接进入投标响应。",
      riskTone: "danger"
    };
  }
  if (item.verification_status === "conflict" || item.verification_status === "expired") {
    return {
      riskNote: `资料状态为${statusLabel}，不能直接绑定为响应证据。`,
      riskTone: "danger"
    };
  }
  if (item.verification_status !== "confirmed") {
    return {
      riskNote: `资料状态为${statusLabel}，采纳前需先完成人工确认。`,
      riskTone: "warning"
    };
  }
  if (relevanceScore(item) < LOW_RELEVANCE_THRESHOLD) {
    return {
      riskNote: `语义相关度较低（${percent(relevanceScore(item))}），绑定前请人工核对是否切合本条款。`,
      riskTone: "warning"
    };
  }
  if (item.rerank_fallback_used || item.rerank_error) {
    return {
      riskNote: item.rerank_error
        ? `重排能力降级：${item.rerank_error}。请人工复核候选排序。`
        : "重排能力降级，当前按召回顺序展示候选，请人工复核排序。",
      riskTone: "warning"
    };
  }
  if (item.material_status_hint) {
    return {
      riskNote: item.material_status_hint,
      riskTone: "warning"
    };
  }
  return {
    riskNote: "资料已确认且数据等级允许；采纳前仍需人工核对片段是否能直接支撑条款。",
    riskTone: "success"
  };
}

export function buildEvidenceCandidateExplanation(
  item: EnterpriseMaterialSearchResult,
  target: EvidenceCandidateTarget,
  options: EvidenceCandidateExplanationOptions = {}
): EvidenceCandidateExplanation {
  const risk = riskNote(item, options);
  return {
    recommendationReason: recommendationReason(item),
    sourceReference: sourceReference(item),
    riskNote: risk.riskNote,
    coverageText: coverageText(target),
    riskTone: risk.riskTone,
    matchedTerms: item.matched_terms
  };
}
