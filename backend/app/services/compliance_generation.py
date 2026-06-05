from __future__ import annotations

import contextvars
import hashlib
import json
import re
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import observed_task
from app.db.session import SessionLocal
from app.models import (
    AsyncTask,
    AuditLog,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentExtractionQualityReport,
    DocumentSemanticSection,
    DocumentVersion,
)
from app.prompts import get_prompt
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
LLM_LOW_CONFIDENCE_THRESHOLD = 0.60
FORK_JOIN_PROGRESS_HEARTBEAT_SECONDS = 15.0
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
    r"(?<![\w./])(?:[（(]\d+[）)]|[1-9]\d?(?:[.．]\d{1,2})+[.．]?|[1-9]\d?[.．、])"
)
CHINESE_LIST_MARKER_RE = re.compile(
    r"(^|[\s。；;！？!?])([一二三四五六七八九十]{1,3})[、.．]"
)
CHINESE_NUMERAL_VALUES = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
OPTION_MARKER_RE = re.compile(r"\s*[□☐\uf0a3]\s*")
PDF_NOISE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])0?43607(?![A-Za-z0-9])")
PAGE_FOOTER_RE = re.compile(r"\s*[-－]\s*\d{1,4}\s*[-－]\s*")
CIRCLED_LIST_MARKER_RE = re.compile(r"(?<![\w])([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])")
CHINESE_PAREN_MARKER_RE = re.compile(r"(?<![\w])([（(][一二三四五六七八九十]{1,3}[）)])")
SECTION_PLAN_HEADING_SIGNALS = (
    "章",
    "节",
    "篇",
    "交易公告",
    "招标公告",
    "采购公告",
    "投标人须知",
    "交易须知",
    "评标",
    "评审",
    "合同",
    "技术",
    "工程量清单",
    "清单",
    "图纸",
    "响应文件格式",
    "投标文件格式",
    "资格",
    "资质",
    "前附表",
)
SECTION_EXTRACT_MAX_CHARS = 4_500
SECTION_EXTRACT_MAX_CHUNKS = 10
SECTION_EXTRACT_MAX_PAGES = 6
SECTION_RETRY_MAX_CHARS = 1_800
SECTION_RETRY_MAX_CHUNKS = 5


class ComplianceGenerationError(Exception):
    def __init__(self, message: str, *, code: str = "COMPLIANCE_GENERATION_FAILED") -> None:
        super().__init__(message)
        self.code = code


class ComplianceQualityGateError(ComplianceGenerationError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "QUALITY_GATE_BLOCKED",
        issues: list[dict[str, Any]] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.issues = issues or []
        self.summary = summary or {}


class LLMComplianceItem(BaseModel):
    source_chunk_index: int = Field(ge=1)
    item_type: str
    requirement_text: str = Field(min_length=1)
    normalized_requirement: str | None = None
    response_suggestion: str | None = None
    risk_level: str = "medium"
    is_mandatory: bool = True
    classification_reason: str | None = None
    split_reason: str | None = None
    source_quote: str | None = None
    review_hint: str | None = None
    needs_human_review: bool = False
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


class LLMDocumentSection(BaseModel):
    section_index: int = Field(ge=1)
    title: str = Field(min_length=1)
    section_type: str = "other"
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    confidence_score: float = Field(default=0.75, ge=0, le=1)
    evidence: str = ""

    @field_validator("section_type")
    @classmethod
    def validate_section_type(cls, value: str) -> str:
        allowed = {
            "announcement",
            "bidder_instructions",
            "evaluation",
            "contract",
            "technical",
            "bill",
            "forms",
            "other",
        }
        return value if value in allowed else "other"


class LLMDocumentSectionPlan(BaseModel):
    sections: list[LLMDocumentSection] = Field(min_length=1)


class LLMCoverageIssue(BaseModel):
    severity: str = "medium"
    code: str = "COVERAGE_REVIEW_ISSUE"
    message: str
    page_no: int | None = None
    source_chunk_index: int | None = None
    suggested_requirement: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        return value if value in {"low", "medium", "high"} else "medium"


class LLMCoverageReview(BaseModel):
    status: str = "passed"
    issues: list[LLMCoverageIssue] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return value if value in {"passed", "blocked"} else "blocked"


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


@dataclass(frozen=True)
class SectionComplianceForkResult:
    section_position: int
    provider: str
    candidates: list[ComplianceCandidate]
    issues: list[dict[str, Any]]
    summary: dict[str, Any]


def _coerce_task_id(task_id: uuid.UUID | str) -> uuid.UUID:
    if isinstance(task_id, uuid.UUID):
        return task_id
    try:
        return uuid.UUID(str(task_id))
    except ValueError as exc:
        raise ComplianceGenerationError("任务ID格式错误", code="INVALID_TASK_ID") from exc


def _update_matrix_task_progress(
    db: Session,
    task: AsyncTask,
    *,
    progress: int,
    stage: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    task.progress = max(int(task.progress or 0), min(progress, 99))
    task.output_json = {
        "progress_stage": stage,
        "progress_message": message,
        **(extra or {}),
    }
    db.commit()


def _clean_requirement_text(text: str) -> str:
    cleaned = " ".join(text.replace("\xa0", " ").split()).strip()
    cleaned = PDF_NOISE_TOKEN_RE.sub(" ", cleaned)
    cleaned = PAGE_FOOTER_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()
    cleaned = re.sub(r"^[□☐☑✓√？?]\s*", "", cleaned).strip()
    return re.sub(r"(具备)\s+\1", r"\1", cleaned)


def _heading_leaf(heading_path: str | None) -> str | None:
    if not heading_path:
        return None
    leaf = heading_path.split("/")[-1].strip()
    if re.fullmatch(r"PDF\s*第\s*\d+\s*页", leaf):
        return None
    return leaf or None


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
    if text == "不要求" and "类似工程业绩要求" in (heading_path or ""):
        return "类似工程业绩要求：不要求。"
    if text == "采用资格后审方式" and "资格审查" in (heading_path or ""):
        return "资格审查方式：采用资格后审方式。"
    if leaf and len(text) <= 20 and text not in leaf and not STRUCTURAL_HEADING_RE.match(leaf):
        return f"{leaf.rstrip(':：')}：{text}"
    return text


def _is_standalone_date_text(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*(?:\d{1,2}\s*[点:：时]\s*(?:\d{1,2}\s*分?)?)?",
            text.strip(),
        )
    )


def _normalized_key(text: str) -> str:
    cleaned = re.sub(r"^[（(]?\d+(?:[.．]\d+)*[）).．、]?\s*", "", text.lower())
    cleaned = re.sub(r"[\s，,。；;：:（）()、.．]+", "", cleaned)
    return "auto:" + hashlib.sha1(cleaned.encode("utf-8")).hexdigest()


def _semantic_key(text: str, item_type: str) -> str:
    compact = _compact_for_match(text)
    if "类似工程业绩要求" in compact and "不要求" in compact:
        return "auto:qualification:similar-performance-not-required"
    if "接受联合体投标" in compact and "不接受联合体投标" not in compact:
        return "auto:qualification:joint-venture-accepted"
    if "拟任工程总承包项目负责人须为联合体牵头人单位人员" in compact:
        return "auto:qualification:joint-venture-leader-personnel"
    duration_match = re.search(r"工期要求[：:]?\s*(\d+)\s*[？?□☐\s]*天", text)
    if duration_match:
        return f"auto:mandatory:duration-days:{int(duration_match.group(1))}"
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
    if any(keyword in text for keyword in ("必须", "须", "不得", "不允许", "最高投标限价", "最高报价限价", "CA")):
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
        "source_quote": text[:300],
    }


def _chunk_payload(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_index": chunk.chunk_index,
            "page_no": chunk.page_no,
            "heading_path": chunk.heading_path,
            "text": chunk.content_text,
        }
        for chunk in chunks
    ]


def _chunk_effective_page_no(chunk: DocumentChunk) -> int:
    if chunk.page_no is not None:
        return int(chunk.page_no)
    return int(chunk.chunk_index or 1)


def _section_plan_limits(page_count: int) -> tuple[int, int, int]:
    if page_count >= 100:
        return 120, 2, 100
    if page_count >= 60:
        return 240, 2, 120
    if page_count >= 25:
        return 520, 5, 180
    return 900, 8, 220


def _section_plan_excerpt(text: str, *, max_chars: int) -> str:
    lines = [_clean_requirement_text(line) for line in re.split(r"[\r\n]+", text or "")]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    heading_lines: list[str] = []
    for line in lines[:30]:
        compact = line.strip()
        if len(compact) > 80:
            continue
        if _is_pure_heading(compact) or STRUCTURAL_HEADING_RE.match(compact):
            heading_lines.append(compact)
            continue
        if any(signal in compact for signal in SECTION_PLAN_HEADING_SIGNALS):
            heading_lines.append(compact)

    lead = _clean_requirement_text(" ".join(lines[:8]))
    picked = list(dict.fromkeys([*heading_lines[:8], lead]))
    excerpt = "\n".join(line for line in picked if line)
    return excerpt[:max_chars]


def _page_payload(
    chunks: list[DocumentChunk],
    *,
    max_text_chars: int | None = None,
    max_table_rows: int | None = None,
    max_table_row_chars: int | None = None,
) -> list[dict[str, Any]]:
    page_count = len({_chunk_effective_page_no(chunk) for chunk in chunks})
    default_text_chars, default_table_rows, default_row_chars = _section_plan_limits(page_count)
    text_limit = max_text_chars if max_text_chars is not None else default_text_chars
    table_row_limit = max_table_rows if max_table_rows is not None else default_table_rows
    table_row_char_limit = max_table_row_chars if max_table_row_chars is not None else default_row_chars
    pages: dict[int, dict[str, Any]] = {}
    for chunk in chunks:
        page_no = _chunk_effective_page_no(chunk)
        page = pages.setdefault(
            page_no,
            {
                "page_no": page_no,
                "chunk_indexes": [],
                "headings": [],
                "text": "",
                "table_rows": [],
            },
        )
        page["chunk_indexes"].append(chunk.chunk_index)
        if chunk.heading_path and chunk.heading_path not in page["headings"]:
            page["headings"].append(chunk.heading_path)
        if len(page["text"]) < text_limit:
            remaining = text_limit - len(page["text"])
            excerpt = _section_plan_excerpt(chunk.content_text, max_chars=remaining)
            if excerpt:
                page["text"] = f"{page['text']}\n{excerpt[:remaining]}".strip()[:text_limit]
        for row_text in _table_row_texts(chunk)[: max(1, table_row_limit)]:
            if len(page["table_rows"]) >= table_row_limit:
                break
            clipped_row = row_text[:table_row_char_limit]
            if clipped_row and clipped_row not in page["table_rows"]:
                page["table_rows"].append(clipped_row)
    return [pages[page_no] for page_no in sorted(pages)]


def _section_record_payload(section: DocumentSemanticSection) -> dict[str, Any]:
    return {
        "id": str(section.id),
        "section_index": section.section_index,
        "title": section.title,
        "section_type": section.section_type,
        "start_page": section.start_page,
        "end_page": section.end_page,
        "confidence_score": float(section.confidence_score or 0),
        "evidence": section.evidence,
        "status": section.status,
    }


def _table_row_texts(chunk: DocumentChunk) -> list[str]:
    table_json = chunk.table_json or {}
    rows = table_json.get("rows") if isinstance(table_json, dict) else None
    if not isinstance(rows, list):
        return []

    row_texts: list[str] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        cells = [
            _clean_requirement_text(str(cell))
            for cell in row
            if cell is not None and _clean_requirement_text(str(cell))
        ]
        if not cells:
            continue
        if len(cells) == 1:
            row_texts.append(cells[0])
            continue
        if re.fullmatch(r"\d{1,2}", cells[0]) and len(cells) >= 3:
            row_texts.append(f"{cells[1]}：{'；'.join(cells[2:])}")
            continue
        row_texts.append(f"{cells[0]}：{'；'.join(cells[1:])}")
    return row_texts


def _rule_source_texts(chunk: DocumentChunk) -> list[str]:
    table_rows = _table_row_texts(chunk)
    return table_rows if table_rows else [chunk.content_text]


def _best_table_row_quote(chunk: DocumentChunk, text: str) -> str | None:
    rows = _table_row_texts(chunk)
    if not rows:
        return None

    compact_text = re.sub(r"\s+", "", text)
    tokens = set(re.findall(r"[A-Za-z0-9.]{2,}", compact_text))
    for chinese_part in re.findall(r"[\u4e00-\u9fff]+", compact_text):
        for size in (2, 3, 4):
            tokens.update(
                chinese_part[index : index + size]
                for index in range(0, max(len(chinese_part) - size + 1, 0))
            )

    best_row: str | None = None
    best_score = 0
    for row in rows:
        compact_row = re.sub(r"\s+", "", row)
        score = 0
        if compact_text and compact_text in compact_row:
            score += 100
        score += sum(min(len(token), 4) for token in tokens if token in compact_row)
        if score > best_score:
            best_row = row
            best_score = score
    return best_row if best_row and best_score > 0 else None


def _is_response_form_table(chunk: DocumentChunk) -> bool:
    if not chunk.table_json:
        return False
    text = _clean_requirement_text(chunk.content_text)
    return any(
        signal in text
        for signal in (
            "见响应文件",
            "例如：",
            "单位工程名称 | 建设规模",
            "材料、 设备品种",
            "机械或设备 名称",
            "总部人员 项目主管",
        )
    )


def _relevant_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    table_chunks = [
        chunk
        for chunk in chunks
        if chunk.table_json
        and not _is_response_form_table(chunk)
        and any(
            keyword in f"{chunk.heading_path or ''} {chunk.content_text}"
            for keyword in GENERATION_KEYWORDS
        )
    ]
    if len(table_chunks) >= 3:
        return table_chunks[:80]

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


def _normalize_llm_compliance_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        payload = {"items": payload}
    if not isinstance(payload, dict):
        return {"items": []}
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        for alias in (
            "candidates",
            "requirements",
            "compliance_items",
            "compliance_entries",
            "compliance_matrix",
            "matrix",
            "matrix_items",
            "entries",
            "results",
        ):
            if isinstance(payload.get(alias), list):
                raw_items = payload[alias]
                break
    if not isinstance(raw_items, list):
        section_items: list[Any] = []
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, list):
                continue
            if re.fullmatch(r"section[_-]?\d+", key, flags=re.IGNORECASE) or re.fullmatch(
                r"第[一二三四五六七八九十\d]+[章节部分]?",
                key,
            ):
                section_items.extend(value)
        if section_items:
            raw_items = section_items
    if not isinstance(raw_items, list):
        return payload
    normalized_items: list[dict[str, Any]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            normalized_items.append(raw_item)
            continue
        item = dict(raw_item)
        if "requirement_text" not in item:
            for alias in ("requirement", "requirement_content", "requirement_name", "text", "content"):
                if item.get(alias):
                    item["requirement_text"] = item[alias]
                    break
        if "source_chunk_index" not in item:
            for alias in ("chunk_index", "source_index", "chunk_id"):
                if item.get(alias) is not None:
                    item["source_chunk_index"] = item[alias]
                    break
        if "source_quote" not in item:
            for alias in ("source_excerpt", "quote", "evidence", "source_text"):
                if item.get(alias):
                    item["source_quote"] = item[alias]
                    break
        if "requirement_text" not in item and item.get("source_quote"):
            item["requirement_text"] = item["source_quote"]
        if "normalized_requirement" not in item and item.get("requirement_text"):
            item["normalized_requirement"] = item["requirement_text"]
        normalized_items.append(item)
    return {**payload, "items": normalized_items}


def _normalize_coverage_review_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "blocked", "issues": []}
    raw_issues = payload.get("issues")
    if not isinstance(raw_issues, list):
        return {**payload, "issues": []}
    normalized_issues: list[dict[str, Any]] = []
    for raw_issue in raw_issues:
        if not isinstance(raw_issue, dict):
            continue
        issue = dict(raw_issue)
        if "message" not in issue:
            for alias in ("description", "reason", "detail", "issue"):
                if issue.get(alias):
                    issue["message"] = issue[alias]
                    break
        if "message" not in issue and (issue.get("item") or issue.get("field")):
            issue_type = str(issue.get("type") or issue.get("code") or "coverage_issue")
            issue["message"] = f"{issue_type}: {issue.get('item') or issue.get('field')}"
        if "suggested_requirement" not in issue:
            for alias in ("suggestion", "suggested_text", "requirement", "item", "field"):
                if issue.get(alias):
                    issue["suggested_requirement"] = issue[alias]
                    break
        normalized_issues.append(issue)
    return {**payload, "issues": normalized_issues}


