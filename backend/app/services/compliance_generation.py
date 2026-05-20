from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AsyncTask, AuditLog, ComplianceItem, Document, DocumentChunk, DocumentVersion
from app.services.llm_gateway import LLMGatewayError, chat_completion


GENERATION_KEYWORDS = (
    "资格",
    "资质",
    "营业执照",
    "许可证",
    "安全生产",
    "项目负责人",
    "建造师",
    "职称",
    "联合体",
    "业绩",
    "类似工程",
    "不得参加",
    "招标文件",
    "投标文件",
    "截止时间",
    "开标时间",
    "解密",
    "CA",
    "最高投标限价",
    "质量要求",
    "工期要求",
    "保修要求",
    "缺陷责任期",
    "标段划分",
    "资格审查",
    "评标办法",
    "综合评估法",
    "行政监督",
    "监督机构",
    "技术咨询",
    "技术支持",
    "咨询联系方式",
    "信息技术科",
    "招标范围",
    "技术要求",
    "技术响应",
    "技术参数",
    "设备",
    "型号",
    "净化",
    "洁净",
    "洁净等级",
    "风量",
    "过滤",
    "噪声",
    "压差",
    "材质",
    "安装调试",
    "验收",
    "售后",
)

VALID_ITEM_TYPES = {
    "qualification",
    "mandatory_response",
    "format",
    "deadline",
    "scoring",
    "reference_info",
    "technical_response",
    "other",
}
VALID_RISK_LEVELS = {"low", "medium", "high"}
PURE_HEADING_RE = re.compile(r"^\d+(?:[.．]\d+)*[.．、]?\s*[\w\u4e00-\u9fff（）()]{2,24}$")
CONTACT_KEYWORDS = ("联系方式", "招标代理机构", "联 系 人", "联系人", "电 话", "电话", "地 址", "地址")
REFERENCE_SIGNALS = (
    "行政监督",
    "监督机构",
    "技术咨询",
    "技术支持",
    "软件公司咨询",
    "咨询联系方式",
    "信息技术科",
    "CA技术支持",
    "400-",
)
REQUIREMENT_SIGNALS = (
    "须",
    "必须",
    "具备",
    "不得",
    "接受",
    "采用",
    "处于有效期",
    "要求",
    "截止",
    "投标人",
    "最高投标限价",
    "质量",
    "工期",
    "技术",
    "设备",
    "验收",
    "保修",
    "缺陷责任期",
    "标段划分",
    "CA",
)
TECHNICAL_SIGNALS = (
    "技术要求",
    "技术响应",
    "技术参数",
    "设备",
    "型号",
    "净化",
    "洁净",
    "洁净等级",
    "风量",
    "过滤",
    "噪声",
    "压差",
    "材质",
    "安装调试",
    "调试",
    "验收",
    "售后",
)
STRUCTURAL_HEADING_RE = re.compile(
    r"^(?:[一二三四五六七八九十]+[、.．]|[1-9]\d?(?:[.．]\d{1,2})*[.．、])\s*[^。；;]{2,40}[:：]?$"
)
LIST_MARKER_RE = re.compile(
    r"(?<![\w./])(?:[（(]\d+[）)]|[1-9]\d?(?:[.．]\d{1,2})+[.．]?|[1-9]\d?[.．])"
)


class ComplianceGenerationError(Exception):
    def __init__(self, message: str, *, code: str = "COMPLIANCE_GENERATION_FAILED") -> None:
        super().__init__(message)
        self.code = code


class LLMComplianceItem(BaseModel):
    source_chunk_index: int = Field(ge=1)
    item_type: str
    requirement_text: str = Field(min_length=1)
    normalized_requirement: str | None = None
    response_suggestion: str | None = None
    risk_level: str = "medium"
    is_mandatory: bool = True
    confidence_score: float = Field(default=0.75, ge=0, le=1)

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, value: str) -> str:
        if value in {"reference", "info", "reference_information"}:
            return "reference_info"
        return value if value in VALID_ITEM_TYPES else "other"

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        return value if value in VALID_RISK_LEVELS else "medium"


class LLMComplianceResponse(BaseModel):
    items: list[LLMComplianceItem]


@dataclass(frozen=True)
class ComplianceCandidate:
    source_chunk_index: int
    item_type: str
    requirement_text: str
    normalized_requirement: str
    response_suggestion: str | None
    risk_level: str
    is_mandatory: bool
    confidence_score: Decimal
    explanation_json: dict[str, Any]


