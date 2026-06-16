"""从招标/磋商文件正文推导"投标文件目录结构"。

设计目标（路线C·采购方式驱动的通用引擎）：
  L2 权威骨架 —— 解析"投标文件格式 / 响应文件组成 / 投标文件组成"章，得到章节、顺序、命名、附件；
  L1 信号校准 —— 抽取采购方式、保证金、有效期、联合体、偏离表等开关信号；
  （L0 基线兜底 / L3 人工确认 在调用方实现。）

本模块是纯函数、无 I/O、无 DB 依赖，便于：
  - 原型阶段直接喂转好的招标文件全文文本；
  - 生产阶段喂 DocumentChunk 的 heading_path + content_text 拼接结果。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 中文数字
# ---------------------------------------------------------------------------
_CN_NUM = {c: i for i, c in enumerate("零一二三四五六七八九十", start=0)}


def _cn_to_int(s: str) -> int | None:
    """支持 一~二十 的简单中文数字解析（目录层级足够用）。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CN_NUM.get(left, 1) if left else 1
        ones = _CN_NUM.get(right, 0) if right else 0
        return tens * 10 + ones
    return _CN_NUM.get(s)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class OutlineNode:
    order: int
    title: str
    level: int = 1
    source: str = "format_chapter"  # format_chapter | attachment | signal | baseline
    children: list["OutlineNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "title": self.title,
            "level": self.level,
            "source": self.source,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class DirectoryOutline:
    procurement_method: str  # tender | consultation | inquiry | unknown
    document_term: str  # 投标文件 | 响应文件
    signals: dict[str, Any]
    nodes: list[OutlineNode]
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "procurement_method": self.procurement_method,
            "document_term": self.document_term,
            "signals": self.signals,
            "nodes": [n.to_dict() for n in self.nodes],
            "diagnostics": self.diagnostics,
        }


# ---------------------------------------------------------------------------
# 章节定位
# ---------------------------------------------------------------------------
_CHAPTER_RE = re.compile(r"^\s*第\s*([一二三四五六七八九十]+)\s*章")
_FORMAT_CHAPTER_TITLE_RE = re.compile(
    r"(投标文件格式|响应文件\s*组成|响应文件\s*格式|投标文件\s*组成|投标文件\s*格式)"
)
_ENUM_TRIGGER_RE = re.compile(
    r"(应包含以下部分|应包括以下部分|由以下.*?组成|应当?包括|应包含下列|包含以下内容)"
)
_TOP_ITEM_RE = re.compile(r"^\s*([一二三四五六七八九十]+)\s*[、.．]\s*(.+?)\s*$")
_ATTACH_RE = re.compile(r"^\s*附件\s*(\d+)\s*[-－—.]\s*(\d+)\s*(.*)$")


def _find_composition_region(lines: list[str]) -> tuple[int, int, str]:
    """返回 (枚举行索引, 区域结束索引, 命中策略)。找不到返回 (-1,-1,'')。"""
    # 优先：枚举触发句"应包含以下部分："且其后紧跟"序号、标题"列表
    for i, ln in enumerate(lines):
        if _ENUM_TRIGGER_RE.search(ln):
            # 校验后面确实有 >=2 条 一、二、 列表
            cnt = 0
            for j in range(i + 1, min(i + 12, len(lines))):
                if _TOP_ITEM_RE.match(lines[j]):
                    cnt += 1
            if cnt >= 2:
                return i, _region_end(lines, i), "enum_trigger"
    # 兜底：定位"格式/组成"章标题（取正文中最后一次出现，避开目录页）
    cand = -1
    for i, ln in enumerate(lines):
        if _CHAPTER_RE.match(ln) and _FORMAT_CHAPTER_TITLE_RE.search(ln):
            cand = i
    if cand >= 0:
        return cand, _region_end(lines, cand), "chapter_title"
    return -1, -1, ""


