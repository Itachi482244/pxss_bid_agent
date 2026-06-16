"""从招标/磋商文件「响应文件组成格式」章抽取格式表单模板，识别填空位并用项目/企业事实填充。

设计原则（与 tender_directory.py 一致）：
  · 纯函数、无 I/O / 无 DB，输入线性正文文本，输出结构化模板与填充结果，便于单测与复用。
  · 不臆造内容：填空位映射不到事实时，保留可见占位符 `［待填:字段］`，由人工补齐。

数据流：
  招标正文 → extract_format_templates() → {模板键: FormTemplate(含 slots)}
           → fill_template(模板, facts) → FilledTemplate(填好的行 + 未填清单)

填空位（slot）来源于三种书面线索（招标 .doc 经解析器拍平后，原下划线/空格塌缩为单空格）：
  (a) 空档后紧跟括号提示：`致 （采购人、采购代理机构）` → 字段＝采购人
  (b) 标签＋冒号＋空档：`采购代理编号： ` `地址： ` → 字段＝冒号前标签
  (c) 空档＋量词：`副本 份` `第 包` `截止时间起 日内` → 字段由量词语义决定
  (d) 日期：`日期： 年 月 日` → 三段年月日
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ----------------------------------------------------------------------------
# 数据结构
# ----------------------------------------------------------------------------


@dataclass
class FormSlot:
    """模板中的一个填空位。"""

    field_key: str  # 规范化字段键，如 'purchaser' / 'supplier_name' / 'date'
    label: str  # 人类可读标签（用于占位提示与 UI）
    raw_hint: str  # 触发该 slot 的原始线索文本


@dataclass
class FormTemplate:
    """一个格式表单模板（如『磋商响应声明』『法定代表人授权委托书』）。"""

    key: str  # 稳定键，如 'bid_commitment' / 'authorization_letter'
    title: str  # 原文标题
    attachment_label: str | None  # 若为附件（附件1-1 等），记录其编号
    body: str  # 模板原文（含填空位线索）
    slots: list[FormSlot] = field(default_factory=list)


@dataclass
class FilledLine:
    text: str
    has_unfilled: bool


@dataclass
class FilledTemplate:
    key: str
    title: str
    lines: list[str]
    unfilled: list[FormSlot] = field(default_factory=list)
    seal_required: bool = False  # 是否需盖单位公章 / 法人签字


# ----------------------------------------------------------------------------
# 字段规范化：把括号提示 / 冒号标签 / 量词 映射到规范字段键
# ----------------------------------------------------------------------------

# 规范字段键 → 用于在 facts 中查值的同义标签集合
FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "purchaser": ("采购人", "采购人、采购代理机构", "采购人名称", "招标人"),
    "project_name": ("项目名称",),
    "agent_code": ("采购代理编号", "采购编号", "项目编号", "招标编号"),
    "signatory": ("签字代表", "姓名、职务", "授权代表"),
    "supplier_name": ("供应商名称", "投标人名称", "供应商", "投标人"),
    "copies_duplicate": ("副本", "副本份数"),
    "package_no": ("包号", "标段", "分包"),
    "bid_validity_days": ("响应文件有效期", "报价有效期", "投标有效期", "有效期"),
    "address": ("地址", "注册地址", "通讯地址"),
    "postcode": ("邮编", "邮政编码"),
    "phone": ("电话", "联系电话"),
    "email": ("电子邮箱", "邮箱", "电子邮件"),
    "legal_representative": ("法定代表人", "单位负责人", "法人"),
    "agent_person": ("代理人", "委托代理人", "授权的代理人"),
    "social_credit_code": ("统一社会信用代码", "信用代码"),
    "gender": ("性别",),
    "age": ("年龄",),
    "title_position": ("职务",),
    "delegation_period": ("委托期限",),
    "date": ("日期", "签署日期"),
}

# 括号提示文本 → 字段键（精确/包含匹配）
_PAREN_HINT_TO_FIELD: list[tuple[tuple[str, ...], str]] = [
    (("采购人", "采购代理机构"), "purchaser"),
    (("项目名称", "采购代理编号"), "project_name"),  # 「项目名称、采购代理编号」复合提示
    (("供应商名称",), "supplier_name"),
    (("姓名、职务", "姓名", "职务"), "signatory"),
]

# 冒号标签 → 字段键
_LABEL_TO_FIELD: list[tuple[str, str]] = [
    ("采购代理编号", "agent_code"),
    ("地址", "address"),
    ("邮编", "postcode"),
    ("电话", "phone"),
    ("电子邮箱", "email"),
    ("统一社会信用代码", "social_credit_code"),
    ("注册地址", "address"),
    ("供应商名称", "supplier_name"),
    ("委托期限", "delegation_period"),
    ("性别", "gender"),
    ("年龄", "age"),
    ("职务", "title_position"),
    ("姓名", "signatory"),
]

_LABEL_LOOKUP = {label: fkey for label, fkey in _LABEL_TO_FIELD}


def _longest_suffix_label(seg: str) -> str | None:
    """在已知标签中找 seg 的最长后缀匹配（『注册地址』优先于『地址』）。"""
    best: str | None = None
    for label in _LABEL_LOOKUP:
        if seg.endswith(label) and (best is None or len(label) > len(best)):
            best = label
    return best


_OCCUPANCY = "［待填:{label}］"  # 未填占位符（全角方括号，便于人工搜索）

# 模板边界：第五章「响应文件组成格式」/「响应文件组成」标题
_FORMAT_CHAPTER_RE = re.compile(r"(响应文件组成格式|响应文件组成|投标文件格式|响应文件格式)")
# 单个格式条目标题：一、xxx / 附件N-M xxx
_ITEM_TITLE_RE = re.compile(r"^\s*([一二三四五六七八九十]+)\s*[、.]\s*(.+)$")
_ATTACH_TITLE_RE = re.compile(r"^\s*(附件\s*[0-9]+\s*[-—－]\s*[0-9]+)\s*(.*)$")

# 已知格式条目标题 → 稳定模板键
_TITLE_TO_KEY: list[tuple[tuple[str, ...], str]] = [
    (("磋商响应声明", "投标声明", "响应声明", "投标函", "响应函"), "bid_commitment"),
    (("法定代表人身份证明", "法人身份证明", "单位负责人身份证明"), "legal_representative_identity"),
    (("法定代表人授权委托书", "授权委托书", "法人授权"), "authorization_letter"),
]


def _title_to_key(title: str) -> str | None:
    for keywords, key in _TITLE_TO_KEY:
        if any(k in title for k in keywords):
            return key
    return None


# ----------------------------------------------------------------------------
# 抽取：定位格式章并切分出各条目模板
# ----------------------------------------------------------------------------


def _locate_format_region(lines: list[str]) -> tuple[int, int]:
    """返回格式章正文区间 [start, end)；定位『一、磋商响应声明』这类条目的**第二次**出现。

    招标文件里『响应文件组成』通常出现两次：先是目录式列举（仅标题），再是带模板正文的
    格式章。我们要的是后者——以『致 （采购人』这类模板特征句锚定。
    """
    anchor = -1
    for i, ln in enumerate(lines):
        if "致" in ln and ("采购人" in ln or "采购代理机构" in ln):
            anchor = i
            break
    if anchor < 0:
        return -1, -1
    # 向上回溯到最近的『一、磋商响应声明』标题
    start = anchor
    for j in range(anchor, max(anchor - 8, -1), -1):
        if _ITEM_TITLE_RE.match(lines[j]) or _title_to_key(lines[j]):
            start = j
            break
    return start, len(lines)


def _norm_title(s: str) -> str:
    """归一化标题用于锚点比对：去空白、去首部序号前缀。"""
    s = re.sub(r"\s+", "", s or "")
    s = re.sub(r"^[一二三四五六七八九十]+[、.]", "", s)
    return s


def _is_chapter_boundary(line: str, top_titles: set[str]) -> str | None:
    """若该行是章级条目边界（命中已知目录标题），返回规范化标题；否则 None。

    关键：用『已推导出的目录标题集合』判定，从而不会把声明内部的『一、二、…』分句
    误判为新章（它们是长句、不在目录标题集合里）。
    """
    m = _ITEM_TITLE_RE.match(line)
    if not m:
        return None
    norm = _norm_title(m.group(2))
    if not top_titles:
        # 无目录锚点时退化：仅接受『短名词短语』（不含句号、长度≤25）为章边界
        if "。" not in norm and len(norm) <= 25:
            return norm
        return None
    return norm if norm in top_titles else None


def _split_items(
    lines: list[str], start: int, end: int, top_titles: set[str]
) -> list[tuple[str, str | None, list[str]]]:
    """边界驱动切分格式区为若干 (title, attachment_label, body_lines)。

    边界 = 章级目录标题（命中 top_titles）或 附件N-M 标记；二者之间整段归入当前条目，
    因此声明内部的『一、…七、』分句、联系方式、盖章、日期都会完整保留在 body。
    """
    items: list[tuple[str, str | None, list[str]]] = []
    cur_title: str | None = None
    cur_attach: str | None = None
    cur_body: list[str] = []

    def flush() -> None:
        if cur_title is not None:
            items.append((cur_title, cur_attach, cur_body.copy()))

    for k in range(start, end):
        ln = lines[k].strip()
        if not ln:
            continue
        m_at = _ATTACH_TITLE_RE.match(ln)
        if m_at:
            flush()
            cur_attach = re.sub(r"\s+", "", m_at.group(1))
            tail = m_at.group(2).strip()
            cur_title = tail or cur_attach
            cur_body = []
            continue
        chap = _is_chapter_boundary(ln, top_titles)
        if chap is not None:
            flush()
            cur_attach = None
            m_it = _ITEM_TITLE_RE.match(ln)
            cur_title = m_it.group(2).strip() if m_it else ln
            cur_body = []
            continue
        cur_body.append(ln)
    flush()
    return items


# ----------------------------------------------------------------------------
# 填空位识别
# ----------------------------------------------------------------------------

# 空档：解析后塌缩为 1+ 空格（招标 .doc 原为下划线/制表）。用前后线索定位。
_GAP = r"[ \u3000]+"


def _detect_slots(body: str) -> list[FormSlot]:
    slots: list[FormSlot] = []
    seen: set[str] = set()

    def add(field_key: str, label: str, hint: str) -> None:
        token = f"{field_key}:{hint}"
        if token in seen:
            return
        seen.add(token)
        slots.append(FormSlot(field_key=field_key, label=label, raw_hint=hint))

    # (a) 空档 + 括号提示： `… （项目名称） …`（结合空档前上下文消歧同形提示）
    for m in re.finditer(rf"{_GAP}[（(]([^）)]+)[）)]", body):
        hint = m.group(1).strip()
        ctx = body[max(0, m.start() - 8) : m.start()]
        fkey = _paren_hint_field(hint, ctx)
        if fkey:
            add(fkey, _hint_label(fkey, hint), f"{ctx}|{hint}")

    # (b) 标签：空档（冒号后留空）
    for label, fkey in _LABEL_TO_FIELD:
        if re.search(rf"{label}[：:]{_GAP}", body) or re.search(rf"{label}[：:]$", body, re.M):
            add(fkey, label, f"{label}：")

    # (c) 量词线索
    if re.search(rf"副本{_GAP}份", body):
        add("copies_duplicate", "副本份数", "副本 份")
    if re.search(rf"第{_GAP}[包标]", body):
        add("package_no", "包号", "第 包")
    if re.search(rf"(截止时间起|有效期){_GAP}日", body):
        add("bid_validity_days", "报价有效期(天)", "起 日内")

    # (d) 日期： 年 月 日
    if re.search(r"日期[：:].*年.*月.*日", body) or re.search(r"年\s*月\s*日", body):
        add("date", "日期", "年 月 日")

    return slots


def _paren_hint_field(hint: str, ctx: str = "") -> str | None:
    """由括号提示 + 空档前上下文判定字段。

    同形提示『（姓名、职务）』在不同语境指代不同角色：
      本人…（姓名、职务）→ 法定代表人；现授权…（姓名、职务）→ 代理人；签字代表…→ 签字代表。
    """
    if ("姓名" in hint or "职务" in hint) and "供应商名称" not in hint:
        if "本人" in ctx:
            return "legal_representative"
        if "授权" in ctx:
            return "agent_person"
        if "签字代表" in ctx:
            return "signatory"
        return "signatory"
    for keywords, fkey in _PAREN_HINT_TO_FIELD:
        if any(k in hint for k in keywords):
            return fkey
    return None


def _hint_label(fkey: str, hint: str) -> str:
    syn = FIELD_SYNONYMS.get(fkey, ())
    return syn[0] if syn else hint


# ----------------------------------------------------------------------------
# 对外：抽取所有模板
# ----------------------------------------------------------------------------


def extract_format_templates(
    text: str, top_titles: list[str] | None = None
) -> dict[str, FormTemplate]:
    """从招标正文抽取格式表单模板，键为稳定模板键或 'attach:<编号>' / 'item:<标题>'。

    top_titles：已推导出的章级目录标题（来自 tender_directory）。传入后切分更稳健，
    可避免把声明内部的『一、二、…』分句误判为新章。
    """
    lines = text.splitlines()
    start, end = _locate_format_region(lines)
    if start < 0:
        return {}
    norm_top = {_norm_title(t) for t in (top_titles or []) if t}
    out: dict[str, FormTemplate] = {}
    for title, attach, body_lines in _split_items(lines, start, end, norm_top):
        body = "\n".join(body_lines).strip()
        if not body and not attach:
            continue
        # 附件标题常与编号分两行（『附件1-2』/『法定代表人授权委托书』），
        # 此时取 body 首行作为语义标题用于定键与展示。
        effective_title = title
        if attach and (title == attach or not title) and body_lines:
            effective_title = body_lines[0].strip()
        key = _title_to_key(effective_title)
        if not key:
            key = f"attach:{attach}" if attach else f"item:{effective_title}"
        slots = _detect_slots(body)
        out[key] = FormTemplate(
            key=key,
            title=effective_title,
            attachment_label=attach,
            body=body,
            slots=slots,
        )
    return out


# ----------------------------------------------------------------------------
# 填充
# ----------------------------------------------------------------------------


def _lookup_fact(field_key: str, facts: dict[str, Any]) -> str | None:
    """在 facts 中查字段值：先按规范键，再按同义标签。"""
    if field_key in facts and _norm(facts[field_key]):
        return _norm(facts[field_key])
    for label in FIELD_SYNONYMS.get(field_key, ()):  # 同义标签
        if label in facts and _norm(facts[label]):
            return _norm(facts[label])
    return None


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def fill_template(template: FormTemplate, facts: dict[str, Any]) -> FilledTemplate:
    """用 facts 填充模板：括号提示后的空档替换为值；冒号后留空补值；未知留占位。"""
    body = template.body
    unfilled: list[FormSlot] = []

    # 收集每个 slot 的值
    resolved: dict[str, str] = {}
    for slot in template.slots:
        val = _lookup_fact(slot.field_key, facts)
        if val is None:
            unfilled.append(slot)
            resolved[slot.field_key] = _OCCUPANCY.format(label=slot.label)
        else:
            resolved[slot.field_key] = val

    text = body

    # (a) 括号提示型：在『空档（提示）』的空档处插值（值放在括号前），按上下文消歧
    def repl_paren(m: re.Match[str]) -> str:
        hint = m.group(1).strip()
        ctx = text[max(0, m.start() - 8) : m.start()]
        fkey = _paren_hint_field(hint, ctx)
        if fkey and fkey in resolved:
            return f" {resolved[fkey]} （{hint}）"
        return m.group(0)

    text = re.sub(rf"{_GAP}[（(]([^）)]+)[）)]", repl_paren, text)

    # (b) 标签：冒号锚定单遍扫描，按『最长后缀标签』定字段，避免『地址/注册地址』子串重复填充
    def repl_label(m: re.Match[str]) -> str:
        seg = m.group(1)
        label = _longest_suffix_label(seg)
        if not label:
            return m.group(0)
        fkey = _LABEL_LOOKUP[label]
        if fkey not in resolved:
            return m.group(0)
        return f"{seg}{m.group(2)}{resolved[fkey]}"

    text = re.sub(r"([\u4e00-\u9fff]{2,12})([：:])[ \u3000]*", repl_label, text)

    # (c) 量词
    if "copies_duplicate" in resolved:
        text = re.sub(rf"(副本){_GAP}(份)", rf"\g<1>{resolved['copies_duplicate']}\g<2>", text)
    if "package_no" in resolved:
        text = re.sub(rf"(第){_GAP}([包标])", rf"\g<1>{resolved['package_no']}\g<2>", text)
    if "bid_validity_days" in resolved:
        text = re.sub(
            rf"(截止时间起|有效期)({_GAP})(日)",
            rf"\g<1>{resolved['bid_validity_days']}\g<3>",
            text,
        )

    # (d) 日期
    if "date" in resolved and resolved["date"] and not resolved["date"].startswith("［待填"):
        ymd = _parse_ymd(resolved["date"])
        if ymd:
            y, mo, d = ymd
            text = re.sub(r"日期[：:]\s*年\s*月\s*日", f"日期：{y}年{mo}月{d}日", text)
            text = re.sub(r"于\s*年\s*月\s*日", f"于{y}年{mo}月{d}日", text)

    seal = ("盖单位公章" in body) or ("盖单位章" in body) or ("盖公章" in body)
    return FilledTemplate(
        key=template.key,
        title=template.title,
        lines=[ln for ln in text.splitlines()],
        unfilled=unfilled,
        seal_required=seal,
    )


def _parse_ymd(s: str) -> tuple[str, str, str] | None:
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", s)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None