def _coerce_task_id(task_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    try:
        return uuid.UUID(str(task_id))
    except ValueError as exc:
        raise ComplianceGenerationError("任务ID格式错误", code="INVALID_TASK_ID") from exc


def _clean_requirement_text(text: str) -> str:
    cleaned = " ".join(text.replace("\xa0", " ").split()).strip()
    return re.sub(r"^[□☐☑✓√？?]\s*", "", cleaned).strip()


def _heading_leaf(heading_path: str | None) -> str | None:
    if not heading_path:
        return None
    return heading_path.split("/")[-1].strip() or None


def _is_contact_text(text: str, heading_path: str | None) -> bool:
    combined = f"{heading_path or ''} {text}"
    if _is_reference_info(text, heading_path):
        return False
    return any(keyword in combined for keyword in CONTACT_KEYWORDS)


def _is_reference_info(text: str, heading_path: str | None) -> bool:
    combined = f"{heading_path or ''} {text}"
    return any(signal in combined for signal in REFERENCE_SIGNALS)


def _is_pure_heading(text: str) -> bool:
    if any(mark in text for mark in ("：", ":", "；", ";", "，", ",", "。")):
        return False
    return len(text) <= 28 and (
        bool(PURE_HEADING_RE.match(text)) or bool(STRUCTURAL_HEADING_RE.match(text))
    )


def _contextual_requirement_text(text: str, heading_path: str | None) -> str:
    leaf = _heading_leaf(heading_path)
    if leaf and len(text) <= 20 and text not in leaf and not STRUCTURAL_HEADING_RE.match(leaf):
        return f"{leaf.rstrip(':：')}：{text}"
    return text


def _normalized_key(text: str) -> str:
    cleaned = re.sub(r"\s+", "", text.lower())
    return "auto:" + hashlib.sha1(cleaned.encode("utf-8")).hexdigest()


def _semantic_key(text: str, item_type: str) -> str:
    if item_type == "deadline":
        date_match = re.search(
            r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{1,2})?\s*[点:：时]?\s*(\d{1,2})?",
            text,
        )
        if date_match:
            year, month, day, hour, minute = date_match.groups()
            return f"auto:deadline:{year}-{int(month):02d}-{int(day):02d}-{int(hour or 0):02d}-{int(minute or 0):02d}"
    if item_type == "format" and "下载招标文件" in text:
        return "auto:format:download-tender-file"
    cleaned = re.sub(r"^[（(]?\d+(?:[.．]\d+)*[）).．、]?\s*", "", text)
    return _normalized_key(cleaned)


def _confidence(value: float) -> Decimal:
    bounded = min(max(value, 0.0), 1.0)
    return Decimal(f"{bounded:.4f}")


def _item_type_label(value: str) -> str:
    return {
        "qualification": "资格要求",
        "mandatory_response": "强制响应",
        "format": "格式要求",
        "deadline": "截止时间",
        "scoring": "评分办法",
        "reference_info": "参考信息",
        "technical_response": "技术响应",
        "other": "其他",
    }.get(value, value)


def _matched_keywords(text: str, heading_path: str | None) -> list[str]:
    combined = f"{heading_path or ''} {text}"
    keywords = []
    for keyword in GENERATION_KEYWORDS + REQUIREMENT_SIGNALS + REFERENCE_SIGNALS:
        if keyword in combined and keyword not in keywords:
            keywords.append(keyword)
    return keywords[:10]


def _rule_code(item_type: str, text: str) -> str:
    if item_type == "reference_info":
        return "RULE-REFERENCE-INFO"
    if item_type == "scoring":
        return "RULE-SCORING-METHOD"
    if item_type == "technical_response":
        return "RULE-TECHNICAL-RESPONSE"
    if item_type == "deadline":
        return "RULE-DEADLINE"
    if item_type == "format":
        return "RULE-FORMAT"
    if item_type == "qualification":
        if "类似工程业绩要求：不要求" in text:
            return "RULE-QUALIFICATION-SIMILAR-PERFORMANCE"
        if "联合体牵头人单位人员" in text:
            return "RULE-QUALIFICATION-JOINT-VENTURE-LEADER"
        return "RULE-QUALIFICATION"
    if item_type == "mandatory_response":
        return "RULE-MANDATORY-RESPONSE"
    return "RULE-GENERAL"


