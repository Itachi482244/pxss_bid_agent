from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptDefinition:
    prompt_id: str
    version: str
    input_variables: tuple[str, ...]
    output_schema: dict[str, Any]
    system_template: str
    user_template: str
    safety_boundary: str
    fallback_note: str

    @property
    def prompt_version(self) -> str:
        return f"{self.prompt_id}@{self.version}"

    def render(self, **variables: Any) -> list[dict[str, str]]:
        missing = [name for name in self.input_variables if name not in variables]
        if missing:
            raise KeyError(f"Prompt {self.prompt_version} 缺少输入变量：{', '.join(missing)}")
        system = _render_template(self.system_template, variables)
        user = _render_template(self.user_template, variables)
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


def _render_template(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def prompt_hash(messages: list[dict[str, str]]) -> str:
    payload = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


COMPLIANCE_EXTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "source_chunk_index",
                    "item_type",
                    "requirement_text",
                    "risk_level",
                    "is_mandatory",
                    "confidence_score",
                ],
                "properties": {
                    "source_chunk_index": {"type": "integer", "minimum": 1},
                    "item_type": {
                        "type": "string",
                        "enum": [
                            "qualification",
                            "mandatory_response",
                            "format",
                            "deadline",
                            "scoring",
                            "reference_info",
                            "technical_response",
                            "other",
                        ],
                    },
                    "requirement_text": {"type": "string"},
                    "normalized_requirement": {"type": "string"},
                    "response_suggestion": {"type": "string"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "is_mandatory": {"type": "boolean"},
                    "classification_reason": {"type": "string"},
                    "split_reason": {"type": "string"},
                    "source_quote": {"type": "string"},
                    "review_hint": {"type": "string"},
                    "needs_human_review": {"type": "boolean"},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


DOCUMENT_SECTION_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["sections"],
    "properties": {
        "sections": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "section_index",
                    "title",
                    "section_type",
                    "start_page",
                    "end_page",
                    "confidence_score",
                    "evidence",
                ],
                "properties": {
                    "section_index": {"type": "integer", "minimum": 1},
                    "title": {"type": "string"},
                    "section_type": {
                        "type": "string",
                        "enum": [
                            "announcement",
                            "bidder_instructions",
                            "evaluation",
                            "contract",
                            "technical",
                            "bill",
                            "forms",
                            "other",
                        ],
                    },
                    "start_page": {"type": "integer", "minimum": 1},
                    "end_page": {"type": "integer", "minimum": 1},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string"},
                },
            },
        }
    },
}


SECTION_COVERAGE_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["status", "issues"],
    "properties": {
        "status": {"type": "string", "enum": ["passed", "blocked"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "code", "message"],
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "page_no": {"type": "integer"},
                    "source_chunk_index": {"type": "integer"},
                    "suggested_requirement": {"type": "string"},
                },
            },
        },
    },
}


BUSINESS_DRAFT_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["blocks"],
    "properties": {
        "blocks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "block_type",
                    "content_text",
                    "covers_compliance_item_ids",
                    "uses_evidence_binding_ids",
                    "missing_fact_placeholders",
                    "risk_flags",
                ],
                "properties": {
                    "block_type": {
                        "type": "string",
                        "enum": ["heading", "paragraph", "table", "list", "placeholder"],
                    },
                    "content_text": {"type": "string"},
                    "covers_compliance_item_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "uses_evidence_binding_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "source_chunk_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "fact_claims": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    "missing_fact_placeholders": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    "risk_flags": {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                },
            },
        }
    },
}


