import type { EnterpriseMaterialSearchResult } from "../../api/bid";

// 末尾粘连的生成式 id（如 "。7D3087E3" 的 8 位大小写十六进制、
// 或 "API 测试响应项 238e5fff...caef" 的长 uuid）。要求至少含一个十六进制字母，
// 避免误删合法的纯数字（金额、数量等）。
const GENERATED_ID_SUFFIX = /[\s_-]*\b(?=[0-9A-Fa-f]*[A-Fa-f])[0-9A-Fa-f]{8,}\b\s*$/;

// snippet 实为送入向量库的原始切片，末尾常拼接结构化字段 JSON，不宜直接展示。
const TRAILING_JSON_BLOB = /\n?\s*\{[\s\S]*\}\s*$/;

/**
 * 去掉条款/资料名末尾的生成式 id 尾巴（仅裁剪展示，不改后端数据）。
 * 仅命中末尾、含十六进制字母、长度 ≥8 的 token；裁空则回退原文。
 */
export function stripGeneratedIdSuffix(text: string | null | undefined): string {
  if (!text) return text ?? "";
  const cleaned = text.replace(GENERATED_ID_SUFFIX, "").trim();
  return cleaned || text;
}

/**
 * 证据摘录的展示文本。优先用干净的 evidence_text；
 * 缺失时回退到 snippet 并剥离末尾结构化 JSON；再不行用资料名。
 */
export function formatEvidenceSnippet(
  record: Pick<EnterpriseMaterialSearchResult, "evidence_text" | "snippet" | "name">
): string {
  const clean = record.evidence_text?.trim();
  if (clean) return clean;
  const snippet = record.snippet?.trim();
  if (snippet) {
    const stripped = snippet.replace(TRAILING_JSON_BLOB, "").trim();
    return stripped || stripGeneratedIdSuffix(record.name);
  }
  return stripGeneratedIdSuffix(record.name);
}