def _rule_name(item_type: str, text: str) -> str:
    code = _rule_code(item_type, text)
    return {
        "RULE-REFERENCE-INFO": "参考信息识别",
        "RULE-SCORING-METHOD": "评标办法识别",
        "RULE-TECHNICAL-RESPONSE": "技术响应要求识别",
        "RULE-DEADLINE": "截止时间识别",
        "RULE-FORMAT": "格式与电子投标要求识别",
        "RULE-QUALIFICATION-SIMILAR-PERFORMANCE": "类似业绩要求识别",
        "RULE-QUALIFICATION-JOINT-VENTURE-LEADER": "联合体牵头人约束识别",
        "RULE-QUALIFICATION": "资格要求识别",
        "RULE-MANDATORY-RESPONSE": "强制响应条款识别",
        "RULE-GENERAL": "通用合规条款识别",
    }[code]


def _risk_reason(item_type: str, text: str, risk_level: str) -> str:
    if item_type == "reference_info":
        return "该条款用于投标过程参考或应急沟通，不直接形成资格阻断或强制响应风险。"
    if "类似工程业绩要求：不要求" in text:
        return "公告明确不要求类似工程业绩，当前项目准入风险较低。"
    if item_type == "technical_response":
        return "该条款涉及技术参数、设备配置、安装调试或验收响应，v1.0 只形成待确认技术响应项，不自动生成技术标承诺。"
    if any(keyword in text for keyword in ("保修要求", "缺陷责任期", "招标范围", "评标办法")):
        return "条款直接影响商务标响应完整性或投标策略，遗漏会影响标书实质响应。"
    if item_type == "qualification":
        return "资格类条款通常属于准入条件，缺失或不满足可能导致资格审查不通过。"
    if item_type == "deadline":
        return "截止时间或开标时间错过后通常无法补救，需要作为高风险时间节点处理。"
    if any(keyword in text for keyword in ("必须", "须", "不得", "最高投标限价", "CA")):
        return "原文包含必须、须、不得、限价或 CA 等强约束信号，需要逐条核验响应。"
    if risk_level == "medium":
        return "该条款需要投标文件响应或材料支撑，但暂未识别为一票否决条件。"
    return "该条款目前识别为低风险，保留来源证据供人工复核。"


def _batch_confirm_reason(risk_level: str, is_mandatory: bool) -> str:
    if risk_level == "high":
        return "高风险项不允许批量确认，必须逐条核验来源和响应证据。"
    if is_mandatory:
        return "强制项不允许批量确认，必须逐条人工确认。"
    return "非高风险且非强制项，可在人工确认范围内批量处理。"


def _candidate_explanation(
    *,
    item_type: str,
    text: str,
    heading_path: str | None,
    risk_level: str,
    is_mandatory: bool,
    extraction_provider: str,
) -> dict[str, Any]:
    keywords = _matched_keywords(text, heading_path)
    label = _item_type_label(item_type)
    heading_note = f"，所在章节为“{heading_path}”" if heading_path else ""
    keyword_note = f"命中关键词：{'、'.join(keywords)}" if keywords else "未命中显式关键词，按上下文归类"
    return {
        "rule_code": _rule_code(item_type, text),
        "rule_name": _rule_name(item_type, text),
        "rule_reason": f"{keyword_note}{heading_note}，因此识别为{label}。",
        "risk_reason": _risk_reason(item_type, text, risk_level),
        "batch_confirm_reason": _batch_confirm_reason(risk_level, is_mandatory),
        "matched_keywords": keywords,
        "extraction_provider": extraction_provider,
    }


def _chunk_payload(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_index": chunk.chunk_index,
            "heading_path": chunk.heading_path,
            "text": chunk.content_text,
        }
        for chunk in chunks
    ]


def _relevant_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    relevant = [
        chunk
        for chunk in chunks
        if any(
            keyword in f"{chunk.heading_path or ''} {chunk.content_text}"
            for keyword in GENERATION_KEYWORDS
        )
    ]
    return relevant[:80] if relevant else chunks[:60]


def _json_from_model_text(content: str) -> dict[str, Any]:
    content = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()
    return json.loads(content)


