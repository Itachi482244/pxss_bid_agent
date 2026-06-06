import { Tooltip } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";

/**
 * 术语白话化字典（MVP1.4 易用性优化）。
 *
 * 目的：把系统内部概念换成一线用户能直接看懂的大白话，仅用于"面向用户的展示文案"。
 * 约束：后端字段名、code、筛选 value 一律不改，这里只负责"怎么显示给人看"。
 *
 * 用法：
 *   - 静态文案直接用 `GLOSSARY.context_pack.plain`；
 *   - 需要保留专业概念并解释时，用 <TermHint term="context_pack" />。
 *
 * 措辞为初版，先上线再按反馈微调（与《投标Agent MVP-v1.4需求规划与开发进度.md》映射表一致）。
 */
export type GlossaryEntry = {
  /** 白话主词，直接展示给用户 */
  plain: string;
  /** 可选悬浮解释；保留专业概念时配合问号图标使用 */
  tip?: string;
  /** 原系统术语，便于检索与回溯，不直接展示 */
  legacy?: string;
};

export const GLOSSARY = {
  context_pack: {
    plain: "投标素材包",
    tip: "某一节标书在生成前整理好的资料与要求合集：包含已绑定证据、必须覆盖的条款和写作指令。",
    legacy: "ContextPack / 上下文包"
  },
  section_context_pack: {
    plain: "本节资料与要求",
    tip: "针对单个章节整理的素材与要求，是投标素材包的一部分。",
    legacy: "SectionContextPack"
  },
  mandatory_text: {
    plain: "必须原样写入的内容",
    tip: "由你指定、要求一字不改写进标书的原文。其中的事实仍会被核查，无法回链证据会拦截导出。",
    legacy: "强制措辞"
  },
  lightweight_rebuild: {
    plain: "快速重新生成",
    tip: "只改了写作指令（没改事实）时，沿用上一版已核实的事实快速重出，省去完整重建。",
    legacy: "轻量重建"
  },
  no_go: {
    plain: "不建议参标",
    tip: "系统判断该项目存在硬性资格或重大风险，不建议投标；可人工复核后决定是否继续。",
    legacy: "No-Go"
  },
  go: {
    plain: "建议参标",
    legacy: "Go"
  },
  matrix_version: {
    plain: "合规清单版本",
    tip: "招标要求拆解成的合规条目清单的版本号，每次重新生成会产生新版本。",
    legacy: "矩阵版本"
  },
  compliance_matrix: {
    plain: "合规清单",
    tip: "从招标文件拆解出的、必须逐条响应的要求清单。",
    legacy: "合规矩阵"
  },
  needs_confirm: {
    plain: "待确认的指定内容",
    tip: "你指定要原样写入的内容，导出前需要人工逐条确认。",
    legacy: "待确认强制措辞 / needs_confirm"
  },
  draft_fact: {
    plain: "草稿中的关键数据",
    tip: "草稿里涉及的名称、日期、金额、证书编号、人员、业绩等关键事实，会逐项核查来源。",
    legacy: "草稿事实"
  }
} satisfies Record<string, GlossaryEntry>;

export type GlossaryKey = keyof typeof GLOSSARY;

/** 取白话主词；未知 key 时回退到原文本，避免界面出现空白。 */
export function plainTerm(key: GlossaryKey, fallback?: string): string {
  return GLOSSARY[key]?.plain ?? fallback ?? key;
}

/**
 * 展示白话主词 + 问号悬浮解释。
 * 仅在需要保留专业概念、帮助用户建立认知时使用；纯文案替换直接用 plainTerm。
 */
export function TermHint({
  term,
  text,
  showIcon = true
}: {
  term: GlossaryKey;
  /** 覆盖展示文案，默认用白话主词 */
  text?: string;
  showIcon?: boolean;
}) {
  const entry = GLOSSARY[term] as GlossaryEntry | undefined;
  const label = text ?? entry?.plain ?? term;
  if (!entry?.tip) return <>{label}</>;
  return (
    <Tooltip title={entry.tip}>
      <span style={{ borderBottom: "1px dashed currentColor", cursor: "help" }}>
        {label}
        {showIcon && <QuestionCircleOutlined style={{ marginLeft: 4, opacity: 0.65 }} />}
      </span>
    </Tooltip>
  );
}
