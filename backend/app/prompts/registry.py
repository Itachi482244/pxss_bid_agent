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
        fallback_note="模型不可用、JSON 失败、schema 失败、缺来源或规则冲突时降级到本地规则抽取。",
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