def _llm_prompt(chunks: list[DocumentChunk]) -> list[dict[str, str]]:
    payload = json.dumps(_chunk_payload(chunks), ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": (
                "你是招投标合规矩阵分析助手。请只输出 JSON，不要输出解释。"
                "任务是从招标公告/招标文件分块中抽取投标人必须响应或需要核验的合规项。"
            ),
        },
        {
            "role": "user",
            "content": (
                "请从下面的 chunks 中抽取合规矩阵候选项。只抽取文本中有证据的要求，"
                "不要编造。模板说明、未选中的 □ 选项不要抽取；如果勾选符号被识别成 ? 或 ？ ，"
                "请结合语义判断。每项必须引用 source_chunk_index。\n\n"
                "输出 JSON 格式：\n"
                "{ \"items\": [ {"
                "\"source_chunk_index\": 22,"
                "\"item_type\": \"qualification|mandatory_response|format|deadline|scoring|reference_info|technical_response|other\","
                "\"requirement_text\": \"原文要求\","
                "\"normalized_requirement\": \"简短归一化描述\","
                "\"response_suggestion\": \"投标响应建议或需准备材料\","
                "\"risk_level\": \"low|medium|high\","
                "\"is_mandatory\": true,"
                "\"confidence_score\": 0.0"
                "} ] }\n\n"
                f"chunks:\n{payload}"
            ),
        },
    ]


def _call_llm(
    db: Session,
    task: AsyncTask,
    chunks: list[DocumentChunk],
) -> tuple[str, list[ComplianceCandidate]]:
    messages = _llm_prompt(chunks)
    char_count = sum(len(chunk.content_text or "") for chunk in chunks)
    result = chat_completion(
        db,
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        section_id=task.section_id,
        actor_user_id=task.created_by,
        actor_type="worker",
        task_type="compliance_matrix_generation",
        prompt_version="compliance-matrix-extract@2026-05-17",
        messages=messages,
        complexity="complex" if len(chunks) >= 40 or char_count >= 6000 else "simple",
        temperature=0.0,
        response_format={"type": "json_object"},
        evidence_refs={
            "chunk_ids": [str(chunk.id) for chunk in chunks],
            "chunk_indexes": [chunk.chunk_index for chunk in chunks],
            "document_version_ids": sorted({str(chunk.document_version_id) for chunk in chunks}),
        },
    )
    parsed = LLMComplianceResponse.model_validate(_json_from_model_text(result.content))
    chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    candidates: list[ComplianceCandidate] = []
    for item in parsed.items:
        cleaned_text = _clean_requirement_text(item.requirement_text)
        if not cleaned_text:
            continue
        source_chunk = chunk_by_index.get(item.source_chunk_index)
        candidates.append(
            ComplianceCandidate(
                source_chunk_index=item.source_chunk_index,
                item_type=item.item_type,
                requirement_text=cleaned_text,
                normalized_requirement=item.normalized_requirement or _normalized_key(item.requirement_text),
                response_suggestion=item.response_suggestion,
                risk_level=item.risk_level,
                is_mandatory=item.is_mandatory,
                confidence_score=_confidence(item.confidence_score),
                explanation_json=_candidate_explanation(
                    item_type=item.item_type,
                    text=cleaned_text,
                    heading_path=source_chunk.heading_path if source_chunk else None,
                    risk_level=item.risk_level,
                    is_mandatory=item.is_mandatory,
                    extraction_provider=f"{result.provider}:{result.model_name}",
                ),
            )
        )
    return f"{result.provider}:{result.model_name}", candidates


def _rule_item_type(text: str, heading_path: str | None) -> str:
    heading_leaf = _heading_leaf(heading_path) or ""
    qualification_context = "资格" in heading_leaf and len(heading_leaf) <= 40
    technical_context = any(signal in heading_leaf for signal in ("技术要求", "技术响应", "技术参数", "采购需求"))
    if _is_reference_info(text, heading_path):
        return "reference_info"
    if any(keyword in text for keyword in ("评标办法", "综合评估法")):
        return "scoring"
    if any(keyword in text for keyword in ("截止时间", "开标时间", "解密", "递交")):
        return "deadline"
    if ("请于" in text and "至" in text) or re.search(
        r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", text
    ):
        return "deadline"
    if any(
        keyword in text
        for keyword in (
            "资格",
            "资质",
            "营业执照",
            "许可证",
            "项目负责人",
            "建造师",
            "职称",
            "联合体",
            "业绩",
            "标段划分",
            "资格审查",
            "资格后审",
            "牵头人单位",
        )
    ) or qualification_context:
        return "qualification"
    if any(keyword in text for keyword in ("电子", "CA", "格式", "制作工具", "下载", "公共资源交易平台")):
        return "format"
    if any(keyword in text for keyword in TECHNICAL_SIGNALS) or technical_context:
        return "technical_response"
    return "mandatory_response"


