import { describe, expect, it } from "vitest";

import { formatEvidenceSnippet, stripGeneratedIdSuffix } from "./evidenceText";

describe("stripGeneratedIdSuffix", () => {
  it("剥离条款末尾粘连的 8 位十六进制 id", () => {
    expect(stripGeneratedIdSuffix("投标人须具备工程设计综合资质。3589D647")).toBe(
      "投标人须具备工程设计综合资质。"
    );
  });

  it("剥离测试响应项末尾的长 uuid", () => {
    expect(stripGeneratedIdSuffix("API 测试响应项 238e5fffa410426b95579fd19f27caef")).toBe(
      "API 测试响应项"
    );
  });

  it("保留合法的纯数字尾巴（金额/数量）", () => {
    expect(stripGeneratedIdSuffix("近三年营业额不低于 12345678")).toBe("近三年营业额不低于 12345678");
  });

  it("不误伤无尾巴的正常条款", () => {
    expect(stripGeneratedIdSuffix("资格要求：投标人须提供有效安全生产许可证。")).toBe(
      "资格要求：投标人须提供有效安全生产许可证。"
    );
  });

  it("裁剪结果为空时回退原文", () => {
    expect(stripGeneratedIdSuffix("7D3087E3")).toBe("7D3087E3");
  });

  it("空值安全", () => {
    expect(stripGeneratedIdSuffix(null)).toBe("");
    expect(stripGeneratedIdSuffix(undefined)).toBe("");
  });
});

describe("formatEvidenceSnippet", () => {
  it("优先使用干净的 evidence_text", () => {
    expect(
      formatEvidenceSnippet({
        evidence_text: "证书载明资质类别为市政公用工程施工总承包二级。",
        snippet: "市政公用\nqualification\n机关\n{\"grade\":\"二级\"}",
        name: "市政资质"
      })
    ).toBe("证书载明资质类别为市政公用工程施工总承包二级。");
  });

  it("evidence_text 缺失时回退 snippet 并剥离末尾 JSON", () => {
    expect(
      formatEvidenceSnippet({
        evidence_text: null,
        snippet: "市政公用工程施工总承包二级资质\n证书正文\n{\"grade\": \"二级\", \"category\": \"市政\"}",
        name: "市政资质"
      })
    ).toBe("市政公用工程施工总承包二级资质\n证书正文");
  });

  it("evidence_text 与 snippet 都缺失时用资料名", () => {
    expect(
      formatEvidenceSnippet({ evidence_text: null, snippet: null, name: "标准化切片测试资质 0121347ABC" })
    ).toBe("标准化切片测试资质");
  });
});