def _quality_issue(
    *,
    code: str,
    message: str,
    severity: str = "high",
    semantic_section: DocumentSemanticSection | None = None,
    page_no: int | None = None,
    source_chunk_index: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if semantic_section is not None:
        issue["section_id"] = str(semantic_section.id)
        issue["section_index"] = semantic_section.section_index
        issue["section_title"] = semantic_section.title
    if page_no is not None:
        issue["page_no"] = page_no
    if source_chunk_index is not None:
        issue["source_chunk_index"] = source_chunk_index
    if extra:
        issue.update(extra)
    return issue


def _write_quality_report(
    db: Session,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
    *,
    status: str,
    issues: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
) -> DocumentExtractionQualityReport:
    report = DocumentExtractionQualityReport(
        tenant_id=task.tenant_id,
        task_id=task.id,
        document_id=document.id,
        document_version_id=version.id,
        section_id=task.section_id,
        status=status,
        issues_json=issues or [],
        summary_json=summary or {},
    )
    db.add(report)
    db.flush()
    return report


def _message_payload_char_count(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content") or "") for message in messages)


def latest_extraction_quality_report(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_version_id: uuid.UUID,
) -> DocumentExtractionQualityReport | None:
    return db.scalar(
        select(DocumentExtractionQualityReport)
        .where(
            DocumentExtractionQualityReport.tenant_id == tenant_id,
            DocumentExtractionQualityReport.document_version_id == document_version_id,
        )
        .order_by(DocumentExtractionQualityReport.created_at.desc())
        .limit(1)
    )


def _validate_section_plan(
    sections: list[LLMDocumentSection],
    chunks: list[DocumentChunk],
) -> list[LLMDocumentSection]:
    if not chunks:
        raise ComplianceGenerationError("文档版本没有解析分块", code="NO_DOCUMENT_CHUNKS")
    page_numbers = sorted({_chunk_effective_page_no(chunk) for chunk in chunks})
    min_page = page_numbers[0]
    max_page = page_numbers[-1]
    ordered = sorted(sections, key=lambda section: (section.start_page, section.end_page, section.section_index))
    if not ordered:
        raise ComplianceQualityGateError(
            "模型未返回有效章节计划",
            code="SECTION_PLAN_EMPTY",
            issues=[
                _quality_issue(
                    code="SECTION_PLAN_EMPTY",
                    message="模型未返回任何章节/语义段。",
                )
            ],
        )

    previous_end = min_page - 1
    normalized: list[LLMDocumentSection] = []
    seen_indexes: set[int] = set()
    for position, section in enumerate(ordered, start=1):
        if section.section_index in seen_indexes:
            raise ComplianceQualityGateError(
                "章节计划存在重复序号",
                code="SECTION_PLAN_DUPLICATE_INDEX",
                issues=[
                    _quality_issue(
                        code="SECTION_PLAN_DUPLICATE_INDEX",
                        message=f"章节序号 {section.section_index} 重复。",
                        page_no=section.start_page,
                    )
                ],
            )
        seen_indexes.add(section.section_index)
        if section.start_page < min_page or section.end_page > max_page:
            raise ComplianceQualityGateError(
                "章节计划页码越界",
                code="SECTION_PLAN_PAGE_OUT_OF_RANGE",
                issues=[
                    _quality_issue(
                        code="SECTION_PLAN_PAGE_OUT_OF_RANGE",
                        message=f"章节“{section.title}”页码 {section.start_page}-{section.end_page} 超出解析页范围 {min_page}-{max_page}。",
                        page_no=section.start_page,
                    )
                ],
            )
        if section.start_page <= previous_end:
            raise ComplianceQualityGateError(
                "章节计划页码重叠",
                code="SECTION_PLAN_OVERLAP",
                issues=[
                    _quality_issue(
                        code="SECTION_PLAN_OVERLAP",
                        message=f"章节“{section.title}”与上一段页码重叠。",
                        page_no=section.start_page,
                    )
                ],
            )
        if section.start_page > previous_end + 1:
            raise ComplianceQualityGateError(
                "章节计划存在断档",
                code="SECTION_PLAN_GAP",
                issues=[
                    _quality_issue(
                        code="SECTION_PLAN_GAP",
                        message=f"章节计划缺少第 {previous_end + 1} 页到第 {section.start_page - 1} 页。",
                        page_no=previous_end + 1,
                    )
                ],
            )
        previous_end = section.end_page
        normalized.append(section.model_copy(update={"section_index": position}))
    if previous_end < max_page:
        raise ComplianceQualityGateError(
            "章节计划末尾存在断档",
            code="SECTION_PLAN_GAP",
            issues=[
                _quality_issue(
                    code="SECTION_PLAN_GAP",
                    message=f"章节计划缺少第 {previous_end + 1} 页到第 {max_page} 页。",
                    page_no=previous_end + 1,
                )
            ],
        )
    return normalized


def _section_size_stats(
    *,
    start_page: int,
    end_page: int,
    chunks: list[DocumentChunk],
) -> tuple[int, int, int]:
    current_chunks = [
        chunk for chunk in chunks if start_page <= _chunk_effective_page_no(chunk) <= end_page
    ]
    return (
        max(0, end_page - start_page + 1),
        len(current_chunks),
        sum(len(chunk.content_text or "") for chunk in current_chunks),
    )


def _section_within_extract_limits(
    *,
    start_page: int,
    end_page: int,
    chunks: list[DocumentChunk],
) -> bool:
    page_count, chunk_count, char_count = _section_size_stats(
        start_page=start_page,
        end_page=end_page,
        chunks=chunks,
    )
    return (
        page_count <= SECTION_EXTRACT_MAX_PAGES
        and chunk_count <= SECTION_EXTRACT_MAX_CHUNKS
        and char_count <= SECTION_EXTRACT_MAX_CHARS
    )


def _stored_section_plan_has_oversized_section(
    sections: list[DocumentSemanticSection],
    chunks: list[DocumentChunk],
) -> bool:
    return any(
        not _section_within_extract_limits(
            start_page=section.start_page,
            end_page=section.end_page,
            chunks=chunks,
        )
        for section in sections
    )


def _split_large_section_plan(
    sections: list[LLMDocumentSection],
    chunks: list[DocumentChunk],
) -> list[LLMDocumentSection]:
    chunks_by_page: dict[int, list[DocumentChunk]] = {}
    for chunk in chunks:
        chunks_by_page.setdefault(_chunk_effective_page_no(chunk), []).append(chunk)

    split_sections: list[LLMDocumentSection] = []
    for section in sections:
        if _section_within_extract_limits(
            start_page=section.start_page,
            end_page=section.end_page,
            chunks=chunks,
        ):
            split_sections.append(section)
            continue

        ranges: list[tuple[int, int]] = []
        current_start: int | None = None
        current_end: int | None = None
        current_chunk_count = 0
        current_char_count = 0
        for page_no in range(section.start_page, section.end_page + 1):
            page_chunks = chunks_by_page.get(page_no, [])
            page_char_count = sum(len(chunk.content_text or "") for chunk in page_chunks)
            would_exceed = current_start is not None and (
                page_no - current_start + 1 > SECTION_EXTRACT_MAX_PAGES
                or current_chunk_count + len(page_chunks) > SECTION_EXTRACT_MAX_CHUNKS
                or current_char_count + page_char_count > SECTION_EXTRACT_MAX_CHARS
            )
            if would_exceed:
                ranges.append((current_start, current_end or page_no - 1))
                current_start = page_no
                current_chunk_count = len(page_chunks)
                current_char_count = page_char_count
            else:
                current_start = page_no if current_start is None else current_start
                current_chunk_count += len(page_chunks)
                current_char_count += page_char_count
            current_end = page_no

        if current_start is not None and current_end is not None:
            ranges.append((current_start, current_end))

        for offset, (start_page, end_page) in enumerate(ranges, start=1):
            title = section.title if len(ranges) == 1 else f"{section.title}（{offset}）"
            evidence_parts = [section.evidence.strip()] if section.evidence else []
            evidence_parts.append("长章节按页码拆分，控制单段抽取上下文。")
            split_sections.append(
                section.model_copy(
                    update={
                        "title": title,
                        "start_page": start_page,
                        "end_page": end_page,
                        "evidence": "；".join(evidence_parts),
                    }
                )
            )

    return [
        section.model_copy(update={"section_index": index})
        for index, section in enumerate(split_sections, start=1)
    ]


def ensure_document_section_plan(
    db: Session,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
    *,
    force: bool = False,
) -> list[DocumentSemanticSection]:
    existing = list(
        db.scalars(
            select(DocumentSemanticSection)
            .where(
                DocumentSemanticSection.tenant_id == task.tenant_id,
                DocumentSemanticSection.document_version_id == version.id,
            )
            .order_by(DocumentSemanticSection.section_index)
        ).all()
    )
    existing_plan_reusable = bool(existing) and not _stored_section_plan_has_oversized_section(
        existing,
        chunks,
    )
    if existing_plan_reusable and not force:
        return existing

    prompt = get_prompt("document_section_plan", "1.1.0")
    pages = _page_payload(chunks)
    messages = prompt.render(pages_json=json.dumps(pages, ensure_ascii=False))
    payload_char_count = _message_payload_char_count(messages)
    result = None
    try:
        result = chat_completion(
            db,
            tenant_id=task.tenant_id,
            project_id=task.project_id,
            section_id=task.section_id,
            actor_user_id=task.created_by,
            actor_type="worker",
            task_type="document_section_plan",
            prompt_version=prompt.prompt_version,
            messages=messages,
            complexity="complex" if len(pages) >= 20 else "simple",
            temperature=0.0,
            response_format={"type": "json_object"},
            timeout_seconds=180.0 if len(pages) >= 20 else None,
            evidence_refs={
                "document_version_ids": [str(version.id)],
                "page_numbers": [page["page_no"] for page in pages],
                "chunk_indexes": [chunk.chunk_index for chunk in chunks],
                "payload_char_count": payload_char_count,
            },
        )
        plan = LLMDocumentSectionPlan.model_validate(_json_from_model_text(result.content))
    except (LLMGatewayError, json.JSONDecodeError, ValidationError) as exc:
        if isinstance(exc, LLMGatewayError):
            timed_out = "timed out" in str(exc).lower() or "timeout" in str(exc).lower()
            failure_message = "章节规划模型调用超时。" if timed_out else "章节规划模型调用失败。"
            error_code = exc.code
            model_invocation_log_id = str(exc.log_id) if exc.log_id else None
        elif isinstance(exc, ValidationError):
            failure_message = "章节规划模型返回结构不符合要求。"
            error_code = "LLM_SCHEMA_VALIDATION_FAILED"
            model_invocation_log_id = str(result.log_id) if result and result.log_id else None
        else:
            failure_message = "章节规划模型返回内容不是有效 JSON。"
            error_code = "LLM_JSON_PARSE_FAILED"
            model_invocation_log_id = str(result.log_id) if result and result.log_id else None

        if existing_plan_reusable:
            _update_matrix_task_progress(
                db,
                task,
                progress=21,
                stage="document_section_plan_reused",
                message=(
                    f"{failure_message}已复用上一版 {len(existing)} 个语义段继续生成，"
                    "无需用户手动处理。"
                ),
                extra={
                    "section_count": len(existing),
                    "fallback_from_stage": "document_section_plan",
                    "fallback_reason": error_code,
                    "model_invocation_log_id": model_invocation_log_id,
                    "page_count": len(pages),
                    "chunk_count": len(chunks),
                    "payload_char_count": payload_char_count,
                },
            )
            return existing

        raise ComplianceQualityGateError(
            f"{failure_message}{str(exc)}",
            code=error_code,
            issues=[
                _quality_issue(
                    code=error_code,
                    message=(
                        f"{failure_message}请稍后重试；若持续失败，需要继续压缩规划输入或调高模型读取超时。"
                    ),
                    severity="high",
                    extra={
                        "stage": "document_section_plan",
                        "model_invocation_log_id": model_invocation_log_id,
                        "page_count": len(pages),
                        "chunk_count": len(chunks),
                        "payload_char_count": payload_char_count,
                    },
                )
            ],
            summary={
                "document_id": str(document.id),
                "document_version_id": str(version.id),
                "stage": "document_section_plan",
                "page_count": len(pages),
                "chunk_count": len(chunks),
                "payload_char_count": payload_char_count,
            },
        ) from exc

    planned_sections = _split_large_section_plan(_validate_section_plan(plan.sections, chunks), chunks)

    if existing:
        db.execute(
            delete(DocumentSemanticSection).where(
                DocumentSemanticSection.tenant_id == task.tenant_id,
                DocumentSemanticSection.document_version_id == version.id,
            )
        )
        db.flush()

    stored: list[DocumentSemanticSection] = []
    for section in planned_sections:
        status = "low_confidence" if section.confidence_score < 0.6 else "planned"
        record = DocumentSemanticSection(
            tenant_id=task.tenant_id,
            document_id=document.id,
            document_version_id=version.id,
            section_id=task.section_id,
            section_index=section.section_index,
            title=section.title[:300],
            section_type=section.section_type,
            start_page=section.start_page,
            end_page=section.end_page,
            confidence_score=_confidence(section.confidence_score),
            evidence=section.evidence[:1000] if section.evidence else None,
            status=status,
            model_invocation_log_id=result.log_id,
            raw_json=section.model_dump(),
        )
        db.add(record)
        stored.append(record)
    db.flush()
    return stored


def _llm_prompt(chunks: list[DocumentChunk]) -> list[dict[str, str]]:
    payload = json.dumps(_chunk_payload(chunks), ensure_ascii=False)
    return get_prompt("compliance_extract", "1.1.0").render(chunks_json=payload)


def _source_quote(item: LLMComplianceItem, source_chunk: DocumentChunk, cleaned_text: str) -> str:
    row_quote = _best_table_row_quote(source_chunk, cleaned_text)
    if row_quote:
        return row_quote[:300]
    quote = _clean_requirement_text(item.source_quote or "")
    if quote and quote in source_chunk.content_text:
        return quote[:300]
    if cleaned_text in source_chunk.content_text:
        return cleaned_text[:300]
    return _clean_requirement_text(source_chunk.content_text)[:300]


def _compact_for_match(text: str) -> str:
    return re.sub(r"\s+", "", _clean_requirement_text(text))


def _compact_for_source_match(text: str) -> str:
    text = text.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    compact = re.sub(r"[\s|:：☑√✓□\\\"'“”‘’\x80-\x9f\ue000-\uf8ff]+", "", _clean_requirement_text(text))
    return compact.replace("其受委托", "受其委托")


def _compact_preserving_check_marks(text: str) -> str:
    text = text.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ").replace("\xa0", " ")
    text = PDF_NOISE_TOKEN_RE.sub(" ", text)
    text = PAGE_FOOTER_RE.sub(" ", text)
    return re.sub(r"[\s|:：\\\"'“”‘’\x80-\x9f\ue000-\uf8ff]+", "", text)


def _drop_short_parenthetical(text: str) -> str:
    previous = None
    cleaned = text
    while cleaned != previous:
        previous = cleaned
        cleaned = re.sub(r"[(（][^()（）]{1,80}[)）]", "", cleaned)
    return cleaned


def _drop_soft_punctuation(text: str) -> str:
    return re.sub(r"[，,。；;]+", "", text)


def _drop_terminal_soft_punctuation(text: str) -> str:
    return re.sub(r"[.。．]+$", "", text)


def _drop_optional_chinese_particles(text: str) -> str:
    return re.sub(r"[的为是]", "", text)


def _drop_optional_source_labels(text: str) -> str:
    return text.replace("约定", "")


def _drop_carried_subject_prefix(text: str) -> str:
    return re.sub(r"^(?:承包人|发包人|潜在承包人|投标人|供应商)", "", text)


def _field_value_reordered_match(compact_source: str, compact_quote: str) -> bool:
    for value in ("不允许", "不接受", "不收取", "允许", "接受", "无", "否", "是"):
        if compact_quote.startswith(value):
            field = compact_quote.removeprefix(value)
            if len(field) >= 4 and value in compact_source and field in compact_source:
                return True
        if compact_quote.endswith(value):
            field = compact_quote.removesuffix(value)
            if len(field) >= 4 and value in compact_source and field in compact_source:
                return True
    return False


def _cost_rate_label_match(compact_source: str, compact_quote: str) -> bool:
    match = re.fullmatch(
        r"(单独装饰工程|安装工程|市政工程|景观绿化工程)(规费|企业管理费)不得低于(\d+(?:\.\d+)?%)",
        compact_quote,
    )
    if not match:
        return False
    subject, label, rate = match.groups()
    return label in compact_source and f"{subject}不得低于{rate}" in compact_source


def _carried_short_intro_match(compact_source: str, compact_quote: str) -> bool:
    searchable_source = _drop_soft_punctuation(compact_source)
    searchable_quote = _drop_soft_punctuation(compact_quote)
    for intro in ("列入",):
        if not searchable_quote.startswith(intro):
            continue
        tail = searchable_quote.removeprefix(intro)
        if len(tail) < 5:
            continue
        intro_index = searchable_source.find(intro)
        if intro_index < 0:
            continue
        tail_index = searchable_source.find(tail, intro_index + len(intro))
        if tail_index >= 0 and tail_index - intro_index <= 80:
            return True
    return False


def _is_checked_field_option_quote(quote: str) -> bool:
    return bool(re.search(r"(?:[:：|]|\.{2,}|…{1,2}).*[☑√✓]", quote))


def _checked_ellipsis_option_match(source: str, quote: str) -> bool:
    if not _is_checked_field_option_quote(quote):
        return False
    fragments = [
        fragment
        for fragment in re.split(r"(?:[:：|]|\.{2,}|…{1,2})", quote)
        if _compact_for_source_match(fragment)
    ]
    if len(fragments) < 2:
        return False
    label = _drop_soft_punctuation(_compact_for_source_match(fragments[0]))
    if len(label) < 4:
        return False
    tail = " ".join(fragments[-1].replace("\xa0", " ").split()).strip()
    selected_match = re.search(r"[☑√✓]\s*([^□☐☑√✓，,。；;\s]+)", tail)
    if not selected_match:
        return False
    selected_value = _drop_soft_punctuation(_compact_for_source_match(selected_match.group(1)))
    if not 1 <= len(selected_value) <= 8:
        return False

    source_with_marks = _drop_soft_punctuation(_compact_preserving_check_marks(source))
    label_index = _drop_soft_punctuation(_compact_for_source_match(source)).find(label)
    if label_index < 0:
        return False
    return any(
        f"{marker}{selected_value}" in source_with_marks[label_index + len(label) :]
        for marker in ("☑", "√", "✓")
    )


def _selected_numbered_option_match(compact_source: str, compact_quote: str) -> bool:
    marker_match = re.search(r"第[（(]?([0-9一二三四五六七八九十]+)[)）]?种方式", compact_quote)
    if not marker_match:
        return False
    prefix = compact_quote[: marker_match.end()]
    tail = compact_quote[marker_match.end() :]
    if len(prefix) < 8 or len(tail) < 6:
        return False
    prefix_index = compact_source.find(prefix)
    if prefix_index >= 0 and tail in compact_source[prefix_index + len(prefix) :]:
        return True

    searchable_source = _drop_soft_punctuation(compact_source)
    prefix_fragments = [
        _drop_soft_punctuation(fragment)
        for fragment in re.split(r"[，,。；;]+", prefix)
        if len(_drop_soft_punctuation(fragment)) >= 4
    ]
    searchable_tail = _drop_soft_punctuation(tail)
    if not prefix_fragments or len(searchable_tail) < 6:
        return False
    cursor = 0
    for fragment in prefix_fragments:
        index = searchable_source.find(fragment, cursor)
        if index < 0:
            return False
        cursor = index + len(fragment)
    return searchable_tail in searchable_source[cursor:]


def _source_insertion_fuzzy_match(compact_source: str, compact_quote: str) -> bool:
    searchable_source = _drop_soft_punctuation(compact_source)
    searchable_quote = _drop_soft_punctuation(compact_quote)
    if len(searchable_quote) < 30:
        return False
    match = SequenceMatcher(None, searchable_quote, searchable_source, autojunk=False).find_longest_match(
        0,
        len(searchable_quote),
        0,
        len(searchable_source),
    )
    if match.size < 18:
        return False
    before = searchable_quote[: match.a]
    after = searchable_quote[match.a + match.size :]
    before_ok = not before or (
        len(before) >= 6 and before in searchable_source[: match.b]
    )
    after_ok = not after or (
        len(after) >= 6 and after in searchable_source[match.b + match.size :]
    )
    return before_ok and after_ok


def _short_source_insertion_match(compact_source: str, compact_quote: str) -> bool:
    searchable_source = _drop_soft_punctuation(compact_source)
    searchable_quote = _drop_soft_punctuation(compact_quote)
    if len(searchable_quote) < 12:
        return False
    for split_at in range(min(len(searchable_quote) - 3, 18), 7, -1):
        prefix = searchable_quote[:split_at]
        tail = searchable_quote[split_at:]
        if len(tail) < 3:
            continue
        prefix_index = searchable_source.find(prefix)
        if prefix_index < 0:
            continue
        tail_index = searchable_source.find(tail, prefix_index + len(prefix))
        if tail_index >= 0 and tail_index - prefix_index <= len(searchable_quote) + 40:
            return True
    return False


def _trailing_context_intro_match(compact_source: str, compact_quote: str) -> bool:
    searchable_source = _drop_soft_punctuation(compact_source)
    searchable_quote = _drop_soft_punctuation(compact_quote)
    for context in ("发包人有权单方解除合同", "作废标处理"):
        if not searchable_quote.endswith(context):
            continue
        requirement = searchable_quote.removesuffix(context)
        if len(requirement) < 8:
            continue
        context_index = searchable_source.find(context)
        requirement_index = searchable_source.find(requirement)
        if context_index >= 0 and requirement_index >= 0:
            return True
    return False


def _party_alternative_variants(compact_source: str) -> set[str]:
    return {
        compact_source,
        compact_source.replace("／承包人", "").replace("/承包人", ""),
        compact_source.replace("发包人／", "").replace("发包人/", ""),
    }


def _source_quote_fuzzy_matches(compact_source: str, compact_quote: str) -> bool:
    if not compact_source:
        return False
    compact_source_without_soft_punctuation = _drop_soft_punctuation(compact_source)
    ellipsis_fragments = [
        _drop_soft_punctuation(fragment)
        for fragment in re.split(r"(?:\.{2,}|…{1,2})", compact_quote)
        if len(_drop_soft_punctuation(fragment)) >= 6
    ]
    raw_ellipsis_fragments = [
        _drop_soft_punctuation(fragment)
        for fragment in re.split(r"(?:\.{2,}|…{1,2})", compact_quote)
        if _drop_soft_punctuation(fragment)
    ]
    if len(raw_ellipsis_fragments) >= 2:
        first_fragment = raw_ellipsis_fragments[0]
        last_fragment = raw_ellipsis_fragments[-1]
        if len(first_fragment) >= 8 and len(last_fragment) >= 3:
            first_index = compact_source_without_soft_punctuation.find(first_fragment)
            if first_index >= 0:
                last_index = compact_source_without_soft_punctuation.find(
                    last_fragment,
                    first_index + len(first_fragment),
                )
                if last_index >= 0:
                    return True
    if len(ellipsis_fragments) >= 2:
        cursor = 0
        matched_all = True
        for fragment in ellipsis_fragments:
            index = compact_source_without_soft_punctuation.find(fragment, cursor)
            if index < 0:
                matched_all = False
                break
            cursor = index + len(fragment)
        if matched_all:
            return True
    fragments = [
        fragment
        for fragment in re.split(r"[，,。；;]+|(?=[(（]\d+[)）])", compact_quote)
        if len(fragment) >= 6
    ]
    if len(fragments) >= 2 and sum(len(fragment) for fragment in fragments) >= 12:
        cursor = 0
        matched_all = True
        for fragment in fragments:
            index = compact_source.find(fragment, cursor)
            if index < 0:
                matched_all = False
                break
            cursor = index + len(fragment)
        if matched_all:
            return True
    compact_quote_without_soft_punctuation = _drop_soft_punctuation(compact_quote)
    if (
        len(compact_quote_without_soft_punctuation) >= 160
        and compact_quote_without_soft_punctuation[:120] in compact_source_without_soft_punctuation
    ):
        return True
    if len(compact_quote) < 12:
        return False
    if len(compact_quote) < 20:
        match = SequenceMatcher(None, compact_quote, compact_source, autojunk=False).find_longest_match(
            0,
            len(compact_quote),
            0,
            len(compact_source),
        )
        return match.size >= max(10, int(len(compact_quote) * 0.60)) and compact_quote[-4:] in compact_source
    if len(compact_quote) < 40:
        match = SequenceMatcher(None, compact_quote, compact_source, autojunk=False).find_longest_match(
            0,
            len(compact_quote),
            0,
            len(compact_source),
        )
        return match.size >= max(16, int(len(compact_quote) * 0.65)) and compact_quote[-4:] in compact_source
    match = SequenceMatcher(None, compact_quote, compact_source, autojunk=False).find_longest_match(
        0,
        len(compact_quote),
        0,
        len(compact_source),
    )
    return match.size >= max(32, int(len(compact_quote) * 0.42)) or _source_insertion_fuzzy_match(
        compact_source,
        compact_quote,
    )


def _source_texts_match_quote(sources: list[str], quote: str) -> bool:
    compact_quote = _compact_for_source_match(quote)
    if not compact_quote:
        return False
    checked_field_option_quote = _is_checked_field_option_quote(quote)
    colon_fragments = [
        _compact_for_source_match(fragment)
        for fragment in re.split(r"[:：|]", quote)
        if _compact_for_source_match(fragment)
    ]
    for source in sources:
        if _checked_ellipsis_option_match(source, quote):
            return True
        compact_source_base = _compact_for_source_match(source)
        if checked_field_option_quote:
            compact_source_with_marks = _compact_preserving_check_marks(source)
            compact_quote_with_marks = _compact_preserving_check_marks(quote)
            if compact_quote_with_marks and compact_quote_with_marks in compact_source_with_marks:
                return True
            continue
        for compact_source in _party_alternative_variants(compact_source_base):
            compact_source_without_parenthetical = _drop_short_parenthetical(compact_source)
            compact_quote_without_parenthetical = _drop_short_parenthetical(compact_quote)
            compact_source_without_soft_punctuation = _drop_soft_punctuation(compact_source)
            compact_quote_without_soft_punctuation = _drop_soft_punctuation(compact_quote)
            compact_source_without_terminal_punctuation = _drop_terminal_soft_punctuation(compact_source)
            compact_quote_without_terminal_punctuation = _drop_terminal_soft_punctuation(compact_quote)
            compact_source_without_parenthetical_soft_punctuation = _drop_soft_punctuation(
                compact_source_without_parenthetical
            )
            compact_quote_without_parenthetical_soft_punctuation = _drop_soft_punctuation(
                compact_quote_without_parenthetical
            )
            compact_quote_without_carried_subject = _drop_carried_subject_prefix(compact_quote)
            compact_source_without_particles = _drop_optional_chinese_particles(
                compact_source_without_soft_punctuation
            )
            compact_quote_without_particles = _drop_optional_chinese_particles(
                compact_quote_without_soft_punctuation
            )
            compact_source_without_labels = _drop_optional_source_labels(
                compact_source_without_soft_punctuation
            )
            compact_quote_without_labels = _drop_optional_source_labels(
                compact_quote_without_soft_punctuation
            )
            colon_fragments_match = False
            if len(colon_fragments) >= 2 and len(colon_fragments[0]) >= 4:
                cursor = 0
                colon_fragments_match = True
                for fragment in colon_fragments:
                    index = compact_source.find(fragment, cursor)
                    if index < 0:
                        colon_fragments_match = False
                        break
                    cursor = index + len(fragment)
            if (
                compact_quote in compact_source
                or compact_quote_without_terminal_punctuation
                in compact_source_without_terminal_punctuation
                or compact_quote_without_soft_punctuation in compact_source_without_soft_punctuation
                or compact_quote_without_parenthetical_soft_punctuation
                in compact_source_without_parenthetical_soft_punctuation
                or (
                    len(compact_quote_without_carried_subject) >= 8
                    and compact_quote_without_carried_subject in compact_source
                )
                or compact_quote_without_particles in compact_source_without_particles
                or compact_quote_without_labels in compact_source_without_labels
                or compact_quote in compact_source_without_parenthetical
                or compact_quote_without_parenthetical in compact_source
                or colon_fragments_match
                or _field_value_reordered_match(compact_source, compact_quote)
                or _cost_rate_label_match(compact_source, compact_quote)
                or _carried_short_intro_match(compact_source, compact_quote)
                or _selected_numbered_option_match(compact_source, compact_quote)
                or _trailing_context_intro_match(compact_source, compact_quote)
                or _short_source_insertion_match(compact_source, compact_quote)
                or _source_quote_fuzzy_matches(compact_source, compact_quote)
                or _source_quote_fuzzy_matches(
                    compact_source_without_parenthetical,
                    compact_quote_without_parenthetical,
                )
            ):
                return True
    return False


def _source_quote_matches(source_chunk: DocumentChunk, quote: str) -> bool:
    return _source_texts_match_quote([source_chunk.content_text, *(_table_row_texts(source_chunk))], quote)


def _source_quote_matches_adjacent_chunk_window(
    chunks: list[DocumentChunk],
    source_chunk: DocumentChunk,
    quote: str,
) -> bool:
    ordered_chunks = sorted(chunks, key=lambda chunk: chunk.chunk_index)
    try:
        position = ordered_chunks.index(source_chunk)
    except ValueError:
        return False

    windows: list[list[DocumentChunk]] = []
    if position > 0:
        windows.append([ordered_chunks[position - 1], source_chunk])
    if position < len(ordered_chunks) - 1:
        windows.append([source_chunk, ordered_chunks[position + 1]])
    if 0 < position < len(ordered_chunks) - 1:
        windows.append([ordered_chunks[position - 1], source_chunk, ordered_chunks[position + 1]])
    if position > 1:
        windows.append([ordered_chunks[position - 2], ordered_chunks[position - 1], source_chunk])
    if position < len(ordered_chunks) - 2:
        windows.append([source_chunk, ordered_chunks[position + 1], ordered_chunks[position + 2]])
    if 0 < position < len(ordered_chunks) - 2:
        windows.append(
            [
                ordered_chunks[position - 1],
                source_chunk,
                ordered_chunks[position + 1],
                ordered_chunks[position + 2],
            ]
        )
    if 1 < position < len(ordered_chunks) - 1:
        windows.append(
            [
                ordered_chunks[position - 2],
                ordered_chunks[position - 1],
                source_chunk,
                ordered_chunks[position + 1],
            ]
        )

    for window in windows:
        sources = ["\n".join(chunk.content_text for chunk in window)]
        for chunk in window:
            sources.extend(_table_row_texts(chunk))
        if _source_texts_match_quote(sources, quote):
            return True
    return False


def _source_quote_text_variants(quote: str) -> list[tuple[str, dict[str, str]]]:
    variants: list[tuple[str, dict[str, str]]] = [(quote, {})]
    replacements = (
        ("专用条款", "通用条款"),
        ("通用条款", "专用条款"),
        (
            "文明施工、环境保护、安全施工、临时设施费四项费用",
            "文明施工费、环境保护费、安全施工费和临时设施费四项费用",
        ),
        (
            "风险控制价：最高投标限价",
            "风险控制价：为防止投标人恶意低价竞标，最高投标限价",
        ),
        (
            "或者合同签订日期，结束时间为验收合格或合同解除日期",
            "或者不通过招标方式的则以合同签订日期为开始时间，结束时间为该合同工程验收合格或合同解除日期",
        ),
        (
            "不能满足竞标文件要求的保修期",
            "不能满足竞标文件要求的工程验收、施工工期、保修期",
        ),
        (
            "无法导入成功的响应文件",
            "电子响应文件无法解密或解密后无法正确读取的，或无法导入成功的",
        ),
        (
            "签订合同后 7天内，承包人提交项目管理机构及施工现场管理人员安排报告，并对相应人员的到位率作出承诺",
            "承包人提交项目管理机构及施工现场管理人员安排报告的期限：签订合同后 7天内，并对相应人员的到位率作出承诺",
        ),
        (
            "不得低于投标时的资质",
            "不得低于投标时的职称、资质",
        ),
        (
            "文明施工按杭州市人民政府令第278号文《杭州市建设工程文明施工管理规定》执行",
            "文明施工按杭州市人民政府令第278号文《杭州市建设工程文明施工管理规定》、及文明工地杭建监总[2011]21号《关于打造“文明工地”创建全国文明城市活动实施方案》执行",
        ),
    )
    for old, new in replacements:
        if old in quote:
            variants.append((quote.replace(old, new), {old: new}))
    if "重新传输递交" in quote:
        variants.append((quote.replace("重新传输递交", "重新传输递"), {}))
    for marker in ("...", "…"):
        old = f"风险控制价：{marker}最高投标限价"
        if old in quote:
            new = "风险控制价：为防止投标人恶意低价竞标，最高投标限价"
            variants.append((quote.replace(old, new), {old: new}))
    deduct_score_match = re.search(r"扣(\d+(?:\.\d+)?)分", quote)
    if deduct_score_match:
        old = deduct_score_match.group(0)
        new = f"扣分{deduct_score_match.group(1)}分"
        variants.append((quote.replace(old, new), {old: new}))
    return variants


def _align_text_with_source_quote_variant(text: str, replacements: dict[str, str]) -> str:
    aligned = text
    for old, new in replacements.items():
        aligned = aligned.replace(old, new)
    return aligned


def _unique_chunk_matching_quote(
    chunks: list[DocumentChunk],
    quote: str,
) -> DocumentChunk | None:
    matches = [chunk for chunk in chunks if _source_quote_matches(chunk, quote)]
    if len(matches) == 1:
        return matches[0]
    return None


def _best_chunk_matching_quote(
    chunks: list[DocumentChunk],
    quote: str,
    *,
    preferred_chunk_index: int,
) -> DocumentChunk | None:
    matches = [chunk for chunk in chunks if _source_quote_matches(chunk, quote)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None
    ranked = sorted(matches, key=lambda chunk: abs(chunk.chunk_index - preferred_chunk_index))
    if len(ranked) >= 2 and abs(ranked[0].chunk_index - preferred_chunk_index) == abs(
        ranked[1].chunk_index - preferred_chunk_index
    ):
        return None
    return ranked[0]


def _best_chunk_matching_quote_window(
    chunks: list[DocumentChunk],
    quote: str,
    *,
    preferred_chunk_index: int,
) -> DocumentChunk | None:
    direct_match = _best_chunk_matching_quote(
        chunks,
        quote,
        preferred_chunk_index=preferred_chunk_index,
    )
    if direct_match is not None:
        return direct_match

    window_matches = [
        chunk for chunk in chunks if _source_quote_matches_adjacent_chunk_window(chunks, chunk, quote)
    ]
    if not window_matches:
        return None
    ranked = sorted(window_matches, key=lambda chunk: abs(chunk.chunk_index - preferred_chunk_index))
    if len(ranked) >= 2 and abs(ranked[0].chunk_index - preferred_chunk_index) == abs(
        ranked[1].chunk_index - preferred_chunk_index
    ):
        return None
    return ranked[0]


def _contextualized_llm_requirement_text(source_chunk: DocumentChunk, cleaned_text: str) -> str:
    row_quote = _best_table_row_quote(source_chunk, cleaned_text)
    if not row_quote or "：" not in row_quote:
        return _contextual_requirement_text(cleaned_text, source_chunk.heading_path)
    label, _value = row_quote.split("：", 1)
    label = _clean_requirement_text(label)
    if not label or label in cleaned_text or len(label) > 40:
        return _contextual_requirement_text(cleaned_text, source_chunk.heading_path)
    if not any(
        signal in label
        for signal in (
            "发包范围",
            "招标范围",
            "承包方式",
            "交易方式",
            "评审办法",
            "最高",
            "限价",
            "工期",
            "服务期限",
            "资质要求",
            "资格要求",
            "联合体",
            "类似工程业绩",
        )
    ):
        return _contextual_requirement_text(cleaned_text, source_chunk.heading_path)
    value = "不允许。" if "联合体" in label and "不允许" in cleaned_text else cleaned_text
    return f"{label}：{value}"


def _candidate_is_mandatory(item_type: str, risk_level: str, text: str, preferred: bool | None = None) -> bool:
    if "类似工程业绩要求" in text and "不要求" in text:
        return False
    if preferred is not None:
        return bool(preferred)
    return risk_level == "high" or item_type in {"qualification", "deadline"}


def _section_chunks(
    semantic_section: DocumentSemanticSection,
    chunks: list[DocumentChunk],
) -> list[DocumentChunk]:
    return [
        chunk
        for chunk in chunks
        if semantic_section.start_page <= _chunk_effective_page_no(chunk) <= semantic_section.end_page
    ]


def _section_chunk_payload(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for chunk in chunks:
        payload.append(
            {
                "chunk_index": chunk.chunk_index,
                "page_no": _chunk_effective_page_no(chunk),
                "heading_path": chunk.heading_path,
                "text": chunk.content_text,
                "table_rows": _table_row_texts(chunk),
            }
        )
    return payload


def _call_section_llm(
    db: Session,
    task: AsyncTask,
    semantic_section: DocumentSemanticSection,
    chunks: list[DocumentChunk],
) -> tuple[str, list[ComplianceCandidate]]:
    prompt = get_prompt("compliance_extract_by_section", "1.1.0")
    messages = prompt.render(
        section_json=json.dumps(_section_record_payload(semantic_section), ensure_ascii=False),
        chunks_json=json.dumps(_section_chunk_payload(chunks), ensure_ascii=False),
    )
    char_count = sum(len(chunk.content_text or "") for chunk in chunks)
    result = chat_completion(
        db,
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        section_id=task.section_id,
        actor_user_id=task.created_by,
        actor_type="worker",
        task_type="section_compliance_extract",
        prompt_version=prompt.prompt_version,
        messages=messages,
        complexity="complex" if len(chunks) >= 20 or char_count >= 8000 else "simple",
        temperature=0.0,
        response_format={"type": "json_object"},
        timeout_seconds=180.0,
        evidence_refs={
            "semantic_section_id": str(semantic_section.id),
            "document_version_ids": sorted({str(chunk.document_version_id) for chunk in chunks}),
            "chunk_ids": [str(chunk.id) for chunk in chunks],
            "chunk_indexes": [chunk.chunk_index for chunk in chunks],
            "page_range": [semantic_section.start_page, semantic_section.end_page],
        },
    )
    parsed = LLMComplianceResponse.model_validate(
        _normalize_llm_compliance_payload(_json_from_model_text(result.content))
    )
    chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    candidates: list[ComplianceCandidate] = []
    for item in parsed.items:
        cleaned_text = _clean_requirement_text(item.requirement_text)
        if not cleaned_text:
            continue
        source_chunk = chunk_by_index.get(item.source_chunk_index)
        if source_chunk is None:
            raise ComplianceQualityGateError(
                "模型输出引用了不存在的解析 chunk",
                code="SOURCE_CHUNK_NOT_FOUND",
                issues=[
                    _quality_issue(
                        code="SOURCE_CHUNK_NOT_FOUND",
                        message=f"条目“{cleaned_text[:80]}”引用的 chunk_index={item.source_chunk_index} 不在当前语义段内。",
                        severity="high",
                        semantic_section=semantic_section,
                        source_chunk_index=item.source_chunk_index,
                    )
                ],
                summary={"semantic_section_id": str(semantic_section.id)},
            )
        if _should_skip_rule_text(cleaned_text, source_chunk.heading_path):
            continue
        if _is_contact_text(cleaned_text, source_chunk.heading_path):
            continue
        cleaned_text = _contextualized_llm_requirement_text(source_chunk, cleaned_text)
        if _should_skip_rule_text(cleaned_text, source_chunk.heading_path):
            continue
        rule_type = _rule_item_type(cleaned_text, source_chunk.heading_path)
        item_type = item.item_type
        risk_level = item.risk_level
        if item_type in {"reference_info", "other"} and rule_type != "reference_info":
            item_type = rule_type
            risk_level = _risk_level(item_type, cleaned_text)
        rule_risk = _risk_level(item_type, cleaned_text)
        if rule_risk == "high" and item_type in {"qualification", "deadline", "mandatory_response", "technical_response"}:
            risk_level = "high"
        source_quote = _clean_requirement_text(item.source_quote or "")
        source_chunk_was_corrected = False
        source_quote_spans_adjacent_chunks = False
        source_quote_text_was_aligned = False
        if source_quote and not _source_quote_matches(source_chunk, source_quote):
            for source_quote_variant, replacements in _source_quote_text_variants(source_quote)[1:]:
                if _source_quote_matches(source_chunk, source_quote_variant) or _source_quote_matches_adjacent_chunk_window(
                    chunks,
                    source_chunk,
                    source_quote_variant,
                ):
                    source_quote = source_quote_variant
                    cleaned_text = _align_text_with_source_quote_variant(cleaned_text, replacements)
                    source_quote_text_was_aligned = True
                    break
        if not _source_quote_matches(source_chunk, source_quote):
            if _source_quote_matches_adjacent_chunk_window(chunks, source_chunk, source_quote):
                source_quote_spans_adjacent_chunks = True
            else:
                corrected_source_chunk = _best_chunk_matching_quote_window(
                    chunks,
                    source_quote,
                    preferred_chunk_index=item.source_chunk_index,
                )
                if corrected_source_chunk is not None:
                    source_chunk = corrected_source_chunk
                    source_chunk_was_corrected = True
                    cleaned_text = _contextualized_llm_requirement_text(source_chunk, cleaned_text)
                    rule_type = _rule_item_type(cleaned_text, source_chunk.heading_path)
                    if item_type in {"reference_info", "other"} and rule_type != "reference_info":
                        item_type = rule_type
                        risk_level = _risk_level(item_type, cleaned_text)
                    rule_risk = _risk_level(item_type, cleaned_text)
                    if rule_risk == "high" and item_type in {
                        "qualification",
                        "deadline",
                        "mandatory_response",
                        "technical_response",
                    }:
                        risk_level = "high"
        if not _source_quote_matches(source_chunk, source_quote) and not _source_quote_matches_adjacent_chunk_window(
            chunks,
            source_chunk,
            source_quote,
        ):
            raise ComplianceQualityGateError(
                "模型输出 source_quote 无法回链到解析文本",
                code="SOURCE_QUOTE_NOT_FOUND",
                issues=[
                    _quality_issue(
                        code="SOURCE_QUOTE_NOT_FOUND",
                        message=f"条目“{cleaned_text[:80]}”的 source_quote 无法在 chunk {item.source_chunk_index} 文本或表格行中找到。",
                        severity="high",
                        semantic_section=semantic_section,
                        page_no=_chunk_effective_page_no(source_chunk),
                        source_chunk_index=item.source_chunk_index,
                        extra={"source_quote": source_quote[:300]},
                    )
                ],
                summary={"semantic_section_id": str(semantic_section.id)},
            )
        row_quote = _best_table_row_quote(source_chunk, cleaned_text)
        if row_quote:
            source_quote = row_quote

        is_mandatory = _candidate_is_mandatory(item_type, risk_level, cleaned_text, item.is_mandatory)
        needs_review, classification_reason, split_reason, review_hint = _llm_candidate_notes(
            item.model_copy(update={"item_type": item_type, "risk_level": risk_level}),
            source_chunk,
            cleaned_text,
            )
        if source_chunk_was_corrected:
            needs_review = True
            source_hint = (
                f"模型引用的 chunk_index={item.source_chunk_index} 与 source_quote 不一致，"
                f"系统已按同段唯一摘录重定位到 chunk {source_chunk.chunk_index}，请人工复核。"
            )
            review_hint = f"{source_hint} {review_hint}" if review_hint else source_hint
        if source_quote_spans_adjacent_chunks:
            needs_review = True
            source_hint = "source_quote 跨相邻解析分块连续匹配，系统已保留候选项，请人工复核跨页摘录。"
            review_hint = f"{source_hint} {review_hint}" if review_hint else source_hint
        if source_quote_text_was_aligned:
            needs_review = True
            source_hint = "模型摘录与原文存在可定位词项差异，系统已按来源原文修正条目文本，请人工复核。"
            review_hint = f"{source_hint} {review_hint}" if review_hint else source_hint
        normalized = item.normalized_requirement or _semantic_key(cleaned_text, item_type)
        if not normalized.startswith("auto:"):
            normalized = _normalized_key(normalized)
        extraction_provider = f"{result.provider}:{result.model_name}"
        explanation = _candidate_explanation(
            item_type=item_type,
            text=cleaned_text,
            heading_path=source_chunk.heading_path,
            risk_level=risk_level,
            is_mandatory=is_mandatory,
            extraction_provider=extraction_provider,
        )
        explanation.update(
            {
                "prompt_id": prompt.prompt_id,
                "prompt_version": prompt.prompt_version,
                "output_schema": "compliance_extract_by_section",
                "classification_reason": classification_reason,
                "split_reason": split_reason,
                "source_quote": source_quote[:300],
                "review_hint": review_hint,
                "needs_human_review": needs_review,
                "model_confidence_score": item.confidence_score,
                "semantic_section_id": str(semantic_section.id),
                "semantic_section_index": semantic_section.section_index,
                "semantic_section_title": semantic_section.title,
            }
        )
        candidates.append(
            ComplianceCandidate(
                source_chunk_index=source_chunk.chunk_index,
                item_type=item_type,
                requirement_text=cleaned_text,
                normalized_requirement=normalized,
                response_suggestion=item.response_suggestion,
                risk_level=risk_level,
                is_mandatory=is_mandatory,
                confidence_score=_confidence(item.confidence_score),
                explanation_json=explanation,
            )
        )
    semantic_section.status = "verified"
    return f"{result.provider}:{result.model_name}", candidates


def _is_llm_timeout_error(exc: LLMGatewayError) -> bool:
    message = str(exc).lower()
    return "timeout" in message or "timed out" in message


def _is_retriable_llm_response_error(exc: Exception) -> bool:
    if isinstance(exc, LLMGatewayError):
        return _is_llm_timeout_error(exc)
    return isinstance(exc, (json.JSONDecodeError, ValidationError))


def _llm_retry_reason(exc: Exception) -> str:
    if isinstance(exc, LLMGatewayError) and _is_llm_timeout_error(exc):
        return "模型超时"
    if isinstance(exc, json.JSONDecodeError):
        return "模型返回的 JSON 无法解析"
    if isinstance(exc, ValidationError):
        return "模型返回结构不完整"
    return "模型响应异常"


def _split_chunks_for_llm_retry(
    chunks: list[DocumentChunk],
    *,
    include_adjacent_overlap: bool = True,
) -> list[list[DocumentChunk]]:
    raw_batches: list[list[DocumentChunk]] = []
    current: list[DocumentChunk] = []
    current_char_count = 0
    for chunk in chunks:
        chunk_char_count = len(chunk.content_text or "")
        would_exceed = current and (
            len(current) + 1 > SECTION_RETRY_MAX_CHUNKS
            or current_char_count + chunk_char_count > SECTION_RETRY_MAX_CHARS
        )
        if would_exceed:
            raw_batches.append(current)
            current = []
            current_char_count = 0
        current.append(chunk)
        current_char_count += chunk_char_count
    if current:
        raw_batches.append(current)
    if len(raw_batches) == 1 and len(chunks) > 1:
        midpoint = max(1, len(chunks) // 2)
        raw_batches = [chunks[:midpoint], chunks[midpoint:]]

    batches: list[list[DocumentChunk]] = []
    for index, batch in enumerate(raw_batches):
        overlapped = list(batch)
        if include_adjacent_overlap and index > 0:
            overlapped.insert(0, raw_batches[index - 1][-1])
        if include_adjacent_overlap and index < len(raw_batches) - 1:
            overlapped.append(raw_batches[index + 1][0])
        deduped: list[DocumentChunk] = []
        seen_chunk_indexes: set[int] = set()
        for chunk in overlapped:
            if chunk.chunk_index in seen_chunk_indexes:
                continue
            seen_chunk_indexes.add(chunk.chunk_index)
            deduped.append(chunk)
        batches.append(deduped)
    return batches


def _merge_provider_names(providers: list[str]) -> str:
    ordered = list(dict.fromkeys(provider for provider in providers if provider))
    return "+".join(ordered) if ordered else "unknown"


def _call_section_llm_resilient(
    db: Session,
    task: AsyncTask,
    semantic_section: DocumentSemanticSection,
    chunks: list[DocumentChunk],
    *,
    section_position: int,
    total_sections: int,
    progress: int,
    retry_depth: int = 0,
    progress_updates: bool = True,
) -> tuple[str, list[ComplianceCandidate]]:
    try:
        return _call_section_llm(db, task, semantic_section, chunks)
    except (LLMGatewayError, json.JSONDecodeError, ValidationError) as exc:
        if not _is_retriable_llm_response_error(exc) or len(chunks) <= 1:
            raise
        retry_reason = _llm_retry_reason(exc)

    providers: list[str] = []
    candidates: list[ComplianceCandidate] = []
    batches = _split_chunks_for_llm_retry(chunks, include_adjacent_overlap=retry_depth == 0)
    for retry_index, batch in enumerate(batches, start=1):
        batch_char_count = sum(len(chunk.content_text or "") for chunk in batch)
        if progress_updates:
            _update_matrix_task_progress(
                db,
                task,
                progress=progress,
                stage="section_llm_extract_retry",
                message=(
                    f"{retry_reason}后细分重试第 {section_position}/{total_sections} 段："
                    f"{semantic_section.title}（子段 {retry_index}/{len(batches)}，"
                    f"{len(batch)} 个分块，约 {batch_char_count} 字）"
                ),
                extra={
                    "section_index": semantic_section.section_index,
                    "section_title": semantic_section.title,
                    "section_position": section_position,
                    "section_count": total_sections,
                    "retry_depth": retry_depth + 1,
                    "retry_index": retry_index,
                    "retry_count": len(batches),
                    "retry_reason": retry_reason,
                    "chunk_count": len(batch),
                    "char_count": batch_char_count,
                },
            )
        provider, batch_candidates = _call_section_llm_resilient(
            db,
            task,
            semantic_section,
            batch,
            section_position=section_position,
            total_sections=total_sections,
            progress=progress,
            retry_depth=retry_depth + 1,
            progress_updates=progress_updates,
        )
        providers.append(provider)
        candidates.extend(batch_candidates)
    semantic_section.status = "verified"
    return _merge_provider_names(providers), candidates


def _llm_candidate_notes(
    item: LLMComplianceItem,
    source_chunk: DocumentChunk,
    cleaned_text: str,
) -> tuple[bool, str | None, str | None, str | None]:
    needs_review = bool(item.needs_human_review)
    review_reasons: list[str] = []

    if item.confidence_score < LLM_LOW_CONFIDENCE_THRESHOLD:
        needs_review = True
        review_reasons.append("模型置信度较低，需要人工复核。")

    rule_type = _rule_item_type(cleaned_text, source_chunk.heading_path)
    if item.item_type != rule_type and item.item_type != "other":
        needs_review = True
        review_reasons.append(f"模型分类为{_item_type_label(item.item_type)}，规则复核倾向为{_item_type_label(rule_type)}。")

    rule_risk = _risk_level(rule_type if item.item_type == "other" else item.item_type, cleaned_text)
    if item.risk_level != rule_risk:
        needs_review = True
        review_reasons.append(f"模型风险为{item.risk_level}，规则复核倾向为{rule_risk}。")

    classification_reason = item.classification_reason or (
        f"模型分类为{_item_type_label(item.item_type)}，规则复核参考类型为{_item_type_label(rule_type)}。"
    )
    split_reason = item.split_reason or "模型按最小可审核要求拆分；人工可对照来源 chunk 复核。"
    review_hint = item.review_hint
    if review_reasons:
        review_hint = " ".join(review_reasons + ([review_hint] if review_hint else []))
    return needs_review, classification_reason, split_reason if split_reason else None, review_hint


def _call_llm(
    db: Session,
    task: AsyncTask,
    chunks: list[DocumentChunk],
) -> tuple[str, list[ComplianceCandidate]]:
    messages = _llm_prompt(chunks)
    prompt = get_prompt("compliance_extract", "1.1.0")
    char_count = sum(len(chunk.content_text or "") for chunk in chunks)
    result = chat_completion(
        db,
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        section_id=task.section_id,
        actor_user_id=task.created_by,
        actor_type="worker",
        task_type="compliance_matrix_generation",
        prompt_version=prompt.prompt_version,
        messages=messages,
        complexity="complex" if len(chunks) >= 40 or char_count >= 6000 else "simple",
        temperature=0.0,
        response_format={"type": "json_object"},
        timeout_seconds=180.0,
        evidence_refs={
            "chunk_ids": [str(chunk.id) for chunk in chunks],
            "chunk_indexes": [chunk.chunk_index for chunk in chunks],
            "document_version_ids": sorted({str(chunk.document_version_id) for chunk in chunks}),
        },
    )
    parsed = LLMComplianceResponse.model_validate(
        _normalize_llm_compliance_payload(_json_from_model_text(result.content))
    )
    chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    candidates: list[ComplianceCandidate] = []
    for item in parsed.items:
        cleaned_text = _clean_requirement_text(item.requirement_text)
        if not cleaned_text:
            continue
        source_chunk = chunk_by_index.get(item.source_chunk_index)
        if source_chunk is None:
            continue
        if _should_skip_rule_text(cleaned_text, source_chunk.heading_path):
            continue
        if _is_contact_text(cleaned_text, source_chunk.heading_path):
            continue
        cleaned_text = _contextual_requirement_text(cleaned_text, source_chunk.heading_path)
        if _should_skip_rule_text(cleaned_text, source_chunk.heading_path):
            continue
        needs_review, classification_reason, split_reason, review_hint = _llm_candidate_notes(
            item,
            source_chunk,
            cleaned_text,
        )
        normalized = item.normalized_requirement or _semantic_key(cleaned_text, item.item_type)
        if not normalized.startswith("auto:"):
            normalized = _normalized_key(normalized)
        is_mandatory = _candidate_is_mandatory(item.item_type, item.risk_level, cleaned_text, item.is_mandatory)
        explanation = _candidate_explanation(
            item_type=item.item_type,
            text=cleaned_text,
            heading_path=source_chunk.heading_path,
            risk_level=item.risk_level,
            is_mandatory=is_mandatory,
            extraction_provider=f"{result.provider}:{result.model_name}",
        )
        explanation.update(
            {
                "prompt_id": prompt.prompt_id,
                "prompt_version": prompt.prompt_version,
                "output_schema": "compliance_extract",
                "classification_reason": classification_reason,
                "split_reason": split_reason,
                "source_quote": _source_quote(item, source_chunk, cleaned_text),
                "review_hint": review_hint,
                "needs_human_review": needs_review,
                "model_confidence_score": item.confidence_score,
            }
        )
        candidates.append(
            ComplianceCandidate(
                source_chunk_index=item.source_chunk_index,
                item_type=item.item_type,
                requirement_text=cleaned_text,
                normalized_requirement=normalized,
                response_suggestion=item.response_suggestion,
                risk_level=item.risk_level,
                is_mandatory=is_mandatory,
                confidence_score=_confidence(item.confidence_score),
                explanation_json=explanation,
            )
        )
    return f"{result.provider}:{result.model_name}", candidates


def _rule_item_type(text: str, heading_path: str | None) -> str:
    heading_leaf = _heading_leaf(heading_path) or ""
    qualification_context = "资格" in heading_leaf and len(heading_leaf) <= 40
    technical_context = any(signal in heading_leaf for signal in ("技术要求", "技术响应", "技术参数", "采购需求"))
    if _is_reference_info(text, heading_path):
        return "reference_info"
    if "响应文件的组成" in text:
        return "format"
    if any(keyword in text for keyword in ("截止时间", "开标时间", "解密", "递交")):
        return "deadline"
    if ("请于" in text and "至" in text) or re.search(
        r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日",
        text,
    ):
        return "deadline"
    if "是否允许分包" in text:
        return "mandatory_response"
    if any(
        keyword in text
        for keyword in ("评分", "评审办法", "综合评分法", "权重系数", "浮动系数", "评标基准价")
    ) or re.search(
        r"(?:得|扣|加)\s*\d+(?:\.\d+)?\s*分|最高得|不得分|分值|满分",
        text,
    ) or re.search(
        r"\bK\d+--",
        text,
        flags=re.IGNORECASE,
    ):
        return "scoring"
    if any(keyword in text for keyword in ("评标办法", "综合评估法")):
        return "scoring"
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
    compact = re.sub(r"\s+", "", text)
    if _is_standalone_date_text(text):
        return True
    if compact == "目录" or (
        compact.startswith("目录") and "第一章" in compact and "第二章" in compact
    ):
        return True
    if compact in {"无", "否", "/", "／"}:
        return True
    if (
        compact.endswith(("：无", ":无", "：否", ":否"))
        and "类似工程业绩要求" not in compact
        and not any(keyword in compact for keyword in ("保证金", "交易担保", "中小企业"))
    ):
        return True
    if re.fullmatch(r"第[一二三四五六七八九十]+章[\u4e00-\u9fff]+(?:前附表)?", compact):
        return True
    if "示范文本" in text and "不得改动" in text:
        return True
    if "有下划线" in text and "不得改动" in text:
        return True
    if "发包人应根据项目的实际情况合理选定评审办法" in text:
        return True
    if heading_leaf and text == heading_leaf:
        return True
    if _is_contact_text(text, heading_path):
        return True
    if _is_pure_heading(text):
        return True
    if STRUCTURAL_HEADING_RE.match(text):
        return True
    if text.endswith(("：", ":")) and len(text) <= 40:
        return True
    if text.endswith(("：", ":")) and "类似工程业绩要求" in text:
        return True
    if text.endswith(("：", ":")) and not any(signal in text for signal in REQUIREMENT_SIGNALS):
        return True
    if "/年/月/日" in compact or "承接过/业绩" in compact:
        return True
    if "发包人需要增加的、符合法律法规的其他要求" in text and len(text) <= 80:
        return True
    if compact in {"建设规模范围内的设计、施工总承包", "建设规模范围内的设计施工总承包"}:
        return True
    if re.match(r"^(项目名称|建设地点|建设规模|资金来源(?:及比例)?)[：:]", text):
        return True
    if any(text.startswith(prefix) for prefix in ("项目名称", "建设地点", "资金来源及比例", "资金来源")) and not any(
        signal in text for signal in ("须", "必须", "不得", "最高", "限价", "工期", "质量")
    ):
        return True
    if "交易须知具体内容如与本前附表不一致" in text:
        return True
    if text.startswith(("重新组织交易的情形", "成交人确定：")):
        return True
    if re.match(r"^于\s*\d+\s*人的单数组成", text):
        return True
    if text == "不要求" and "类似工程业绩要求" not in (heading_path or ""):
        return True
    if "由招标人根据招标项目具体情况" in text:
        return True
    if re.match(r"^(项目编号|项目名称|预算金额|售价|方式)[:：]", text):
        return True
    if text.startswith("地点：") and "下载招标文件" in text:
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
    if not matches:
        return [text]
    if len(matches) == 1:
        return _single_marker_tail_after_long_prefix(text, matches[0]) or [text]
    parts: list[str] = []
    prefix = _context_prefix(text[: matches[0].start()])
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        part = _with_context_prefix(prefix, part)
        parts.append(part)
    return [part for part in parts if part]


def _chinese_marker_value(marker: str) -> int | None:
    if marker == "十":
        return 10
    if "十" not in marker:
        return CHINESE_NUMERAL_VALUES.get(marker)
    left, _, right = marker.partition("十")
    tens = CHINESE_NUMERAL_VALUES.get(left, 1) if left else 1
    ones = CHINESE_NUMERAL_VALUES.get(right, 0) if right else 0
    return tens * 10 + ones


def _consecutive_chinese_marker_matches(text: str) -> list[re.Match[str]]:
    best: list[tuple[re.Match[str], int]] = []
    current: list[tuple[re.Match[str], int]] = []
    for match in CHINESE_LIST_MARKER_RE.finditer(text):
        value = _chinese_marker_value(match.group(2))
        if value is None:
            current = []
            continue
        if not current or value == current[-1][1] + 1:
            current.append((match, value))
            continue
        if len(current) > len(best):
            best = current
        current = [(match, value)]
    if len(current) > len(best):
        best = current
    return [match for match, _ in best] if len(best) >= 2 else []


def _context_prefix(prefix: str) -> str | None:
    prefix = _clean_requirement_text(prefix).strip(" ：:；;，,")
    if not prefix:
        return None
    compact = re.sub(r"\s+", "", prefix)
    if len(compact) > 60:
        return None
    if any(mark in prefix for mark in "。！？!?"):
        return None
    if prefix.count("；") + prefix.count(";") >= 2:
        return None
    if "发包人需要增加" in prefix or "说明：" in prefix:
        return None
    return prefix


def _with_context_prefix(prefix: str | None, part: str) -> str:
    if not prefix:
        return part
    return f"{prefix.rstrip(':：')}：{part}"


def _single_marker_tail_after_long_prefix(
    text: str,
    match: re.Match[str],
) -> list[str] | None:
    prefix = text[: match.start()].strip()
    if not prefix:
        return None
    if _context_prefix(prefix) is not None:
        return None
    if len(re.sub(r"\s+", "", _clean_requirement_text(prefix))) <= 60:
        return None
    tail = text[match.start() :].strip()
    return [tail] if tail else None


def _split_by_inline_markers(text: str, marker_re: re.Pattern[str]) -> list[str]:
    matches = list(marker_re.finditer(text))
    if not matches:
        return [text]
    if len(matches) == 1:
        return _single_marker_tail_after_long_prefix(text, matches[0]) or [text]

    prefix = _context_prefix(text[: matches[0].start()])
    parts: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        if part:
            parts.append(_with_context_prefix(prefix, part))
    return parts or [text]


def _split_by_chinese_markers(text: str) -> list[str]:
    matches = _consecutive_chinese_marker_matches(text)
    if len(matches) <= 1:
        return [text]
    parts: list[str] = []
    for index, match in enumerate(matches):
        start = match.start(2)
        end = matches[index + 1].start(2) if index + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        if part:
            parts.append(part)
    return parts or [text]


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
    deadline_match = re.search(
        r"并于(?P<deadline>\d{4}年\d{2}月\d{2}日\s*\d{2}点\d{2}分（北京时间）)前递交投标文件",
        text,
    )
    if deadline_match:
        requirements.append(f"投标文件递交截止时间为{deadline_match.group('deadline')}。")

    return requirements or [text]


def _selected_single_choice_texts(text: str) -> list[str] | None:
    if not any(prefix in text for prefix in ("是否允许联合体", "是否允许分包", "响应文件的质询")):
        return None
    if "不允许" not in text and "不质询" not in text:
        return None
    selected = OPTION_MARKER_RE.split(text, maxsplit=1)[0].strip(" ；;。")
    if not selected:
        return None
    return [selected if selected.endswith("。") else f"{selected}。"]


def _project_manager_requirement_texts(text: str) -> list[str] | None:
    if "拟派项目负责人" not in text or "☑" not in text:
        return None

    requirements: list[str] = []
    qualification_match = re.search(r"拟派项目负责人[：:]\s*(具有.*?资格)", text)
    if qualification_match:
        requirements.append(f"资质要求：拟派项目负责人{qualification_match.group(1)}。")

    for selected in re.findall(r"☑\s*([^□☐☑\uf0a3]+)", text):
        cleaned = re.split(r"说明[:：]", selected, maxsplit=1)[0]
        cleaned = re.sub(r"发包人需要增加的、符合法律法规的其他要求.*$", "", cleaned).strip(" ；;。")
        if cleaned:
            requirements.append(cleaned if cleaned.endswith("。") else f"{cleaned}。")

    return requirements or None


def _response_file_composition_texts(text: str) -> list[str] | None:
    if "响应文件的组成" not in text or "☑" not in text:
        return None
    selected_match = re.search(r"☑\s*(.+)$", text)
    if selected_match is None:
        return None
    selected = re.split(r"说明[:：]", selected_match.group(1), maxsplit=1)[0]
    selected = selected.strip(" ；;。")
    if not selected:
        return None
    return [f"响应文件的组成：{selected}。"]


def _split_scoring_parameter_texts(text: str) -> list[str]:
    matches = list(re.finditer(r"\bK\d+--", text, flags=re.IGNORECASE))
    if len(matches) <= 1:
        return [text]

    prefix = _context_prefix(text[: matches[0].start()])
    parts: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        part = text[start:end].strip(" ；;")
        if part:
            parts.append(_with_context_prefix(prefix, part))
    return parts or [text]


def _atomic_requirement_texts(text: str) -> list[str]:
    selected_single_choice = _selected_single_choice_texts(text)
    if selected_single_choice is not None:
        return selected_single_choice
    response_file_composition = _response_file_composition_texts(text)
    if response_file_composition is not None:
        return response_file_composition
    if "响应文件的组成" in text:
        return [text]
    overview_parts = _split_project_overview(text)
    atomic: list[str] = []
    for overview_part in overview_parts:
        chinese_paren_parts = _split_by_inline_markers(overview_part, CHINESE_PAREN_MARKER_RE)
        for chinese_paren_part in chinese_paren_parts:
            circled_parts = _split_by_inline_markers(chinese_paren_part, CIRCLED_LIST_MARKER_RE)
            for circled_part in circled_parts:
                chinese_marker_parts = _split_by_chinese_markers(circled_part)
                for chinese_part in chinese_marker_parts:
                    marker_parts = _split_by_markers(chinese_part)
                    for part in marker_parts:
                        for scoring_part in _split_scoring_parameter_texts(part):
                            project_manager_requirements = _project_manager_requirement_texts(
                                scoring_part
                            )
                            if project_manager_requirements is not None:
                                atomic.extend(project_manager_requirements)
                                continue
                            atomic.extend(_split_qualification_series(scoring_part))
    return [item.strip() for item in atomic if item.strip()]


def _risk_level(item_type: str, text: str) -> str:
    if item_type == "reference_info":
        return "low"
    if item_type == "scoring":
        return "medium"
    if "类似工程业绩要求：不要求" in text:
        return "low"
    if any(keyword in text for keyword in ("保修要求", "缺陷责任期", "招标范围", "评标办法")):
        return "high"
    if any(keyword in text for keyword in ("扣罚", "罚没全部", "履约保证金")):
        return "high"
    if item_type == "technical_response":
        if any(keyword in text for keyword in ("必须", "须", "不得", "验收", "洁净等级", "风量", "压差")):
            return "high"
        return "medium"
    if item_type in {"qualification", "deadline"}:
        return "high"
    if any(keyword in text for keyword in ("必须", "须", "不得", "不允许", "最高投标限价", "CA")):
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
        normalized = _semantic_key(requirement, "qualification")
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
        for source_text in _rule_source_texts(chunk):
            original_text = _clean_requirement_text(source_text)
            is_similar_performance_not_required = (
                original_text == "不要求" and "类似工程业绩要求" in (chunk.heading_path or "")
            )
            if not original_text or (len(original_text) < 4 and not is_similar_performance_not_required):
                continue
            if original_text.lstrip().startswith("□"):
                continue
            if (
                "□" in original_text
                and "☑" not in original_text
                and "√" not in original_text
                and "？" not in original_text
                and "?" not in original_text
            ):
                continue
            atomic_texts = _atomic_requirement_texts(original_text)
            if _should_skip_rule_text(original_text, chunk.heading_path) and all(
                _should_skip_rule_text(text, chunk.heading_path) for text in atomic_texts
            ):
                continue

            for text in atomic_texts:
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
                        "不允许",
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
                is_mandatory = _candidate_is_mandatory(item_type, risk_level, text)
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


def _review_section_coverage(
    db: Session,
    task: AsyncTask,
    semantic_section: DocumentSemanticSection,
    chunks: list[DocumentChunk],
    candidates: list[ComplianceCandidate],
) -> list[dict[str, Any]]:
    prompt = get_prompt("section_coverage_review", "1.1.0")
    items_payload = [
        {
            "source_chunk_index": item.source_chunk_index,
            "item_type": item.item_type,
            "requirement_text": item.requirement_text,
            "risk_level": item.risk_level,
            "source_quote": item.explanation_json.get("source_quote"),
        }
        for item in candidates
    ]
    messages = prompt.render(
        section_json=json.dumps(_section_record_payload(semantic_section), ensure_ascii=False),
        chunks_json=json.dumps(_section_chunk_payload(chunks), ensure_ascii=False),
        items_json=json.dumps(items_payload, ensure_ascii=False),
    )
    result = chat_completion(
        db,
        tenant_id=task.tenant_id,
        project_id=task.project_id,
        section_id=task.section_id,
        actor_user_id=task.created_by,
        actor_type="worker",
        task_type="section_compliance_extract",
        prompt_version=prompt.prompt_version,
        messages=messages,
        complexity="complex" if len(chunks) >= 20 else "simple",
        temperature=0.0,
        response_format={"type": "json_object"},
        timeout_seconds=120.0,
        evidence_refs={
            "semantic_section_id": str(semantic_section.id),
            "chunk_ids": [str(chunk.id) for chunk in chunks],
            "chunk_indexes": [chunk.chunk_index for chunk in chunks],
            "candidate_count": len(candidates),
        },
    )
    review = LLMCoverageReview.model_validate(
        _normalize_coverage_review_payload(_json_from_model_text(result.content))
    )
    issues: list[dict[str, Any]] = []
    for issue in review.issues:
        issues.append(
            _quality_issue(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
                semantic_section=semantic_section,
                page_no=issue.page_no,
                source_chunk_index=issue.source_chunk_index,
                extra={
                    "suggested_requirement": issue.suggested_requirement,
                    "coverage_status": review.status,
                },
            )
        )
    return issues


def _review_section_coverage_resilient(
    db: Session,
    task: AsyncTask,
    semantic_section: DocumentSemanticSection,
    chunks: list[DocumentChunk],
    candidates: list[ComplianceCandidate],
    *,
    section_position: int,
    total_sections: int,
    progress: int,
    retry_depth: int = 0,
    progress_updates: bool = True,
) -> list[dict[str, Any]]:
    try:
        return _review_section_coverage(db, task, semantic_section, chunks, candidates)
    except (LLMGatewayError, json.JSONDecodeError, ValidationError) as exc:
        if not _is_retriable_llm_response_error(exc) or len(chunks) <= 1:
            raise
        retry_reason = _llm_retry_reason(exc)

    issues: list[dict[str, Any]] = []
    batches = _split_chunks_for_llm_retry(chunks)
    for retry_index, batch in enumerate(batches, start=1):
        batch_indexes = {chunk.chunk_index for chunk in batch}
        batch_candidates = [
            candidate for candidate in candidates if candidate.source_chunk_index in batch_indexes
        ]
        batch_char_count = sum(len(chunk.content_text or "") for chunk in batch)
        if progress_updates:
            _update_matrix_task_progress(
                db,
                task,
                progress=progress,
                stage="section_coverage_review_retry",
                message=(
                    f"覆盖复核{retry_reason}后细分重试第 {section_position}/{total_sections} 段："
                    f"{semantic_section.title}（子段 {retry_index}/{len(batches)}，"
                    f"{len(batch)} 个分块，约 {batch_char_count} 字）"
                ),
                extra={
                    "section_index": semantic_section.section_index,
                    "section_title": semantic_section.title,
                    "section_position": section_position,
                    "section_count": total_sections,
                    "retry_depth": retry_depth + 1,
                    "retry_index": retry_index,
                    "retry_count": len(batches),
                    "retry_reason": retry_reason,
                    "chunk_count": len(batch),
                    "char_count": batch_char_count,
                    "candidate_count": len(batch_candidates),
                },
            )
        issues.extend(
            _review_section_coverage_resilient(
                db,
                task,
                semantic_section,
                batch,
                batch_candidates,
                section_position=section_position,
                total_sections=total_sections,
                progress=progress,
                retry_depth=retry_depth + 1,
                progress_updates=progress_updates,
            )
        )
    return issues


def _is_boilerplate_semantic_section(section: DocumentSemanticSection) -> bool:
    if section.section_type != "other":
        return False
    marker_text = f"{section.title or ''} {section.evidence or ''}"
    return any(marker in marker_text for marker in ("封面", "目录", "说明", "示范文本"))


def _table_guard_item_type(label: str) -> str | None:
    compact_label = _compact_for_match(label)
    if "中小企业" in label:
        return "qualification"
    if "响应文件有效期" in compact_label:
        return "mandatory_response"
    if "最高" in label and "限价" in label:
        return "mandatory_response"
    if "工期" in label or "服务期限" in label:
        return "mandatory_response"
    if "交易时间" in compact_label or ("截止" in label and "时间" in label):
        return "deadline"
    if "交易方式" in label or "评审办法" in label:
        return "scoring"
    if "保证金" in label or "交易担保" in label:
        return "mandatory_response"
    if "发包范围" in label or "招标范围" in label or "承包方式" in label:
        return "mandatory_response"
    return None


def _table_guard_row_pairs(row: list[Any]) -> list[tuple[str, str]]:
    cells = [_clean_requirement_text(str(cell)) for cell in row if cell is not None and _clean_requirement_text(str(cell))]
    if len(cells) < 2:
        return []
    if re.fullmatch(r"\d{1,2}", cells[0]) and len(cells) >= 3:
        return [(cells[1], "；".join(cells[2:]))]
    if len(cells) >= 4 and _table_guard_item_type(cells[0]) and _table_guard_item_type(cells[2]):
        pairs: list[tuple[str, str]] = []
        for index in range(0, len(cells) - 1, 2):
            if _table_guard_item_type(cells[index]):
                pairs.append((cells[index], cells[index + 1]))
        return pairs
    return [(cells[0], "；".join(cells[1:]))]


def _table_guard_value(label: str, value: str) -> str:
    if "中小企业" in label:
        selected_match = re.search(r"[☑√✓]\s*([^□☐☑√✓\uf0a3]+)", value)
        if selected_match:
            selected = re.split(r"说明[:：]", selected_match.group(1), maxsplit=1)[0]
            return selected.strip(" ；;。") or value
    return value


def _augment_section_candidates_from_table_guards(
    chunks: list[DocumentChunk],
    candidates: list[ComplianceCandidate],
    *,
    extraction_provider: str,
) -> list[ComplianceCandidate]:
    existing_text = "\n".join(_compact_for_match(candidate.requirement_text) for candidate in candidates)
    seen = {candidate.normalized_requirement for candidate in candidates}
    augmented = list(candidates)
    for chunk in chunks:
        table_json = chunk.table_json or {}
        rows = table_json.get("rows") if isinstance(table_json, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, list) or len(row) < 2:
                continue
            for label, value in _table_guard_row_pairs(row):
                item_type = _table_guard_item_type(label)
                if item_type is None:
                    continue
                value = _table_guard_value(label, value)
                compact_label = _compact_for_match(label)
                compact_value = _compact_for_match(value)
                if (
                    compact_label
                    and compact_label in existing_text
                    and len(compact_value) >= 2
                    and compact_value in existing_text
                ):
                    continue
                requirement = _clean_requirement_text(f"{label}：{value}")
                if _should_skip_rule_text(requirement, chunk.heading_path):
                    continue
                normalized = _semantic_key(requirement, item_type)
                if normalized in seen:
                    continue
                seen.add(normalized)
                risk_level = _risk_level(item_type, requirement)
                if (
                    item_type == "deadline"
                    or ("最高" in label and "限价" in label)
                    or "工期" in label
                    or "服务期限" in label
                    or "有效期" in label
                    or "保证金" in label
                    or "交易担保" in label
                ):
                    risk_level = "high"
                is_mandatory = _candidate_is_mandatory(item_type, risk_level, requirement)
                augmented.append(
                    ComplianceCandidate(
                        source_chunk_index=chunk.chunk_index,
                        item_type=item_type,
                        requirement_text=requirement,
                        normalized_requirement=normalized,
                        response_suggestion=_response_suggestion(item_type, requirement),
                        risk_level=risk_level,
                        is_mandatory=is_mandatory,
                        confidence_score=Decimal("0.7200"),
                        explanation_json={
                            **_candidate_explanation(
                                item_type=item_type,
                                text=requirement,
                                heading_path=chunk.heading_path,
                                risk_level=risk_level,
                                is_mandatory=is_mandatory,
                                extraction_provider=extraction_provider,
                            ),
                            "source_quote": requirement[:300],
                            "needs_human_review": True,
                            "review_hint": "模型未覆盖该关键表格字段，由结构化表格守卫补齐，请人工核对。",
                            "classification_reason": "结构化表格守卫识别关键字段。",
                            "split_reason": "字段-值表格行形成单条可审核要求。",
                            "table_guard": True,
                        },
                    )
                )
    return augmented


COMMITMENT_BASIC_ABILITY_REQUIREMENTS = (
    "具有独立承担民事责任的能力",
    "具有良好的商业信誉和健全的财务会计制度",
    "具有履行合同所必需的设备和专业技术能力",
    "有依法缴纳税收和社会保障资金的良好记录",
    "参加活动前三年内，在经营活动中没有重大违法记录",
    "具有法律、行政法规规定的其他条件",
)


def _commitment_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    if not all(signal in source_text for signal in ("诚信承诺书", "基本能力方面")):
        return []

    guarded_items: list[tuple[str, str, str]] = []
    for phrase in COMMITMENT_BASIC_ABILITY_REQUIREMENTS:
        pattern = rf"(?:\d+[.．、]\s*)?{re.escape(phrase)}[；;。]?"
        match = re.search(pattern, source_text)
        if not match:
            continue
        source_quote = _clean_requirement_text(match.group(0))
        requirement_body = re.sub(r"^\d+[.．、]\s*", "", source_quote).rstrip("；;")
        requirement = _clean_requirement_text(f"诚信承诺书：{requirement_body}")
        guarded_items.append(("qualification", requirement, source_quote))
    return guarded_items


def _qualification_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []

    joint_venture_leader_match = re.search(
        r"以联合体投标的，拟任工程总承包项目负责人须为联合体牵头人单位人员[）)]?[；;。]?",
        source_text,
    )
    if joint_venture_leader_match:
        source_quote = _clean_requirement_text(joint_venture_leader_match.group(0)).rstrip("）)")
        guarded_items.append(
            (
                "qualification",
                "以联合体投标的，拟任工程总承包项目负责人须为联合体牵头人单位人员。",
                source_quote,
            )
        )

    joint_venture_accept_match = re.search(
        r"(?:\d+(?:\.\d+)?\s*)?(?:本次招标|本项目)接受联合体投标"
        r"(?:，联合体投标的相关要求见投标人须知前附表)?[。；;]?",
        source_text,
    )
    if joint_venture_accept_match:
        source_quote = _clean_requirement_text(joint_venture_accept_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "本项目接受联合体投标。",
                source_quote,
            )
        )

    joint_venture_rules_match = re.search(
        r"1\.4\.2\s*交易公告规定接受联合体承包的，联合体除应符合本章第\s*1\.4\.1\s*项和交易须知前"
        r"\s*附表的要求外，还应遵守以下规定：.*?"
        r"\(3\)联合体各方不得再以自己名义单独或参加其他联合体在同一项目中响应[。；;]?",
        source_text,
    )
    if joint_venture_rules_match:
        source_quote = _clean_requirement_text(joint_venture_rules_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "联合体承包：接受联合体的，须签订联合体协议书；同一专业按资质等级较低单位确定资质等级；联合体各方不得再以自己名义或参加其他联合体响应。",
                source_quote,
            )
        )

    in_progress_manager_match = re.search(
        r"拟派项目负责人在投标截止时间尚有在其他在建合同工程中\s*担任项目负责人的情形为“有在建合同工程”[。；;]?",
        source_text,
    )
    if in_progress_manager_match:
        source_quote = _clean_requirement_text(in_progress_manager_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "拟派项目负责人在投标截止时间尚有在其他在建合同工程中担任项目负责人的，认定为有在建合同工程。",
                source_quote,
            )
        )

    in_progress_period_match = re.search(
        r"在建合同工程的时间界定：在建合同工程的开始时间为合同\s*工程中标通知书发出日期，"
        r"或者不通过招标方式的则以合同签订\s*日期为开始时间，结束时间为该合同工程验收合格或合同解除日\s*期[）)]?[。；;]?",
        source_text,
    )
    if in_progress_period_match:
        source_quote = _clean_requirement_text(in_progress_period_match.group(0)).rstrip("）)")
        guarded_items.append(
            (
                "qualification",
                "在建合同工程时间界定：以中标通知书发出日期或合同签订日期为开始时间，以合同工程验收合格或合同解除日期为结束时间。",
                source_quote,
            )
        )

    return guarded_items


def _project_overview_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []

    duration_match = re.search(
        r"(?:\d+(?:\.\d+)?\s*)?工期要求：\s*(\d+)\s*[？?□☐\s]*天\s*[（(]日历日，下同[）)]\s*(?:□月□年)?[；;。]?",
        source_text,
    )
    if duration_match:
        days = duration_match.group(1)
        source_quote = _clean_requirement_text(duration_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                f"工期要求：{days}天（日历日，下同）。",
                source_quote,
            )
        )

    provisional_sum_match = re.search(r"本工程暂列金额：\s*(\d+(?:\.\d+)?)\s*元[。；;]?", source_text)
    if provisional_sum_match:
        amount = provisional_sum_match.group(1)
        source_quote = _clean_requirement_text(provisional_sum_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                f"本工程暂列金额：{amount}元。",
                source_quote,
            )
        )

    return guarded_items