def _should_skip_rule_text(text: str, heading_path: str | None) -> bool:
    heading_leaf = _heading_leaf(heading_path)
    if heading_leaf and text == heading_leaf:
        return True
    if _is_contact_text(text, heading_path):
        return True
    if _is_pure_heading(text):
        return True
    if STRUCTURAL_HEADING_RE.match(text):
        return True
    if text.endswith(("：", ":")) and "类似工程业绩要求" in text:
        return True
    if text.endswith(("：", ":")) and not any(signal in text for signal in REQUIREMENT_SIGNALS):
        return True
    if text == "不要求" and "类似工程业绩要求" not in (heading_path or ""):
        return True
    if "由招标人根据招标项目具体情况" in text:
        return True
    if re.match(r"^(项目编号|项目名称|预算金额|售价|方式)[:：]", text):
        return True
    if "其他落实政府采购政策的资格要求" in text and "无" in text and len(text) <= 40:
        return True
    if text.startswith(("名 称：", "地 址：", "电 话：", "项目联系人：", "来源：")):
        return True
    if "【打印】" in text or "【显示公告概要】" in text:
        return True
    return False


def _split_by_markers(text: str) -> list[str]:
    matches = list(LIST_MARKER_RE.finditer(text))
    if len(matches) <= 1:
        return [text]
    parts: list[str] = []
    prefix = text[: matches[0].start()].strip()
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        if prefix and not re.match(r"^[（(]?\d+", prefix):
            part = f"{prefix.rstrip(':：')}：{part}"
        parts.append(part)
    return [part for part in parts if part]


def _split_qualification_series(text: str) -> list[str]:
    if "资质" not in text or "须具备" not in text:
        return [text]

    project_manager_split = re.split(r"[；;]\s*|[（(]2[）)]", text, maxsplit=1)
    supplier_text = project_manager_split[0].strip()
    tail_parts = [part.strip() for part in project_manager_split[1:] if part.strip()]

    requirements: list[str] = []
    prefix_match = re.search(r"(?:供应商|投标人)[^，；;]*须具备", supplier_text)
    prefix = prefix_match.group(0) if prefix_match else "供应商须具备"
    for material in re.split(r"[、，,]\s*", supplier_text):
        material = material.strip(" ；;。")
        if not material:
            continue
        if "资质" in material and material != prefix:
            cleaned = re.sub(r"^.*?须具备", "", material).strip()
            cleaned = re.sub(r"且具备有效的?安全生产许可证", "", cleaned).strip(" 、，,；;。")
            requirements.append(f"{prefix}{cleaned}。")
        if "安全生产许可证" in material:
            requirements.append("供应商须具备有效的安全生产许可证。")

    for tail in tail_parts:
        if "项目经理" in tail and "建造师" in tail:
            requirements.append(f"供应商拟派项目经理须具备{re.sub(r'^供应商拟派项目经理须具备', '', tail).strip(' 。；;')}。")
        else:
            requirements.append(tail if tail.endswith("。") else f"{tail}。")

    return requirements or [text]


def _split_project_overview(text: str) -> list[str]:
    if "获取招标文件" not in text or "前递交投标文件" not in text:
        return [text]

    requirements: list[str] = []
    download_match = re.search(r"潜在投标人应在(?P<download>.+?)获取招标文件", text)
    if download_match:
        requirements.append(f"潜在投标人应在{download_match.group('download').strip()}获取招标文件。")

    deadline_match = re.search(
        r"并于(?P<deadline>\d{4}年\d{2}月\d{2}日\s*\d{2}点\d{2}分（北京时间）)前递交投标文件",
        text,
    )
    if deadline_match:
        requirements.append(f"投标文件递交截止时间为{deadline_match.group('deadline')}。")

    return requirements or [text]


def _atomic_requirement_texts(text: str) -> list[str]:
    overview_parts = _split_project_overview(text)
    atomic: list[str] = []
    for overview_part in overview_parts:
        marker_parts = _split_by_markers(overview_part)
        for part in marker_parts:
            atomic.extend(_split_qualification_series(part))
    return [item.strip() for item in atomic if item.strip()]