def _region_end(lines: list[str], start: int) -> int:
    """从 start 之后找到下一个『不同章节标题』作为区域结束，否则到文末。"""
    for j in range(start + 1, len(lines)):
        m = _CHAPTER_RE.match(lines[j])
        if m and not _FORMAT_CHAPTER_TITLE_RE.search(lines[j]):
            return j
    return len(lines)


# ---------------------------------------------------------------------------
# 目录解析
# ---------------------------------------------------------------------------
_MAX_ENUM_SKIPS = 3  # 容忍枚举列表中夹杂的个别非匹配行（解析碎片/空行/表格残留）


def _parse_top_level(lines: list[str], enum_idx: int, end_idx: int) -> list[OutlineNode]:
    """从枚举触发句之后，抓取连续递增的『序号、标题』作为一级章节。

    鲁棒性：允许跳过夹在条目间的少量非匹配行（如标题被解析切碎的孤儿片段），
    但在『序号重置』（再次回到更小编号，即进入格式正文区）时立即结束，避免误收
    格式正文里的『一、二、…』内部列举。
    """
    nodes: list[OutlineNode] = []
    expected = 1
    skips = 0
    for j in range(enum_idx + 1, end_idx):
        line = lines[j].strip()
        if not line:
            continue
        m = _TOP_ITEM_RE.match(lines[j])
        if not m:
            if nodes:
                skips += 1
                if skips > _MAX_ENUM_SKIPS:
                    break
            continue
        num = _cn_to_int(m.group(1))
        if num is None:
            continue
        if nodes and num <= nodes[-1].order:
            # 序号重置或回退（进入格式正文区，如再次出现"一、"）→ 结束枚举
            break
        if nodes and num != expected:
            # 向前跳号（疑似漏项）：接受并对齐，不视为重置
            expected = num
        title = _clean_title(m.group(2))
        if not title:
            continue
        nodes.append(OutlineNode(order=num, title=title, level=1, source="format_chapter"))
        expected = num + 1
        skips = 0
    return nodes


def _attach_attachments(
    lines: list[str], region_start: int, end_idx: int, nodes: list[OutlineNode]
) -> int:
    """扫描整个组成区域的『附件P-N 标题』，按 P 挂到第 P 个一级章节下。返回挂载数量。"""
    by_order = {n.order: n for n in nodes}
    attached = 0
    j = region_start
    while j < end_idx:
        m = _ATTACH_RE.match(lines[j])
        if m:
            parent_no = int(m.group(1))
            sub_no = int(m.group(2))
            title = _clean_title(m.group(3))
            if not title:  # 标题在下一非空行
                k = j + 1
                while k < end_idx and not lines[k].strip():
                    k += 1
                if k < end_idx:
                    title = _clean_title(lines[k])
            parent = by_order.get(parent_no)
            if parent is not None and title:
                label = f"附件{parent_no}-{sub_no} {title}"
                if not any(c.title == label for c in parent.children):
                    parent.children.append(
                        OutlineNode(order=sub_no, title=label, level=2, source="attachment")
                    )
                    attached += 1
        j += 1
    return attached