def _deadline_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []

    opening_location_match = re.search(
        r"地点：\s*网上开标，投标人应及时登录[^。；;]*在线参与开标\s*[。；;]?",
        source_text,
    )
    if opening_location_match:
        source_quote = _clean_requirement_text(opening_location_match.group(0))
        location = source_quote.removeprefix("地点：").strip()
        location = re.sub(r"\s+([。；;])", r"\1", location)
        guarded_items.append(
            (
                "deadline",
                f"开标地点：{location}",
                source_quote,
            )
        )

    return guarded_items


def _contract_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []

    defect_match = re.search(
        r"工程缺陷责任期为\s*24\s*个月，缺陷责任期自工程通过竣工验收之日起计算[。；;]?",
        source_text,
    )
    if defect_match:
        source_quote = _clean_requirement_text(defect_match.group(0))
        guarded_items.append(("mandatory_response", f"缺陷责任期：{source_quote}", source_quote))

    price_form_match = re.search(
        r"合同价格形式：[\s\ue000-\uf8ff]*固定单价合同[\s\ue000-\uf8ff]*[。；;]?",
        source_text,
    )
    if price_form_match:
        source_quote = _clean_requirement_text(price_form_match.group(0))
        guarded_items.append(("mandatory_response", source_quote, source_quote))

    contract_price_form_match = re.search(
        r"12\.1\s*合同价格形式\s*1[、.．]\s*单价合同[。；;]?",
        source_text,
    )
    if contract_price_form_match:
        source_quote = _clean_requirement_text(contract_price_form_match.group(0))
        guarded_items.append(("mandatory_response", "合同价格形式：单价合同。", source_quote))

    quality_retention_match = re.search(
        r"剩余\s*1\.5\s*%\s*留作质量保证金（缴纳方式同投标担保）。质量保证金的返还\s*详见工程质量保修书[。；;]?",
        source_text,
    )
    if quality_retention_match:
        source_quote = _clean_requirement_text(quality_retention_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "质量保证金：剩余1.5%留作质量保证金，返还详见工程质量保修书。",
                source_quote,
            )
        )

    quality_guarantee_form_match = re.search(
        r"15\.3\.1\s*承包人提供质量保证金的方式\s*质量保证金采用以下第（3）种方式："
        r".*?其他方式\s*[:：]\s*缴纳形式同投标担保\s*[,，]\s*保证金额为\s*1\.5\s*%\s*的工程款[。；;]?",
        source_text,
    )
    if quality_guarantee_form_match:
        source_quote = _clean_requirement_text(quality_guarantee_form_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "质量保证金：采用缴纳形式同投标担保，保证金额为1.5%的工程款。",
                source_quote,
            )
        )

    performance_bond_penalty_match = re.search(
        r"质量未达到招标文件要求或无法\s*通过竣工验收的，承包人负责返修，直至达到要求，"
        r"并扣罚全部质量履约保证金[^。；;]*[。；;]?",
        source_text,
    )
    if performance_bond_penalty_match:
        source_quote = _clean_requirement_text(performance_bond_penalty_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "履约保证金：质量未达到要求或无法通过竣工验收的，扣罚全部质量履约保证金。",
                source_quote,
            )
        )

    schedule_plan_bond_penalty_match = re.search(
        r"承包人逾期未提交的，每逾期一日，发包人有权扣罚\s*1000\s*元\s*工期\s*履约保证金[^。；;]*[。；;]?",
        source_text,
    )
    if schedule_plan_bond_penalty_match:
        source_quote = _clean_requirement_text(schedule_plan_bond_penalty_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "工期履约保证金：承包人逾期未提交施工组织设计的，每逾期一日扣罚1000元。",
                source_quote,
            )
        )

    management_bond_forfeiture_match = re.search(
        r"发包人可终止本合同，将承包人清退出场，罚没全部履约保证金[^。；;]*[。；;]?",
        source_text,
    )
    if management_bond_forfeiture_match:
        source_quote = _clean_requirement_text(management_bond_forfeiture_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "履约保证金：承包人现场管理等未履行承诺且整改无效或未采取措施时，发包人可终止合同、清退出场并罚没全部履约保证金。",
                source_quote,
            )
        )

    schedule_delay_bond_penalty_match = re.search(
        r"发包人有权要求承包人无条件退场，扣罚全部工期履约保证金[^。；;]*[。；;]?",
        source_text,
    )
    if schedule_delay_bond_penalty_match:
        source_quote = _clean_requirement_text(schedule_delay_bond_penalty_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "工期履约保证金：承包人自身原因造成工期严重滞后且无明显改进措施时，发包人可要求退场并扣罚全部工期履约保证金。",
                source_quote,
            )
        )

    general_contractor_scope_match = re.search(
        r"21\.28\s*总承包服务（配合）内容：甲方另行分包的[^。；;]*不列入本次招标范围，"
        r"不计取总包管理费[^。；;]*[。；;]?",
        source_text,
    )
    if general_contractor_scope_match:
        source_quote = _clean_requirement_text(general_contractor_scope_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "招标范围：甲方另行分包工程不列入本次招标范围，不计取总包管理费；总包仍需履行配合义务并承担相关预留、打孔补洞和保护费用。",
                source_quote,
            )
        )

    payment_guarantee_amount_match = re.search(
        r"(?:\d+[.．、]\s*)?我方保证的金额是主合同约定的工程款的\s*\d+(?:\.\d+)?%"
        r"，数额最高不超过人民币元\s*（大写：\s*）[。；;]?",
        source_text,
    )
    if payment_guarantee_amount_match:
        source_quote = _clean_requirement_text(payment_guarantee_amount_match.group(0))
        requirement = re.sub(r"^\d+[.．、]\s*", "", source_quote).strip()
        guarded_items.append(
            (
                "mandatory_response",
                f"支付担保金额：{requirement}",
                source_quote,
            )
        )

    project_manager_match = re.search(
        r"3\.2\.1\s*项目经理：.*?身份证号：.*?建造师执业资格等级：.*?[；;]",
        source_text,
    )
    if project_manager_match:
        source_quote = _clean_requirement_text(project_manager_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "项目经理信息：须填写姓名、身份证号、建造师执业资格等级。",
                source_quote,
            )
        )

    project_manager_certificate_match = re.search(
        r"建造师注册证书号：.*?建造师执业印章号：.*?安全生产考核合格证书号：.*?[；;]",
        source_text,
    )
    if project_manager_certificate_match:
        source_quote = _clean_requirement_text(project_manager_certificate_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "项目经理信息：须填写建造师注册证书号、建造师执业印章号、安全生产考核合格证书号。",
                source_quote,
            )
        )

    if all(signal in source_text for signal in ("附件8", "履约担保", "担保金额人民币", "担保有效期")):
        header_match = re.search(r"附件8[:：]\s*履约担保", source_text)
        source_quote = _clean_requirement_text(header_match.group(0) if header_match else "附件8：履约担保")
        guarded_items.append(
            (
                "format",
                "附件8履约担保格式：须填写担保金额、担保有效期，并由担保人盖章及法定代表人或委托代理人签字。",
                source_quote,
            )
        )

    if all(signal in source_text for signal in ("附件9", "预付款担保", "担保金额人民币", "担保有效期")):
        header_match = re.search(r"附件9[:：]\s*预付款担保", source_text)
        source_quote = _clean_requirement_text(header_match.group(0) if header_match else "附件9：预付款担保")
        guarded_items.append(
            (
                "format",
                "附件9预付款担保格式：须填写担保金额、担保有效期，并由担保人盖章及法定代表人或委托代理人签字。",
                source_quote,
            )
        )

    if all(signal in source_text for signal in ("附件10", "支付担保", "保证的范围及保证金额", "连带责任保证")):
        header_match = re.search(r"附件10[:：]\s*支付担保", source_text)
        source_quote = _clean_requirement_text(header_match.group(0) if header_match else "附件10：支付担保")
        guarded_items.append(
            (
                "format",
                "附件10支付担保格式：须填写保证范围、保证金额、保证方式、保证期间及代偿安排。",
                source_quote,
            )
        )

    return guarded_items