def _risk_level(item_type: str, text: str) -> str:
    if item_type == "reference_info":
        return "low"
    if "类似工程业绩要求：不要求" in text:
        return "low"
    if any(keyword in text for keyword in ("保修要求", "缺陷责任期", "招标范围", "评标办法")):
        return "high"
    if item_type == "technical_response":
        if any(keyword in text for keyword in ("必须", "须", "不得", "验收", "洁净等级", "风量", "压差")):
            return "high"
        return "medium"
    if item_type in {"qualification", "deadline"}:
        return "high"
    if any(keyword in text for keyword in ("必须", "须", "不得", "最高投标限价", "CA")):
        return "high"
    return "medium"


def _response_suggestion(item_type: str, text: str) -> str:
    if item_type == "reference_info":
        return "作为投标过程参考信息保留，必要时用于异议、投诉或电子投标应急沟通。"
    if item_type == "scoring":
        return "请结合评标办法核对技术方案、资信、报价等编制策略和分值权重。"
    if item_type == "technical_response":
        return "请作为技术响应待确认项处理，先核对企业资料或产品资料能否支撑，v1.0 不自动生成技术标承诺。"
    if item_type == "qualification":
        if "类似工程业绩要求：不要求" in text:
            return "本项目不要求类似工程业绩，确认后可标记为无需绑定业绩证明。"
        if "项目建议书" in text and "不得参加投标" in text:
            return "请确认投标单位及联合体成员未参与本项目建议书、可研、初设文件编制或评估；未选“允许参加投标”作为原文对照。"
        return "请从企业资质库、人员库或联合体资料中绑定证明材料，并由人工复核。"
    if item_type == "deadline":
        return "请同步到项目时间节点，设置提醒并核对投标文件递交计划。"
    if item_type == "format":
        return "请核对电子投标平台、CA、文件制作工具和上传格式要求。"
    if "最高投标限价" in text:
        return "请在报价测算中校验报价不得超过最高投标限价。"
    return "请在投标文件中逐项响应，并绑定对应证据来源。"


def _extra_candidates_for_chunk(
    chunk: DocumentChunk,
    text: str,
    seen: set[str],
) -> list[ComplianceCandidate]:
    extras: list[ComplianceCandidate] = []
    if "拟任工程总承包项目负责人须为联合体牵头人单位人员" in text:
        requirement = "以联合体投标的，拟任工程总承包项目负责人须为联合体牵头人单位人员。"
        normalized = _normalized_key(requirement)
        if normalized not in seen:
            seen.add(normalized)
            extras.append(
                ComplianceCandidate(
                    source_chunk_index=chunk.chunk_index,
                    item_type="qualification",
                    requirement_text=requirement,
                    normalized_requirement=normalized,
                    response_suggestion="联合体投标时，请确认牵头人单位与拟任工程总承包项目负责人所属单位一致。",
                    risk_level="high",
                    is_mandatory=True,
                    confidence_score=Decimal("0.7000"),
                    explanation_json=_candidate_explanation(
                        item_type="qualification",
                        text=requirement,
                        heading_path=chunk.heading_path,
                        risk_level="high",
                        is_mandatory=True,
                        extraction_provider="rules",
                    ),
                )
            )
    return extras