def _clean_title(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[（(]\s*格式\s*[)）]\s*$", "", s).strip()
    s = re.sub(r"[:：。\s]+$", "", s).strip()
    return s


# ---------------------------------------------------------------------------
# 信号抽取（L1 校准）
# ---------------------------------------------------------------------------
def _detect_procurement(text: str) -> tuple[str, str]:
    cons = text.count("磋商")
    tender = text.count("投标") + text.count("招标")
    inquiry = text.count("询价")
    if inquiry > tender and inquiry > cons:
        return "inquiry", "响应文件"
    if cons >= 3 and cons >= tender * 0.3:
        return "consultation", "响应文件"
    if tender > 0:
        return "tender", "投标文件"
    return "unknown", "投标文件"


def _table_pair_value(lines: list[str], label_kw: str, lookahead: int = 3) -> str | None:
    """前附表常被压平成『标签行 + 值行』。给定标签关键词，返回其后若干非空行拼接的值。"""
    for i, ln in enumerate(lines):
        s = ln.strip()
        # 标签行：包含关键词且本身较短（避免命中长正文段落）
        if label_kw in s and len(s) <= len(label_kw) + 8:
            buf: list[str] = []
            for j in range(i + 1, min(i + 1 + lookahead, len(lines))):
                v = lines[j].strip()
                if not v:
                    continue
                buf.append(v)
                if len(buf) >= 2:
                    break
            if buf:
                return " ".join(buf)
    return None


def _extract_signals(text: str) -> dict[str, Any]:
    sig: dict[str, Any] = {}
    lines = text.splitlines()

    # 保证金：优先按前附表键值对判定，跨行兜底
    sec_val = _table_pair_value(lines, "保证金") or ""
    sec_inline = re.search(r"保证金[^。\n]{0,12}(不需要|不要求|无需|免收)", text)
    if re.search(r"(不需要|不要求|无需|免收|■\s*不)", sec_val) or sec_inline:
        sig["bid_security_required"] = False
    elif re.search(r"(投标|磋商|履约)?保证金", text):
        sig["bid_security_required"] = True

    # 联合体：仅在明确表述时给出，避免误报
    if re.search(r"(不接受|不允许)[^。\n]{0,6}联合体", text):
        sig["consortium_allowed"] = False
    elif re.search(r"(接受|允许)[^。\n]{0,6}联合体", text):
        sig["consortium_allowed"] = True

    # 偏离表
    sig["deviation_table_required"] = bool(re.search(r"偏离表", text))

    # 评分索引 / 评分办法
    sig["scoring_index_required"] = bool(re.search(r"评分索引", text))

    # 文件有效期
    m = re.search(r"(响应文件|投标文件)?有效期[^0-9]{0,6}(\d{2,3})\s*日", text)
    if m:
        sig["bid_validity_days"] = int(m.group(2))

    # 份数（正副本）
    if re.search(r"一正两副|正本一份[，,].{0,6}副本两份|一份正本.{0,6}两份副本", text):
        sig["copies"] = "一正两副"

    return sig


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def derive_directory(text: str) -> DirectoryOutline:
    lines = text.splitlines()
    diagnostics: list[str] = []

    method, term = _detect_procurement(text)
    signals = _extract_signals(text)

    enum_idx, end_idx, strategy = _find_composition_region(lines)
    nodes: list[OutlineNode] = []
    if enum_idx < 0:
        diagnostics.append("未定位到『组成/格式』章，需走 L0 基线兜底 + 人工确认")
    else:
        diagnostics.append(f"组成章定位策略={strategy}，区域行 {enum_idx}..{end_idx}")
        nodes = _parse_top_level(lines, enum_idx, end_idx)
        diagnostics.append(f"解析一级章节 {len(nodes)} 个")
        n_attached = _attach_attachments(lines, enum_idx, end_idx, nodes)
        diagnostics.append(f"挂载附件 {n_attached} 个")

    return DirectoryOutline(
        procurement_method=method,
        document_term=term,
        signals=signals,
        nodes=nodes,
        diagnostics=diagnostics,
    )


def render_outline(outline: DirectoryOutline) -> str:
    """把推导结果渲染成可读目录树。"""
    out: list[str] = []
    out.append(f"采购方式：{outline.procurement_method}  文件称谓：{outline.document_term}")
    out.append(f"校准信号：{outline.signals}")
    out.append("-" * 60)
    for n in outline.nodes:
        out.append(f"{n.order}、{n.title}")
        for c in n.children:
            out.append(f"    └─ {c.title}")
    out.append("-" * 60)
    for d in outline.diagnostics:
        out.append(f"· {d}")
    return "\n".join(out)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tender_cangding.txt"
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    print(render_outline(derive_directory(raw)))