def _review_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []

    scoring_method_match = re.search(r"(?:采用|评审办法为|评标办法为)?综合评分法", source_text)
    if scoring_method_match and any(signal in source_text for signal in ("评审办法", "评标办法", "第四章")):
        source_quote = _clean_requirement_text(scoring_method_match.group(0))
        guarded_items.append(
            (
                "scoring",
                "评审办法：本项目采用综合评分法。",
                source_quote,
            )
        )

    business_bid_rejection_match = re.search(
        r"2\.改变竞标文件提供的工程量清单.*?"
        r"3\.改变竞标文件规定的暂定内容的[；;。]?.*?"
        r"4\.经评标委员会认定投标人的投标报价低于成本价的[；;。]?.*?"
        r"5\.投标人拒绝按评标委员会要求提供报价分析说明和证明材料的[；;。]?.*?"
        r"6\.工程量清单报价与工、料、机报价及对应的报价分析不相符的.*?理由不成立的[；;。]?",
        source_text,
    )
    if business_bid_rejection_match:
        source_quote = _clean_requirement_text(business_bid_rejection_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "商务标废标条件：不得改变工程量清单或暂定内容；投标报价不得低于成本价；须按要求提供报价分析说明和证明材料；工程量清单报价须与工料机报价、报价分析及施工组织设计匹配。",
                source_quote,
            )
        )

    return guarded_items