def _rule_extract(chunks: list[DocumentChunk]) -> list[ComplianceCandidate]:
    candidates: list[ComplianceCandidate] = []
    seen: set[str] = set()
    for chunk in chunks:
        original_text = _clean_requirement_text(chunk.content_text)
        is_similar_performance_not_required = (
            original_text == "不要求" and "类似工程业绩要求" in (chunk.heading_path or "")
        )
        if not original_text or (len(original_text) < 4 and not is_similar_performance_not_required):
            continue
        if chunk.content_text.lstrip().startswith("□"):
            continue
        if "□" in chunk.content_text and "？" not in chunk.content_text and "?" not in chunk.content_text:
            continue
        if _should_skip_rule_text(original_text, chunk.heading_path):
            continue

        for text in _atomic_requirement_texts(original_text):
            if _should_skip_rule_text(text, chunk.heading_path):
                continue
            if text == "采用资格后审方式":
                text = _contextual_requirement_text(text, chunk.heading_path)
            elif text == "不要求":
                text = _contextual_requirement_text(text, chunk.heading_path)
            elif "不得参加投标" == text and "项目建议书" in (chunk.heading_path or ""):
                text = _contextual_requirement_text(text, chunk.heading_path)
            else:
                text = _contextual_requirement_text(text, chunk.heading_path)

            item_type = _rule_item_type(text, chunk.heading_path)
            if item_type == "mandatory_response" and not any(
                keyword in text
                for keyword in (
                    "须",
                    "必须",
                    "不得",
                    "最高投标限价",
                    "质量",
                    "工期",
                    "保修",
                    "缺陷责任期",
                    "招标范围",
                    "合同履行期限",
                )
            ):
                continue

            normalized = _semantic_key(text, item_type)
            if normalized in seen:
                continue
            seen.add(normalized)
            risk_level = _risk_level(item_type, text)
            is_mandatory = risk_level == "high" or item_type in {"qualification", "deadline"}
            candidates.append(
                ComplianceCandidate(
                    source_chunk_index=chunk.chunk_index,
                    item_type=item_type,
                    requirement_text=text,
                    normalized_requirement=normalized,
                    response_suggestion=_response_suggestion(item_type, text),
                    risk_level=risk_level,
                    is_mandatory=is_mandatory,
                    confidence_score=Decimal("0.6500"),
                    explanation_json=_candidate_explanation(
                        item_type=item_type,
                        text=text,
                        heading_path=chunk.heading_path,
                        risk_level=risk_level,
                        is_mandatory=is_mandatory,
                        extraction_provider="rules",
                    ),
                )
            )
            candidates.extend(_extra_candidates_for_chunk(chunk, text, seen))
    return candidates


def extract_compliance_candidates(
    db: Session,
    task: AsyncTask,
    chunks: list[DocumentChunk],
) -> tuple[str, list[ComplianceCandidate]]:
    relevant = _relevant_chunks(chunks)
    try:
        provider, candidates = _call_llm(db, task, relevant)
        if candidates:
            return provider, candidates
    except (LLMGatewayError, KeyError, TypeError, ValidationError, json.JSONDecodeError):
        pass
    return "rules", _rule_extract(relevant)


def _select_document_version(
    db: Session,
    task: AsyncTask,
) -> tuple[Document, DocumentVersion]:
    input_json = task.input_json or {}
    document_id = input_json.get("document_id")
    version_id = input_json.get("document_version_id")

    if version_id:
        version = db.get(DocumentVersion, uuid.UUID(str(version_id)))
        if version is None:
            raise ComplianceGenerationError("指定文档版本不存在", code="DOCUMENT_VERSION_NOT_FOUND")
        document = db.get(Document, version.document_id)
        if document is None:
            raise ComplianceGenerationError("指定文档不存在", code="DOCUMENT_NOT_FOUND")
        return document, version

    stmt = (
        select(Document, DocumentVersion)
        .join(DocumentVersion, DocumentVersion.id == Document.current_version_id)
        .where(
            Document.tenant_id == task.tenant_id,
            Document.project_id == task.project_id,
            Document.section_id == task.section_id,
            Document.status != "deleted",
            DocumentVersion.parse_status.in_(("succeeded", "frozen")),
        )
        .order_by(Document.updated_at.desc(), Document.created_at.desc())
        .limit(1)
    )
    if document_id:
        stmt = stmt.where(Document.id == uuid.UUID(str(document_id)))
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise ComplianceGenerationError("没有可用于生成矩阵的已解析文档", code="NO_PARSED_DOCUMENT")
    return row[0], row[1]


def _add_generation_audit(
    db: Session,
    task: AsyncTask,
    *,
    action: str,
    after_json: dict[str, Any],
    severity: str = "info",
) -> None:
    db.add(
        AuditLog(
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            actor_user_id=task.created_by,
            actor_type="worker",
            action=action,
            object_type="async_task",
            object_id=task.id,
            after_json=after_json,
            reason="生成合规矩阵候选项",
            severity=severity,
        )
    )