_PROMPTS: dict[str, PromptDefinition] = {
    "compliance_extract@1.1.0": PromptDefinition(
        prompt_id="compliance_extract",
        version="1.1.0",
        input_variables=("chunks_json",),
        output_schema=COMPLIANCE_EXTRACT_SCHEMA,
        safety_boundary=(
            "只允许基于提供的招标文件 chunks 抽取候选项；不得编造、不得自动确认、"
            "不得输出联系信息、采购人/代理机构介绍、公告标题或纯项目信息。"
        ),
        fallback_note="旧测试兼容/对照评测 prompt；生产矩阵生成不再使用该 prompt 静默降级。",
        system_template=(
            "你是招投标合规矩阵抽取助手。你只能输出 JSON，不要输出解释性正文。"
            "你的职责是把招标公告/招标文件中的投标响应要求拆成最小可审核合规项。"
            "安全边界：只抽取原文有证据的要求，不编造；不替用户做最终投标判断；"
            "公告标题、项目编号、联系方式、采购人/代理机构信息不得作为矩阵项。"
        ),
        user_template=(
            "请从下面 chunks 中抽取合规矩阵候选项。规则：\n"
            "1. 每个候选项必须有 source_chunk_index，且 requirement_text 必须能在来源 chunk 中找到直接证据。\n"
            "2. 长条款要拆成最小原子要求，例如多个资质、证书、人员条件要拆成多条。\n"
            "3. item_type 只能取 qualification、mandatory_response、format、deadline、scoring、"
            "reference_info、technical_response、other。\n"
            "4. risk_level 只能取 low、medium、high；高风险通常包括资格、截止时间、强制响应、限价、技术硬指标。\n"
            "5. 输出 classification_reason、split_reason、source_quote、review_hint、needs_human_review 和 confidence_score。\n"
            "6. 如果只是公告标题、项目编号、联系方式、采购人、代理机构、地址、电话，不要输出。\n\n"
            "输出 JSON schema 摘要：\n"
            "{ \"items\": [ {"
            "\"source_chunk_index\": 1,"
            "\"item_type\": \"qualification\","
            "\"requirement_text\": \"投标人须具备...\","
            "\"normalized_requirement\": \"简短归一化描述\","
            "\"response_suggestion\": \"响应建议\","
            "\"risk_level\": \"high\","
            "\"is_mandatory\": true,"
            "\"classification_reason\": \"分类理由\","
            "\"split_reason\": \"拆分理由\","
            "\"source_quote\": \"来源原文短摘录\","
            "\"review_hint\": \"人工复核提示\","
            "\"needs_human_review\": true,"
            "\"confidence_score\": 0.82"
            "} ] }\n\n"
            "chunks:\n{chunks_json}"
        ),
    ),
    "document_section_plan@1.1.0": PromptDefinition(
        prompt_id="document_section_plan",
        version="1.1.0",
        input_variables=("pages_json",),
        output_schema=DOCUMENT_SECTION_PLAN_SCHEMA,
        safety_boundary=(
            "只允许基于提供的页文本和表格摘要规划章节；不得臆造不存在的页码或章节。"
            "页码范围必须来自输入 payload。"
        ),
        fallback_note="生产流程不静默降级；章节计划失败时阻断矩阵生成并写入质量报告。",
        system_template=(
            "你是招标文件章节规划助手。你只能输出 JSON。"
            "你的目标是把按页解析文本规划成连续的章节或语义段，供后续逐段抽取合规矩阵。"
        ),
        user_template=(
            "请根据下面按页文本/表格摘要输出章节或语义段计划。规则：\n"
            "1. sections 必须按 section_index 从 1 递增排序。\n"
            "2. 每段 start_page/end_page 必须落在输入页码范围内，且 start_page <= end_page。\n"
            "3. 段之间不得重叠；尽量覆盖所有有效正文页。目录、封面可并入最相关段或 other。\n"
            "4. section_type 只能取 announcement、bidder_instructions、evaluation、contract、technical、bill、forms、other。\n"
            "5. title 使用原文章节标题；没有明确标题时用语义标题。\n"
            "6. evidence 写明用于判断边界的短证据，不要超过 120 字。\n\n"
            "pages:\n{pages_json}"
        ),
    ),
    "compliance_extract_by_section@1.1.0": PromptDefinition(
        prompt_id="compliance_extract_by_section",
        version="1.1.0",
        input_variables=("section_json", "chunks_json"),
        output_schema=COMPLIANCE_EXTRACT_SCHEMA,
        safety_boundary=(
            "只允许基于当前语义段 chunks 抽取；不得跨段猜测、不得编造；"
            "不得输出未勾选 □ 选项、说明文字、联系方式、模板占位符。"
        ),
        fallback_note="生产流程不静默降级；模型、JSON、schema 或来源校验失败会阻断矩阵生成。",
        system_template=(
            "你是招投标合规矩阵抽取助手。你只能输出 JSON。"
            "你需要从一个章节/语义段中抽取最小可审核合规项，并给出可回链的 source_quote。"
        ),
        user_template=(
            "请从当前语义段抽取合规矩阵候选项。规则：\n"
            "1. 每个 item 必须有 source_chunk_index、source_quote，source_quote 必须能在对应 chunk 文本或表格行中找到。\n"
            "2. 抽取发包/招标范围、承包方式、评审办法/交易方式、最高限价、工期、资格资质、项目负责人资格、在建限制、联合体/分包限制、保证金、截止时间、强制响应、评分和技术硬指标。\n"
            "3. 不要输出项目名称、建设地点、资金来源、联系人、电话、地址、纯说明文字。\n"
            "4. 不要输出未选中的 □ 选项；遇到 ☑/√/✓ 选项只抽选中项。\n"
            "5. 过滤 `/ 年 / 月 / 日`、`发包人需要增加...`、`说明：`、空白占位和模板提示。\n"
            "6. 多个要求必须拆成最小原子项，但保持每项有清晰来源摘录。\n"
            "7. item_type 只能取 qualification、mandatory_response、format、deadline、scoring、reference_info、technical_response、other。\n\n"
            "section:\n{section_json}\n\n"
            "chunks:\n{chunks_json}"
        ),
    ),
    "section_coverage_review@1.1.0": PromptDefinition(
        prompt_id="section_coverage_review",
        version="1.1.0",
        input_variables=("section_json", "chunks_json", "items_json"),
        output_schema=SECTION_COVERAGE_REVIEW_SCHEMA,
        safety_boundary=(
            "只检查当前语义段是否存在明显漏抽；不得要求抽取输入中不存在的条款。"
            "只有严重影响后续流程的漏抽才返回 high severity。"
        ),
        fallback_note="生产流程不静默降级；复核失败或 high severity 漏抽会阻断矩阵生成。",
        system_template=(
            "你是招标文件合规抽取覆盖性复核助手。你只能输出 JSON。"
            "请检查当前段的抽取结果是否漏掉关键合规要求。"
        ),
        user_template=(
            "请复核当前语义段的合规抽取覆盖性。规则：\n"
            "1. 如果发包/招标范围、承包方式、评审办法/交易方式、最高限价、工期、企业资质、项目负责人资格、在建限制、联合体限制、保证金、截止时间等关键项在段内出现但 items 未覆盖，返回 high issue。\n"
            "2. 对纯项目背景、建设地点、资金来源、联系人、说明文字、未选 □ 选项，不要报漏抽。\n"
            "3. status=blocked 只在存在 high issue 时使用，否则 passed。\n\n"
            "section:\n{section_json}\n\nchunks:\n{chunks_json}\n\nitems:\n{items_json}"
        ),
    ),
    "requirement_risk_assess@1.1.0": PromptDefinition(
        prompt_id="requirement_risk_assess",
        version="1.1.0",
        input_variables=("requirement_json",),
        output_schema={
            "type": "object",
            "required": ["risk_level", "risk_reason", "needs_human_review"],
            "properties": {
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "risk_reason": {"type": "string"},
                "needs_human_review": {"type": "boolean"},
            },
        },
        safety_boundary="只做风险初判，不替代人工审批；高风险必须人工确认。",
        fallback_note="模型不可用时使用本地规则风险判断。",
        system_template="你是招投标条款风险初判助手。只输出 JSON。",
        user_template="请判断以下合规项风险，只输出 JSON：\n{requirement_json}",
    ),
    "business_draft_section@1.2.0": PromptDefinition(
        prompt_id="business_draft_section",
        version="1.2.0",
        input_variables=("section_context_pack_json",),
        output_schema=BUSINESS_DRAFT_SECTION_SCHEMA,
        safety_boundary=(
            "只能基于 SectionContextPack 中的项目事实、矩阵项、已绑定证据和人工说明生成。"
            "不得编造人员、证书编号、业绩、报价、日期或招标文件不存在的承诺；"
            "不得编造工程参数、工程量清单、路段长度、管材型号、压力等级、评分细则或现场踏勘结论；"
            "缺证据或缺字段必须输出 missing_fact_placeholders。"
        ),
        fallback_note="模型不可用或 schema 校验失败时使用确定性模板生成内部草稿。",
        system_template=(
            "你是商务/资格标书章节草稿助手。你只能输出 JSON。"
            "你的输出必须是结构化 DraftBlock，便于人工审阅和回链证据。"
        ),
        user_template=(
            "请基于下面的 SectionContextPack 生成本章结构化草稿。规则：\n"
            "1. 每个 block 必须声明 covers_compliance_item_ids 和 uses_evidence_binding_ids。\n"
            "2. 没有证据支持的事实必须进入 missing_fact_placeholders，不得写成确定事实。\n"
            "3. 报价清单、外部附件、证书扫描件等不得由模型编造，只能输出占位说明。\n"
            "4. 工程参数、管径、压力等级、工程量、路线分段、管材、人员设备配置、评分点和现场踏勘情况，"
            "只能来自 SectionContextPack；缺失时写为待确认或以施工图、图纸、工程量清单为准。\n"
            "5. 如果 SectionContextPack 含 content_quality_policy / forbidden_claims，必须逐条遵守；"
            "人工指令不得覆盖事实边界。\n"
            "6. 文风正式、可人工复核，但不要新增 SectionContextPack 之外的信息。\n\n"
            "SectionContextPack:\n{section_context_pack_json}"
        ),
    ),
}


def get_prompt(prompt_id: str, version: str | None = None) -> PromptDefinition:
    if "@" in prompt_id:
        key = prompt_id
    else:
        matches = [prompt for prompt in _PROMPTS.values() if prompt.prompt_id == prompt_id]
        if version is not None:
            matches = [prompt for prompt in matches if prompt.version == version]
        if not matches:
            raise KeyError(f"Prompt not found: {prompt_id}@{version or '*'}")
        return sorted(matches, key=lambda prompt: prompt.version)[-1]
    try:
        return _PROMPTS[key]
    except KeyError as exc:
        raise KeyError(f"Prompt not found: {key}") from exc