def _response_form_text_guard_items(chunk: DocumentChunk) -> list[tuple[str, str, str]]:
    source_text = _clean_requirement_text(chunk.content_text or "")
    guarded_items: list[tuple[str, str, str]] = []
    if "响应函" not in source_text and "授权委托书" not in source_text:
        return guarded_items

    price_amount_match = re.search(
        r"我方愿以人民币\s*[(（]\s*大\s*写\s*[)）]\s*[：:]\s*，\s*RMB\s*[：:]\s*¥\s*元，"
        r"\s*[(（]\s*大小写不一致的以大写金额为准\s*[)）]\s*的报价",
        source_text,
    )
    if price_amount_match:
        source_quote = _clean_requirement_text(price_amount_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "响应函：须填写报价金额（人民币大写和RMB小写），大小写不一致以大写为准。",
                source_quote,
            )
        )

    project_manager_match = re.search(
        r"本项目拟派项目负责人姓名：\s*，身份证\s*号：\s*。",
        source_text,
    )
    if project_manager_match:
        source_quote = _clean_requirement_text(project_manager_match.group(0))
        guarded_items.append(
            (
                "qualification",
                "响应函：须填写本项目拟派项目负责人姓名、身份证号。",
                source_quote,
            )
        )
    duration_match = re.search(r"工期\s*[(（]服务期[)）]\s*个日历天[。；;]?", source_text)
    if duration_match:
        source_quote = _clean_requirement_text(duration_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "响应函：须填写工期(服务期)日历天。",
                source_quote,
            )
        )
    performance_bond_commitment_match = re.search(
        r"一旦我方成为成交人，我方保证按交易文件要求向贵方递交经贵方认可的履约担保[。；;]?"
        r"\s*在我方报价低于风险控制价的情况下，我方将按照规定以保函的形式提交成交价与风险控制\s*价之差额[。；;]?",
        source_text,
    )
    if performance_bond_commitment_match:
        source_quote = _clean_requirement_text(performance_bond_commitment_match.group(0))
        guarded_items.append(
            (
                "mandatory_response",
                "响应函：成交后须递交履约担保；报价低于风险控制价的，须以保函形式提交成交价与风险控制价之差额。",
                source_quote,
            )
        )

    authorization_match = re.search(
        r"授权委托书\s*本授权委托书声明：.*?代理时限.*?"
        r"代理人在代理时间内参加交易活动过程中.*?本人均予以承认。代理人无权转委托。",
        source_text,
    )
    if authorization_match:
        source_quote = _clean_requirement_text(authorization_match.group(0))
        guarded_items.append(
            (
                "format",
                "授权委托书：须提供授权委托书，填写代理人信息和代理时限，并附代理人身份证复印件。",
                source_quote,
            )
        )
    return guarded_items