def execute_compliance_matrix_generation_task(
    db: Session,
    task_id: uuid.UUID | str,
) -> dict[str, str | int]:
    task_uuid = _coerce_task_id(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "matrix_generate":
        raise ComplianceGenerationError("矩阵生成任务不存在", code="TASK_NOT_FOUND")

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = 20
    db.commit()

    try:
        document, version = _select_document_version(db, task)
        chunks = db.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.tenant_id == task.tenant_id,
                DocumentChunk.document_version_id == version.id,
            )
            .order_by(DocumentChunk.chunk_index)
        ).all()
        if not chunks:
            raise ComplianceGenerationError("文档版本没有解析分块", code="NO_DOCUMENT_CHUNKS")

        provider, candidates = extract_compliance_candidates(db, task, list(chunks))
        chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
        created_count = 0
        updated_count = 0
        skipped_count = 0
        superseded_count = 0

        if (task.input_json or {}).get("force"):
            stale_items = db.scalars(
                select(ComplianceItem).where(
                    ComplianceItem.tenant_id == task.tenant_id,
                    ComplianceItem.project_id == task.project_id,
                    ComplianceItem.section_id == task.section_id,
                    ComplianceItem.deleted_at.is_(None),
                )
            ).all()
            for item in stale_items:
                item.status = "superseded"
                item.deleted_at = now
                item.modified_by = task.created_by
                item.modified_at = now
                item.modify_reason = "强制重新生成合规矩阵，旧候选项自动淘汰"
                superseded_count += 1

        for candidate in candidates:
            chunk = chunk_by_index.get(candidate.source_chunk_index)
            if chunk is None:
                skipped_count += 1
                continue

            existing = db.scalar(
                select(ComplianceItem).where(
                    ComplianceItem.tenant_id == task.tenant_id,
                    ComplianceItem.project_id == task.project_id,
                    ComplianceItem.section_id == task.section_id,
                    ComplianceItem.source_version_id == version.id,
                    ComplianceItem.normalized_requirement == candidate.normalized_requirement,
                    ComplianceItem.deleted_at.is_(None),
                )
            )
            is_batch_confirm_allowed = (
                candidate.risk_level != "high" and not candidate.is_mandatory
            )
            if existing is None:
                db.add(
                    ComplianceItem(
                        tenant_id=task.tenant_id,
                        project_id=task.project_id,
                        section_id=task.section_id,
                        source_document_id=document.id,
                        source_version_id=version.id,
                        source_chunk_id=chunk.id,
                        source_page_no=chunk.page_no,
                        item_type=candidate.item_type,
                        requirement_text=candidate.requirement_text,
                        normalized_requirement=candidate.normalized_requirement,
                        response_suggestion=candidate.response_suggestion,
                        evidence_text=chunk.content_text,
                        explanation_json=candidate.explanation_json,
                        status="pending_confirm",
                        risk_level=candidate.risk_level,
                        is_mandatory=candidate.is_mandatory,
                        is_batch_confirm_allowed=is_batch_confirm_allowed,
                        confidence_score=candidate.confidence_score,
                        created_by=task.created_by,
                    )
                )
                created_count += 1
            else:
                existing.source_chunk_id = chunk.id
                existing.source_page_no = chunk.page_no
                existing.item_type = candidate.item_type
                existing.requirement_text = candidate.requirement_text
                existing.response_suggestion = candidate.response_suggestion
                existing.evidence_text = chunk.content_text
                existing.explanation_json = candidate.explanation_json
                existing.risk_level = candidate.risk_level
                existing.is_mandatory = candidate.is_mandatory
                existing.is_batch_confirm_allowed = is_batch_confirm_allowed
                existing.confidence_score = candidate.confidence_score
                existing.modified_by = task.created_by
                existing.modified_at = datetime.now(UTC)
                existing.modify_reason = "重新生成合规矩阵候选项"
                updated_count += 1

        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "provider": provider,
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "candidate_count": len(candidates),
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "superseded_count": superseded_count,
        }
        task.finished_at = datetime.now(UTC)
        _add_generation_audit(
            db,
            task,
            action="compliance.matrix_generated",
            after_json=task.output_json,
        )
        db.commit()
        return {
            "status": "succeeded",
            "provider": provider,
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "superseded_count": superseded_count,
        }
    except Exception as exc:
        error_code = exc.code if isinstance(exc, ComplianceGenerationError) else "COMPLIANCE_GENERATION_FAILED"
        task.status = "failed"
        task.progress = 100
        task.error_code = error_code
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        _add_generation_audit(
            db,
            task,
            action="compliance.matrix_generate_failed",
            after_json={"error_code": error_code, "error_message": str(exc)},
            severity="warning",
        )
        db.commit()
        return {"status": "failed", "error_code": error_code}