def _augment_section_candidates_from_text_guards(
    chunks: list[DocumentChunk],
    candidates: list[ComplianceCandidate],
    *,
    extraction_provider: str,
) -> list[ComplianceCandidate]:
    existing_text = "\n".join(_compact_for_match(candidate.requirement_text) for candidate in candidates)
    seen = {candidate.normalized_requirement for candidate in candidates}
    augmented = list(candidates)
    for chunk in chunks:
        text_guard_items = [
            *_qualification_text_guard_items(chunk),
            *_project_overview_text_guard_items(chunk),
            *_deadline_text_guard_items(chunk),
            *_commitment_text_guard_items(chunk),
            *_contract_text_guard_items(chunk),
            *_review_text_guard_items(chunk),
            *_response_form_text_guard_items(chunk),
        ]
        for item_type, requirement, source_quote in text_guard_items:
            if "接受联合体投标" in requirement and "接受联合体投标" in existing_text:
                continue
            guarded_phrase = _compact_for_match(requirement.replace("诚信承诺书：", ""))
            if guarded_phrase and guarded_phrase in existing_text:
                continue
            normalized = _semantic_key(requirement, item_type)
            if normalized in seen:
                continue
            seen.add(normalized)
            risk_level = _risk_level(item_type, requirement)
            is_mandatory = _candidate_is_mandatory(item_type, risk_level, requirement)
            augmented.append(
                ComplianceCandidate(
                    source_chunk_index=chunk.chunk_index,
                    item_type=item_type,
                    requirement_text=requirement,
                    normalized_requirement=normalized,
                    response_suggestion=_response_suggestion(item_type, requirement),
                    risk_level=risk_level,
                    is_mandatory=is_mandatory,
                    confidence_score=Decimal("0.7200"),
                    explanation_json={
                        **_candidate_explanation(
                            item_type=item_type,
                            text=requirement,
                            heading_path=chunk.heading_path,
                            risk_level=risk_level,
                            is_mandatory=is_mandatory,
                            extraction_provider=extraction_provider,
                        ),
                            "source_quote": source_quote[:300],
                            "needs_human_review": True,
                            "review_hint": "模型未覆盖该关键文本条款，由文本守卫补齐，请人工核对。",
                            "classification_reason": "文本守卫识别关键资格、合同或响应格式要求。",
                            "split_reason": "关键文本条款逐条形成可审核要求。",
                            "text_guard": True,
                        },
                    )
            )
    return augmented


def _extract_sectioned_compliance_candidates_serial(
    db: Session,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
    *,
    force_sections: bool = False,
    planned_sections: list[DocumentSemanticSection] | None = None,
) -> tuple[str, list[ComplianceCandidate], list[dict[str, Any]], dict[str, Any]]:
    sections = planned_sections or ensure_document_section_plan(
        db,
        task,
        document,
        version,
        chunks,
        force=force_sections,
    )
    providers: list[str] = []
    all_candidates: list[ComplianceCandidate] = []
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    section_summaries: list[dict[str, Any]] = []
    total_sections = max(1, len(sections))
    _update_matrix_task_progress(
        db,
        task,
        progress=22,
        stage="section_plan_done",
        message=f"章节规划完成，共 {len(sections)} 个语义段。",
        extra={"section_count": len(sections)},
    )

    for section_position, semantic_section in enumerate(sections, start=1):
        section_progress = 25 + int(((section_position - 1) / total_sections) * 65)
        _update_matrix_task_progress(
            db,
            task,
            progress=section_progress,
            stage="section_extract",
            message=f"正在抽取第 {section_position}/{len(sections)} 段：{semantic_section.title}",
            extra={
                "section_index": semantic_section.section_index,
                "section_title": semantic_section.title,
                "section_position": section_position,
                "section_count": len(sections),
            },
        )
        if _is_boilerplate_semantic_section(semantic_section):
            semantic_section.status = "verified"
            section_summaries.append(
                {
                    "semantic_section_id": str(semantic_section.id),
                    "section_index": semantic_section.section_index,
                    "title": semantic_section.title,
                    "page_range": [semantic_section.start_page, semantic_section.end_page],
                    "candidate_count": 0,
                    "accepted_count": 0,
                    "coverage_issue_count": 0,
                    "skipped_reason": "boilerplate_section",
                }
            )
            continue
        current_chunks = _section_chunks(semantic_section, chunks)
        if not current_chunks:
            issues.append(
                _quality_issue(
                    code="SECTION_HAS_NO_CHUNKS",
                    message=f"章节“{semantic_section.title}”页码范围内没有解析分块。",
                    severity="high",
                    semantic_section=semantic_section,
                )
            )
            continue
        current_char_count = sum(len(chunk.content_text or "") for chunk in current_chunks)
        _update_matrix_task_progress(
            db,
            task,
            progress=section_progress,
            stage="section_llm_extract",
            message=(
                f"正在调用模型抽取第 {section_position}/{len(sections)} 段："
                f"{semantic_section.title}（{len(current_chunks)} 个分块，约 {current_char_count} 字）"
            ),
            extra={
                "section_index": semantic_section.section_index,
                "section_title": semantic_section.title,
                "section_position": section_position,
                "section_count": len(sections),
                "chunk_count": len(current_chunks),
                "char_count": current_char_count,
            },
        )
        provider, candidates = _call_section_llm_resilient(
            db,
            task,
            semantic_section,
            current_chunks,
            section_position=section_position,
            total_sections=len(sections),
            progress=section_progress,
        )
        candidates = _augment_section_candidates_from_table_guards(
            current_chunks,
            candidates,
            extraction_provider=f"{provider}:table_guard",
        )
        candidates = _augment_section_candidates_from_text_guards(
            current_chunks,
            candidates,
            extraction_provider=f"{provider}:text_guard",
        )
        providers.append(provider)
        _update_matrix_task_progress(
            db,
            task,
            progress=min(section_progress + 2, 89),
            stage="section_coverage_review",
            message=f"正在复核第 {section_position}/{len(sections)} 段覆盖率：{semantic_section.title}",
            extra={
                "section_index": semantic_section.section_index,
                "section_title": semantic_section.title,
                "section_position": section_position,
                "section_count": len(sections),
                "candidate_count": len(candidates),
            },
        )
        coverage_issues = _review_section_coverage_resilient(
            db,
            task,
            semantic_section,
            current_chunks,
            candidates,
            section_position=section_position,
            total_sections=len(sections),
            progress=min(section_progress + 2, 89),
        )
        issues.extend(coverage_issues)
        _update_matrix_task_progress(
            db,
            task,
            progress=25 + int((section_position / total_sections) * 65),
            stage="section_review",
            message=f"已完成第 {section_position}/{len(sections)} 段覆盖复核：{semantic_section.title}",
            extra={
                "section_index": semantic_section.section_index,
                "section_title": semantic_section.title,
                "section_position": section_position,
                "section_count": len(sections),
                "candidate_count": len(candidates),
                "coverage_issue_count": len(coverage_issues),
            },
        )
        accepted_count = 0
        for candidate in candidates:
            if candidate.normalized_requirement in seen:
                continue
            seen.add(candidate.normalized_requirement)
            all_candidates.append(candidate)
            accepted_count += 1
        section_summaries.append(
            {
                "semantic_section_id": str(semantic_section.id),
                "section_index": semantic_section.section_index,
                "title": semantic_section.title,
                "page_range": [semantic_section.start_page, semantic_section.end_page],
                "candidate_count": len(candidates),
                "accepted_count": accepted_count,
                "coverage_issue_count": len(coverage_issues),
            }
        )

    high_issues = [issue for issue in issues if issue.get("severity") == "high"]
    summary = {
        "document_id": str(document.id),
        "document_version_id": str(version.id),
        "section_count": len(sections),
        "candidate_count": len(all_candidates),
        "issue_count": len(issues),
        "high_issue_count": len(high_issues),
        "sections": section_summaries,
    }
    if high_issues:
        high_issue_codes = {
            str(issue.get("code") or "").strip()
            for issue in high_issues
            if str(issue.get("code") or "").strip()
        }
        gate_code = next(iter(high_issue_codes)) if len(high_issue_codes) == 1 else "QUALITY_GATE_BLOCKED"
        raise ComplianceQualityGateError(
            "覆盖性复核发现严重漏抽或来源质量问题",
            code=gate_code,
            issues=issues,
            summary=summary,
        )
    if not all_candidates:
        raise ComplianceQualityGateError(
            "章节抽取未生成合规矩阵候选项",
            code="NO_COMPLIANCE_CANDIDATES",
            issues=[
                _quality_issue(
                    code="NO_COMPLIANCE_CANDIDATES",
                    message="章节规划和模型抽取均完成，但没有生成任何可入库候选项。",
                    severity="high",
                )
            ],
            summary=summary,
        )
    return ",".join(sorted(set(providers))) or "ai_sectioned", all_candidates, issues, summary


def _matrix_fork_join_max_workers() -> int:
    try:
        configured = int(settings.matrix_fork_join_max_workers)
    except (TypeError, ValueError):
        configured = 4
    return max(1, min(configured, 12))


def _should_use_matrix_fork_join(task: AsyncTask, sections: list[DocumentSemanticSection]) -> bool:
    input_json = task.input_json or {}
    if input_json.get("serial_processing") is True or input_json.get("fork_join") is False:
        return False
    if not settings.matrix_fork_join_enabled:
        return False
    try:
        min_sections = max(1, int(settings.matrix_fork_join_min_sections))
    except (TypeError, ValueError):
        min_sections = 4
    return len(sections) >= min_sections and _matrix_fork_join_max_workers() > 1


def _fork_join_failure_result(
    semantic_section: DocumentSemanticSection,
    section_position: int,
    exc: Exception,
) -> SectionComplianceForkResult:
    if isinstance(exc, ComplianceQualityGateError):
        issues = exc.issues or [
            _quality_issue(
                code=exc.code,
                message=str(exc),
                severity="high",
                semantic_section=semantic_section,
            )
        ]
    else:
        error_code = getattr(exc, "code", "SECTION_FORK_FAILED")
        if isinstance(exc, ValidationError):
            error_code = "LLM_SCHEMA_VALIDATION_FAILED"
        elif isinstance(exc, json.JSONDecodeError):
            error_code = "LLM_JSON_PARSE_FAILED"
        issues = [
            _quality_issue(
                code=error_code,
                message=f"章节“{semantic_section.title}”并发抽取失败：{exc}",
                severity="high",
                semantic_section=semantic_section,
            )
        ]
    return SectionComplianceForkResult(
        section_position=section_position,
        provider="",
        candidates=[],
        issues=issues,
        summary={
            "semantic_section_id": str(semantic_section.id),
            "section_index": semantic_section.section_index,
            "title": semantic_section.title,
            "page_range": [semantic_section.start_page, semantic_section.end_page],
            "candidate_count": 0,
            "accepted_count": 0,
            "coverage_issue_count": len(issues),
            "fork_status": "failed",
            "error_code": issues[0].get("code") if issues else "SECTION_FORK_FAILED",
        },
    )


def _extract_one_section_for_fork_join(
    *,
    task_id: uuid.UUID,
    semantic_section_id: uuid.UUID,
    version_id: uuid.UUID,
    section_position: int,
    total_sections: int,
) -> SectionComplianceForkResult:
    with SessionLocal() as fork_db:
        task = fork_db.get(AsyncTask, task_id)
        semantic_section = fork_db.get(DocumentSemanticSection, semantic_section_id)
        if task is None:
            raise ComplianceGenerationError("矩阵生成任务不存在", code="TASK_NOT_FOUND")
        if semantic_section is None:
            raise ComplianceGenerationError("语义段不存在", code="SEMANTIC_SECTION_NOT_FOUND")

        if _is_boilerplate_semantic_section(semantic_section):
            semantic_section.status = "verified"
            fork_db.commit()
            return SectionComplianceForkResult(
                section_position=section_position,
                provider="",
                candidates=[],
                issues=[],
                summary={
                    "semantic_section_id": str(semantic_section.id),
                    "section_index": semantic_section.section_index,
                    "title": semantic_section.title,
                    "page_range": [semantic_section.start_page, semantic_section.end_page],
                    "candidate_count": 0,
                    "accepted_count": 0,
                    "coverage_issue_count": 0,
                    "skipped_reason": "boilerplate_section",
                    "fork_status": "succeeded",
                },
            )

        chunks = fork_db.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.tenant_id == task.tenant_id,
                DocumentChunk.document_version_id == version_id,
            )
            .order_by(DocumentChunk.chunk_index)
        ).all()
        current_chunks = _section_chunks(semantic_section, list(chunks))
        if not current_chunks:
            issue = _quality_issue(
                code="SECTION_HAS_NO_CHUNKS",
                message=f"章节“{semantic_section.title}”页码范围内没有解析分块。",
                severity="high",
                semantic_section=semantic_section,
            )
            return SectionComplianceForkResult(
                section_position=section_position,
                provider="",
                candidates=[],
                issues=[issue],
                summary={
                    "semantic_section_id": str(semantic_section.id),
                    "section_index": semantic_section.section_index,
                    "title": semantic_section.title,
                    "page_range": [semantic_section.start_page, semantic_section.end_page],
                    "candidate_count": 0,
                    "accepted_count": 0,
                    "coverage_issue_count": 1,
                    "fork_status": "failed",
                    "error_code": "SECTION_HAS_NO_CHUNKS",
                },
            )

        section_progress = 25 + int(((section_position - 1) / max(1, total_sections)) * 65)
        provider, candidates = _call_section_llm_resilient(
            fork_db,
            task,
            semantic_section,
            current_chunks,
            section_position=section_position,
            total_sections=total_sections,
            progress=section_progress,
            progress_updates=False,
        )
        candidates = _augment_section_candidates_from_table_guards(
            current_chunks,
            candidates,
            extraction_provider=f"{provider}:table_guard",
        )
        candidates = _augment_section_candidates_from_text_guards(
            current_chunks,
            candidates,
            extraction_provider=f"{provider}:text_guard",
        )
        coverage_issues = _review_section_coverage_resilient(
            fork_db,
            task,
            semantic_section,
            current_chunks,
            candidates,
            section_position=section_position,
            total_sections=total_sections,
            progress=min(section_progress + 2, 89),
            progress_updates=False,
        )
        semantic_section.status = "verified"
        fork_db.commit()
        return SectionComplianceForkResult(
            section_position=section_position,
            provider=provider,
            candidates=candidates,
            issues=coverage_issues,
            summary={
                "semantic_section_id": str(semantic_section.id),
                "section_index": semantic_section.section_index,
                "title": semantic_section.title,
                "page_range": [semantic_section.start_page, semantic_section.end_page],
                "candidate_count": len(candidates),
                "accepted_count": 0,
                "coverage_issue_count": len(coverage_issues),
                "fork_status": "succeeded",
            },
        )


def _extract_sectioned_compliance_candidates_fork_join(
    db: Session,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
    sections: list[DocumentSemanticSection],
) -> tuple[str, list[ComplianceCandidate], list[dict[str, Any]], dict[str, Any]]:
    total_sections = max(1, len(sections))
    max_workers = min(_matrix_fork_join_max_workers(), total_sections)
    _update_matrix_task_progress(
        db,
        task,
        progress=22,
        stage="section_plan_done",
        message=f"章节规划完成，共 {len(sections)} 个语义段；即将并发抽取。",
        extra={
            "section_count": len(sections),
            "execution_mode": "fork_join",
            "fork_join_max_workers": max_workers,
        },
    )
    _update_matrix_task_progress(
        db,
        task,
        progress=25,
        stage="section_fork_join",
        message=f"正在并发抽取合规条款：0/{len(sections)} 段完成，最大并发 {max_workers}。",
        extra={
            "section_count": len(sections),
            "fork_join_completed": 0,
            "fork_join_total": len(sections),
            "fork_join_max_workers": max_workers,
            "execution_mode": "fork_join",
        },
    )

    results: list[SectionComplianceForkResult] = []
    section_by_id = {section.id: section for section in sections}
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="matrix-section") as executor:
        future_by_section = {
            # Run each section in a *copy* of the current context so structlog's
            # request_id/task_id correlation propagates into the worker thread
            # (contextvars are not inherited by ThreadPoolExecutor threads).
            executor.submit(
                contextvars.copy_context().run,
                _extract_one_section_for_fork_join,
                task_id=task.id,
                semantic_section_id=section.id,
                version_id=version.id,
                section_position=position,
                total_sections=len(sections),
            ): (position, section.id)
            for position, section in enumerate(sections, start=1)
        }
        completed = 0
        heartbeat_count = 0
        pending = set(future_by_section)
        while pending:
            done, pending = wait(
                pending,
                timeout=FORK_JOIN_PROGRESS_HEARTBEAT_SECONDS,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                heartbeat_count += 1
                pending_sections = sorted(
                    (future_by_section[future][0], section_by_id[future_by_section[future][1]])
                    for future in pending
                )
                pending_titles = [
                    f"{position}/{len(sections)} {semantic_section.title}"
                    for position, semantic_section in pending_sections[:max_workers]
                ]
                progress = 25 + int((completed / total_sections) * 65)
                _update_matrix_task_progress(
                    db,
                    task,
                    progress=progress,
                    stage="section_fork_join",
                    message=(
                        f"正在并发抽取合规条款：{completed}/{len(sections)} 段完成，"
                        f"剩余 {len(pending)} 段；正在处理或排队：{'、'.join(pending_titles)}。"
                    ),
                    extra={
                        "section_count": len(sections),
                        "fork_join_completed": completed,
                        "fork_join_total": len(sections),
                        "fork_join_pending": len(pending),
                        "fork_join_pending_sections": [
                            {
                                "section_position": position,
                                "section_index": semantic_section.section_index,
                                "section_title": semantic_section.title,
                            }
                            for position, semantic_section in pending_sections[:max_workers]
                        ],
                        "fork_join_max_workers": max_workers,
                        "fork_join_heartbeat": heartbeat_count,
                        "execution_mode": "fork_join",
                    },
                )
                continue

            for future in done:
                position, section_id = future_by_section[future]
                semantic_section = section_by_id[section_id]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001 - converts child failure into quality issue.
                    result = _fork_join_failure_result(semantic_section, position, exc)
                results.append(result)
                completed += 1
                progress = 25 + int((completed / total_sections) * 65)
                _update_matrix_task_progress(
                    db,
                    task,
                    progress=progress,
                    stage="section_fork_join",
                    message=(
                        f"正在并发抽取合规条款：{completed}/{len(sections)} 段完成，"
                        f"最近完成：{semantic_section.title}"
                    ),
                    extra={
                        "section_index": semantic_section.section_index,
                        "section_title": semantic_section.title,
                        "section_position": position,
                        "section_count": len(sections),
                        "fork_join_completed": completed,
                        "fork_join_total": len(sections),
                        "fork_join_pending": len(pending),
                        "fork_join_max_workers": max_workers,
                        "execution_mode": "fork_join",
                        "last_section_status": result.summary.get("fork_status"),
                    },
                )

    providers: list[str] = []
    issues: list[dict[str, Any]] = []
    all_candidates: list[ComplianceCandidate] = []
    section_summaries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in sorted(results, key=lambda item: item.section_position):
        if result.provider:
            providers.append(result.provider)
        issues.extend(result.issues)
        accepted_count = 0
        for candidate in result.candidates:
            if candidate.normalized_requirement in seen:
                continue
            seen.add(candidate.normalized_requirement)
            all_candidates.append(candidate)
            accepted_count += 1
        section_summary = dict(result.summary)
        section_summary["accepted_count"] = accepted_count
        section_summaries.append(section_summary)

    high_issues = [issue for issue in issues if issue.get("severity") == "high"]
    summary = {
        "document_id": str(document.id),
        "document_version_id": str(version.id),
        "section_count": len(sections),
        "candidate_count": len(all_candidates),
        "issue_count": len(issues),
        "high_issue_count": len(high_issues),
        "sections": section_summaries,
        "execution_mode": "fork_join",
        "fork_join_max_workers": max_workers,
    }
    if high_issues:
        high_issue_codes = {
            str(issue.get("code") or "").strip()
            for issue in high_issues
            if str(issue.get("code") or "").strip()
        }
        gate_code = next(iter(high_issue_codes)) if len(high_issue_codes) == 1 else "QUALITY_GATE_BLOCKED"
        raise ComplianceQualityGateError(
            "覆盖性复核发现严重漏抽或来源质量问题",
            code=gate_code,
            issues=issues,
            summary=summary,
        )
    if not all_candidates:
        raise ComplianceQualityGateError(
            "章节抽取未生成合规矩阵候选项",
            code="NO_COMPLIANCE_CANDIDATES",
            issues=[
                _quality_issue(
                    code="NO_COMPLIANCE_CANDIDATES",
                    message="章节规划和模型抽取均完成，但没有生成任何可入库候选项。",
                    severity="high",
                )
            ],
            summary=summary,
        )
    return _merge_provider_names(providers) or "ai_sectioned_fork_join", all_candidates, issues, summary


def extract_sectioned_compliance_candidates(
    db: Session,
    task: AsyncTask,
    document: Document,
    version: DocumentVersion,
    chunks: list[DocumentChunk],
    *,
    force_sections: bool = False,
) -> tuple[str, list[ComplianceCandidate], list[dict[str, Any]], dict[str, Any]]:
    if not settings.matrix_fork_join_enabled or (task.input_json or {}).get("serial_processing") is True:
        return _extract_sectioned_compliance_candidates_serial(
            db,
            task,
            document,
            version,
            chunks,
            force_sections=force_sections,
        )

    sections = ensure_document_section_plan(
        db,
        task,
        document,
        version,
        chunks,
        force=force_sections,
    )
    if not _should_use_matrix_fork_join(task, sections):
        return _extract_sectioned_compliance_candidates_serial(
            db,
            task,
            document,
            version,
            chunks,
            force_sections=force_sections,
            planned_sections=sections,
        )
    return _extract_sectioned_compliance_candidates_fork_join(db, task, document, version, chunks, sections)


def extract_compliance_candidates(
    db: Session,
    task: AsyncTask,
    chunks: list[DocumentChunk],
) -> tuple[str, list[ComplianceCandidate]]:
    provider, candidates = _call_llm(db, task, chunks)
    if not candidates:
        raise ComplianceGenerationError("模型未返回合规矩阵候选项", code="NO_COMPLIANCE_CANDIDATES")
    return provider, candidates


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


SYSTEM_MATRIX_MODIFY_REASONS = {
    "重新生成合规矩阵候选项",
    "强制重新生成合规矩阵，旧候选项自动淘汰",
}


def _is_human_touched_compliance_item(item: ComplianceItem) -> bool:
    if item.status == "confirmed":
        return True
    if item.source_create_method in {"manual_selection", "similar_candidate"}:
        return True
    if item.selected_text:
        return True
    if item.modified_by is not None and (item.modify_reason or "") not in SYSTEM_MATRIX_MODIFY_REASONS:
        return True
    return False


def _source_create_method(explanation_json: dict[str, Any], default: str) -> str:
    provider = str(explanation_json.get("extraction_provider") or "").strip()
    if not provider:
        return default
    if "table_guard" in provider:
        return "table_guard"
    if "text_guard" in provider:
        return "text_guard"
    if provider == "rules":
        return "rule"
    if ":" in provider:
        return "ai_sectioned"
    return provider[:32]


@observed_task("matrix_generate")
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

    document: Document | None = None
    version: DocumentVersion | None = None
    document_id_for_report: uuid.UUID | None = None
    version_id_for_report: uuid.UUID | None = None
    write_started = False
    try:
        document, version = _select_document_version(db, task)
        document_id_for_report = document.id
        version_id_for_report = version.id
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

        provider, candidates, quality_issues, quality_summary = extract_sectioned_compliance_candidates(
            db,
            task,
            document,
            version,
            list(chunks),
            force_sections=bool((task.input_json or {}).get("force")),
        )
        chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
        created_count = 0
        updated_count = 0
        skipped_count = 0
        superseded_count = 0

        write_started = True
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
                if _is_human_touched_compliance_item(item):
                    skipped_count += 1
                    continue
                item.status = "superseded"
                item.deleted_at = now
                item.modified_by = task.created_by
                item.modified_at = now
                item.modify_reason = "强制重新生成合规矩阵，旧候选项自动淘汰"
                superseded_count += 1

        current_candidate_keys = {candidate.normalized_requirement for candidate in candidates}

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
            source_quote = str(candidate.explanation_json.get("source_quote") or "").strip()
            evidence_text = source_quote or chunk.content_text
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
                        dedup_key=candidate.normalized_requirement[:160],
                        response_suggestion=candidate.response_suggestion,
                        evidence_text=evidence_text,
                        explanation_json=candidate.explanation_json,
                        source_create_method=_source_create_method(candidate.explanation_json, "rule"),
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
                if _is_human_touched_compliance_item(existing):
                    skipped_count += 1
                    continue
                existing.source_chunk_id = chunk.id
                existing.source_page_no = chunk.page_no
                existing.item_type = candidate.item_type
                existing.requirement_text = candidate.requirement_text
                existing.dedup_key = candidate.normalized_requirement[:160]
                existing.response_suggestion = candidate.response_suggestion
                existing.evidence_text = evidence_text
                existing.explanation_json = candidate.explanation_json
                existing.source_create_method = _source_create_method(candidate.explanation_json, "rule")
                existing.status = "pending_confirm"
                existing.deleted_at = None
                existing.risk_level = candidate.risk_level
                existing.is_mandatory = candidate.is_mandatory
                existing.is_batch_confirm_allowed = is_batch_confirm_allowed
                existing.confidence_score = candidate.confidence_score
                existing.modified_by = task.created_by
                existing.modified_at = datetime.now(UTC)
                existing.modify_reason = "重新生成合规矩阵候选项"
                updated_count += 1

        stale_items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == task.tenant_id,
                ComplianceItem.project_id == task.project_id,
                ComplianceItem.section_id == task.section_id,
                ComplianceItem.source_version_id == version.id,
                ComplianceItem.deleted_at.is_(None),
                ComplianceItem.normalized_requirement.not_in(current_candidate_keys),
            )
        ).all()
        for item in stale_items:
            if _is_human_touched_compliance_item(item):
                skipped_count += 1
                continue
            item.status = "superseded"
            item.deleted_at = now
            item.modified_by = task.created_by
            item.modified_at = now
            item.modify_reason = "强制重新生成合规矩阵，旧候选项自动淘汰"
            superseded_count += 1

        quality_summary.update(
            {
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "superseded_count": superseded_count,
                "provider": provider,
            }
        )
        report = _write_quality_report(
            db,
            task,
            document,
            version,
            status="passed",
            issues=quality_issues,
            summary=quality_summary,
        )
        task.status = "succeeded"
        task.progress = 100
        task.output_json = {
            "provider": provider,
            "document_id": str(document.id),
            "document_version_id": str(version.id),
            "execution_mode": quality_summary.get("execution_mode", "serial"),
            "fork_join_max_workers": quality_summary.get("fork_join_max_workers"),
            "candidate_count": len(candidates),
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "superseded_count": superseded_count,
            "quality_report_id": str(report.id),
            "section_count": quality_summary.get("section_count"),
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
        if write_started or not db.is_active:
            db.rollback()
        error_code = getattr(exc, "code", "COMPLIANCE_GENERATION_FAILED")
        if isinstance(exc, ValidationError):
            error_code = "LLM_SCHEMA_VALIDATION_FAILED"
        elif isinstance(exc, json.JSONDecodeError):
            error_code = "LLM_JSON_PARSE_FAILED"
        issues: list[dict[str, Any]]
        summary: dict[str, Any]
        if isinstance(exc, ComplianceQualityGateError):
            issues = exc.issues
            summary = exc.summary
        else:
            issues = [
                _quality_issue(
                    code=error_code,
                    message=str(exc),
                    severity="high",
                )
            ]
            summary = {
                "document_id": str(document_id_for_report) if document_id_for_report else None,
                "document_version_id": str(version_id_for_report) if version_id_for_report else None,
            }
        if document_id_for_report is not None and version_id_for_report is not None:
            document = db.get(Document, document_id_for_report)
            version = db.get(DocumentVersion, version_id_for_report)
        if document is not None and version is not None:
            _write_quality_report(
                db,
                task,
                document,
                version,
                status="blocked",
                issues=issues,
                summary=summary,
            )
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


@observed_task("section_compliance_extract")
def execute_section_compliance_extract_task(
    db: Session,
    task_id: uuid.UUID | str,
) -> dict[str, str | int]:
    task_uuid = _coerce_task_id(task_id)
    task = db.get(AsyncTask, task_uuid)
    if task is None or task.task_type != "section_compliance_extract":
        raise ComplianceGenerationError("章节合规抽取任务不存在", code="TASK_NOT_FOUND")

    now = datetime.now(UTC)
    task.status = "running"
    task.started_at = task.started_at or now
    task.progress = 20
    db.commit()

    document: Document | None = None
    version: DocumentVersion | None = None
    document_id_for_report: uuid.UUID | None = None
    version_id_for_report: uuid.UUID | None = None
    write_started = False
    try:
        semantic_section_id = (task.input_json or {}).get("semantic_section_id")
        if not semantic_section_id:
            raise ComplianceGenerationError("缺少语义段 ID", code="SEMANTIC_SECTION_ID_REQUIRED")
        semantic_section = db.get(DocumentSemanticSection, uuid.UUID(str(semantic_section_id)))
        if semantic_section is None or semantic_section.tenant_id != task.tenant_id:
            raise ComplianceGenerationError("语义段不存在", code="SEMANTIC_SECTION_NOT_FOUND")
        document = db.get(Document, semantic_section.document_id)
        version = db.get(DocumentVersion, semantic_section.document_version_id)
        if document is None or version is None:
            raise ComplianceGenerationError("语义段关联文档不存在", code="DOCUMENT_NOT_FOUND")
        document_id_for_report = document.id
        version_id_for_report = version.id

        chunks = db.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.tenant_id == task.tenant_id,
                DocumentChunk.document_version_id == version.id,
            )
            .order_by(DocumentChunk.chunk_index)
        ).all()
        current_chunks = _section_chunks(semantic_section, list(chunks))
        if not current_chunks:
            raise ComplianceQualityGateError(
                "语义段页码范围内没有解析分块",
                code="SECTION_HAS_NO_CHUNKS",
                issues=[
                    _quality_issue(
                        code="SECTION_HAS_NO_CHUNKS",
                        message=f"章节“{semantic_section.title}”页码范围内没有解析分块。",
                        severity="high",
                        semantic_section=semantic_section,
                    )
                ],
                summary={"semantic_section_id": str(semantic_section.id)},
            )

        provider, candidates = _call_section_llm(db, task, semantic_section, current_chunks)
        candidates = _augment_section_candidates_from_table_guards(
            current_chunks,
            candidates,
            extraction_provider=f"{provider}:table_guard",
        )
        issues = _review_section_coverage(db, task, semantic_section, current_chunks, candidates)
        high_issues = [issue for issue in issues if issue.get("severity") == "high"]
        if high_issues:
            raise ComplianceQualityGateError(
                "单段覆盖性复核发现严重漏抽",
                code="QUALITY_GATE_BLOCKED",
                issues=issues,
                summary={"semantic_section_id": str(semantic_section.id), "candidate_count": len(candidates)},
            )

        chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
        created_count = 0
        updated_count = 0
        skipped_count = 0
        superseded_count = 0
        section_marker = str(semantic_section.id)
        write_started = True
        stale_items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.tenant_id == task.tenant_id,
                ComplianceItem.project_id == task.project_id,
                ComplianceItem.section_id == task.section_id,
                ComplianceItem.source_version_id == version.id,
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
        for item in stale_items:
            if (item.explanation_json or {}).get("semantic_section_id") != section_marker:
                continue
            if _is_human_touched_compliance_item(item):
                skipped_count += 1
                continue
            item.status = "superseded"
            item.deleted_at = now
            item.modified_by = task.created_by
            item.modified_at = now
            item.modify_reason = "强制重新生成合规矩阵，旧候选项自动淘汰"
            superseded_count += 1

        seen: set[str] = set()
        for candidate in candidates:
            if candidate.normalized_requirement in seen:
                continue
            seen.add(candidate.normalized_requirement)
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
            is_batch_confirm_allowed = candidate.risk_level != "high" and not candidate.is_mandatory
            source_quote = str(candidate.explanation_json.get("source_quote") or "").strip()
            evidence_text = source_quote or chunk.content_text
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
                        dedup_key=candidate.normalized_requirement[:160],
                        response_suggestion=candidate.response_suggestion,
                        evidence_text=evidence_text,
                        explanation_json=candidate.explanation_json,
                        source_create_method=_source_create_method(candidate.explanation_json, "ai_sectioned"),
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
                if _is_human_touched_compliance_item(existing):
                    skipped_count += 1
                    continue
                existing.source_chunk_id = chunk.id
                existing.source_page_no = chunk.page_no
                existing.item_type = candidate.item_type
                existing.requirement_text = candidate.requirement_text
                existing.dedup_key = candidate.normalized_requirement[:160]
                existing.response_suggestion = candidate.response_suggestion
                existing.evidence_text = evidence_text
                existing.explanation_json = candidate.explanation_json
                existing.source_create_method = _source_create_method(candidate.explanation_json, "ai_sectioned")
                existing.status = "pending_confirm"
                existing.deleted_at = None
                existing.risk_level = candidate.risk_level
                existing.is_mandatory = candidate.is_mandatory
                existing.is_batch_confirm_allowed = is_batch_confirm_allowed
                existing.confidence_score = candidate.confidence_score
                existing.modified_by = task.created_by
                existing.modified_at = datetime.now(UTC)
                existing.modify_reason = "重新生成合规矩阵候选项"
                updated_count += 1

        summary = {
            "provider": provider,
            "semantic_section_id": str(semantic_section.id),
            "candidate_count": len(candidates),
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "superseded_count": superseded_count,
        }
        report = _write_quality_report(
            db,
            task,
            document,
            version,
            status="passed",
            issues=issues,
            summary=summary,
        )
        task.status = "succeeded"
        task.progress = 100
        task.output_json = {**summary, "quality_report_id": str(report.id)}
        task.finished_at = datetime.now(UTC)
        db.commit()
        return {"status": "succeeded", **summary}
    except Exception as exc:
        if write_started or not db.is_active:
            db.rollback()
        error_code = getattr(exc, "code", "SECTION_COMPLIANCE_EXTRACT_FAILED")
        if isinstance(exc, ValidationError):
            error_code = "LLM_SCHEMA_VALIDATION_FAILED"
        elif isinstance(exc, json.JSONDecodeError):
            error_code = "LLM_JSON_PARSE_FAILED"
        if isinstance(exc, ComplianceQualityGateError):
            issues = exc.issues
            summary = exc.summary
        else:
            issues = [_quality_issue(code=error_code, message=str(exc), severity="high")]
            summary = {}
        if document_id_for_report is not None and version_id_for_report is not None:
            document = db.get(Document, document_id_for_report)
            version = db.get(DocumentVersion, version_id_for_report)
        if document is not None and version is not None:
            _write_quality_report(
                db,
                task,
                document,
                version,
                status="blocked",
                issues=issues,
                summary=summary,
            )
        task.status = "failed"
        task.progress = 100
        task.error_code = error_code
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        db.commit()
        return {"status": "failed", "error_code": error_code}
