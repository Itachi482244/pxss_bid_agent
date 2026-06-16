"""合规覆盖/自检层：把"投标文件应当包含什么"与"我方现在能满足什么"对齐，产出一张分层自检清单。

定位（L1-L3 合规闭环主轴，确定性覆盖优先）：
  · 这是该应用最核心的产出价值——不是"文笔"，而是"投得出、不废标、不丢冤枉分"。
  · 三层覆盖统一成一个 CoverageReport，便于渲染进 docx 自检清单，也便于前端展示缺口：
      L1 合规格式  —— 必备表单/附件/证照齐全性
      L2 评分覆盖  —— 评分项是否有应答/证据绑定，缺口进入评分索引
      L3 偏离响应  —— 技术/商务条款进入偏离响应表，未知响应保持人工确认

设计原则（与 tender_directory / tender_format_templates 一致）：
  · 纯函数、无 I/O / 无 DB，输入结构化数据，输出覆盖报告，便于单测与复用。
  · 不臆造"已满足"：拿不到企业材料即标 needs_material，核心资格缺失标 disqualifying（废标风险）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.services.tender_format_templates import FormTemplate, fill_template

# ----------------------------------------------------------------------------
# 覆盖模型
# ----------------------------------------------------------------------------


class CoverLayer(str, Enum):
    L1_FORMAT = "L1 合规格式"
    L2_SCORING = "L2 评分覆盖"
    L3_RESPONSE = "L3 偏离响应"


class CoverStatus(str, Enum):
    FILLABLE = "fillable"            # 事实齐，可自动填好
    PARTIAL = "partial"             # 部分字段待补
    NEEDS_MATERIAL = "needs_material"  # 需企业材料/扫描件
    READY = "ready"                 # 已有匹配材料
    MISSING = "missing"             # 缺失（无事实、无材料）
    PENDING = "pending"             # 待人工应答 / 待绑定证据 / 待确认口径


_STATUS_LABEL = {
    CoverStatus.FILLABLE: "可自动填",
    CoverStatus.PARTIAL: "部分待补",
    CoverStatus.NEEDS_MATERIAL: "需上传材料",
    CoverStatus.READY: "材料已备",
    CoverStatus.MISSING: "缺失",
    CoverStatus.PENDING: "待应答",
}

# 视为缺口（需人工处理）的状态
_GAP_STATUSES = {CoverStatus.NEEDS_MATERIAL, CoverStatus.MISSING, CoverStatus.PARTIAL, CoverStatus.PENDING}


@dataclass
class CoverageItem:
    layer: CoverLayer
    title: str               # 要求/条目名（如『法定代表人授权委托书』『附件2-1 营业执照』）
    status: CoverStatus
    detail: str = ""         # 状态说明（待填字段、需何种材料、对应评分点等）
    disqualifying: bool = False  # 是否核心资格/废标项（缺则废标）

    @property
    def status_label(self) -> str:
        return _STATUS_LABEL.get(self.status, self.status.value)


@dataclass
class CoverageReport:
    items: list[CoverageItem] = field(default_factory=list)

    def for_layer(self, layer: CoverLayer) -> list[CoverageItem]:
        return [i for i in self.items if i.layer == layer]

    @property
    def gaps(self) -> list[CoverageItem]:
        """需人工处理的缺口（任意层）。"""
        return [i for i in self.items if i.status in _GAP_STATUSES]

    @property
    def disqualifying_gaps(self) -> list[CoverageItem]:
        """废标风险缺口：核心资格项尚未满足。"""
        return [i for i in self.items if i.disqualifying and i.status in {CoverStatus.MISSING, CoverStatus.NEEDS_MATERIAL}]

    def summary(self) -> dict[str, dict[str, int]]:
        """{层: {状态: 数量}}，便于诊断与前端汇总。"""
        out: dict[str, dict[str, int]] = {}
        for it in self.items:
            bucket = out.setdefault(it.layer.value, {})
            bucket[it.status.value] = bucket.get(it.status.value, 0) + 1
        return out


# ----------------------------------------------------------------------------
# L1：必备表单 + 附件/证照
# ----------------------------------------------------------------------------

# 走表单填充的语义模板键（与装配器保持一致）
_FORM_TEMPLATE_KEYS = ("bid_commitment", "authorization_letter", "legal_representative_identity")

# 附件标题关键词 → (期望材料类别, 是否核心资格/废标项)
_ATTACH_RULES: tuple[tuple[tuple[str, ...], str, bool], ...] = (
    (("营业执照", "主体资格", "法人或者其他组织", "事业单位法人", "身份证"), "营业执照/主体资格证明", True),
    (("资质", "资格证书", "许可证", "等级证书", "安全生产许可"), "资质/许可证书", True),
    (("信用", "失信", "信用中国", "中国政府采购网", "重大违法"), "信用查询截图", True),
    (("社保", "纳税", "完税", "缴纳"), "社保/纳税证明", False),
    (("财务", "审计", "资产负债"), "财务/审计报告", False),
    (("业绩", "合同", "中标通知", "验收"), "业绩合同证明", False),
    (("授权", "委托"), "授权/委托文件", False),
    (("承诺",), "承诺函", False),
)


# 本投标文件内生成的表单/表格（非需上传的证照扫描件），从 L1 材料覆盖中排除
_GENERATED_FORM_HINTS = (
    "报价一览表", "分项报价", "报价明细", "明细表", "一览表",
    "偏离表", "响应表", "最后报价", "响应声明",
)


def _classify_attachment(title: str) -> tuple[str, bool, tuple[str, ...]]:
    """附件标题 → (期望材料类别, 是否核心资格/废标项, 匹配关键词组)。命中不到则归为一般证明材料。"""
    for keywords, category, disq in _ATTACH_RULES:
        if any(k in title for k in keywords):
            return category, disq, keywords
    return "证明材料", False, ()


def _material_available(keywords: tuple[str, ...], available_materials: list[str]) -> bool:
    """用该附件所属类别的关键词组，到可用材料名里粗匹配是否已具备。"""
    return any(kw in mat for kw in keywords for mat in available_materials)


def _l1_items(
    templates: dict[str, FormTemplate],
    chapters: list[dict[str, Any]],
    facts: dict[str, Any],
    available_materials: list[str],
) -> list[CoverageItem]:
    items: list[CoverageItem] = []
    by_key = {t.key: t for t in templates.values()}

    # 必备表单：以填充未满字段判定可填/待补
    for key in _FORM_TEMPLATE_KEYS:
        tpl = by_key.get(key)
        if tpl is None:
            continue
        filled = fill_template(tpl, facts)
        if not filled.unfilled:
            status, detail = CoverStatus.FILLABLE, "字段齐全，可直接生成"
        else:
            labels = "、".join(dict.fromkeys(s.label for s in filled.unfilled))
            status, detail = CoverStatus.PARTIAL, f"待补：{labels}"
        items.append(CoverageItem(CoverLayer.L1_FORMAT, tpl.title, status, detail))

    # 附件/证照：逐条判定是否有材料
    seen: set[str] = set()
    for ch in chapters:
        for att in ch.get("attachments") or []:
            norm = att.strip()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            category, disq, keywords = _classify_attachment(norm)
            # 跳过"附件其实是本投标文件内生成的表单/表格"的项（不是需上传的扫描件）：
            #   · 法定代表人身份证明/授权委托书 → 走表单填充
            #   · 报价一览表/分项报价/明细表/偏离表/响应表/最后报价 → 走表格骨架
            # 注意：营业执照附件常含『自然人的身份证明』字样，故身份证明限定『法定代表人』前缀。
            if "授权委托书" in norm or ("法定代表人" in norm and "身份证明" in norm):
                continue
            if any(h in norm for h in _GENERATED_FORM_HINTS):
                continue
            if _material_available(keywords, available_materials):
                status, detail = CoverStatus.READY, f"已匹配材料（{category}）"
            else:
                status = CoverStatus.NEEDS_MATERIAL
                detail = f"需上传：{category}"
            items.append(CoverageItem(CoverLayer.L1_FORMAT, norm, status, detail, disqualifying=disq))
    return items


# ----------------------------------------------------------------------------
# L2：评分点（优先用 ComplianceItem，回退到招标正文中的带分值条目）
# ----------------------------------------------------------------------------

# 分值：排除『分项/分级/分类/分期/分包』等以"分"开头的词，避免把附件编号里的"N 分项"误判为分值
_SCORE_LINE_RE = re.compile(
    r"(?:得|加|扣|计|满分|最高|分值|占)?\s*\d+(?:\.\d+)?\s*分(?![项级类期包标])"
)
_SCORE_SECTION_HINTS = ("评分", "评审办法", "评标办法", "综合评分", "评审标准")


def _active_evidence_bindings(item: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = item.get("evidence_bindings")
    if not isinstance(bindings, list):
        return []
    return [
        binding
        for binding in bindings
        if isinstance(binding, dict) and str(binding.get("status") or "active") == "active"
    ]


def _l2_items_from_compliance(compliance_items: list[Any] | None) -> list[CoverageItem]:
    items: list[CoverageItem] = []
    for raw in compliance_items or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("item_type") != "scoring":
            continue
        if raw.get("status") in {"rejected", "superseded"}:
            continue
        title = str(raw.get("requirement_text") or raw.get("title") or "").strip()
        if not title:
            continue
        bindings = _active_evidence_bindings(raw)
        if bindings:
            names = [
                str(binding.get("material_name") or binding.get("enterprise_material_name") or "").strip()
                for binding in bindings
            ]
            names = [name for name in names if name]
            detail = "已绑定证据" + (f"：{'、'.join(names[:4])}" if names else "")
            status = CoverStatus.READY
        else:
            detail = "需补充评分应答、证据材料及评分索引页码"
            status = CoverStatus.PENDING
        items.append(CoverageItem(CoverLayer.L2_SCORING, title, status, detail))
    return items


def _l2_items(text: str, limit: int = 40, compliance_items: list[Any] | None = None) -> list[CoverageItem]:
    """轻量抽取评分点；有 ComplianceItem 快照时优先用数据层评分项。"""
    data_layer_items = _l2_items_from_compliance(compliance_items)
    if data_layer_items:
        return data_layer_items
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items: list[CoverageItem] = []
    in_scoring = False
    for ln in lines:
        if any(h in ln for h in _SCORE_SECTION_HINTS):
            in_scoring = True
        if not in_scoring:
            continue
        if _SCORE_LINE_RE.search(ln) and 6 <= len(ln) <= 80:
            title = ln if len(ln) <= 60 else ln[:57] + "…"
            items.append(
                CoverageItem(
                    CoverLayer.L2_SCORING,
                    title,
                    CoverStatus.PENDING,
                    "需在标书中应答并在评分索引指明对应章节/页码",
                )
            )
        if len(items) >= limit:
            break
    return items


# ----------------------------------------------------------------------------
# L3：技术/商务偏离响应（优先用 ComplianceItem，回退到目录中的偏离/响应章节）
# ----------------------------------------------------------------------------

_DEVIATION_HINTS = ("偏离", "技术响应", "商务响应", "技术要求", "采购需求", "技术规格")


def _l3_items_from_compliance(compliance_items: list[Any] | None) -> list[CoverageItem]:
    items: list[CoverageItem] = []
    for raw in compliance_items or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("item_type") != "technical_response":
            continue
        if raw.get("status") in {"rejected", "superseded"}:
            continue
        title = str(raw.get("requirement_text") or raw.get("title") or "").strip()
        if not title:
            continue
        bindings = _active_evidence_bindings(raw)
        if bindings:
            status = CoverStatus.READY
            detail = "已绑定技术响应证据，仍需人工确认响应/偏离口径"
        else:
            status = CoverStatus.PENDING
            detail = "需逐条填写我方响应并人工确认是否偏离"
        items.append(CoverageItem(CoverLayer.L3_RESPONSE, title, status, detail))
    return items


def _l3_items(
    chapters: list[dict[str, Any]],
    compliance_items: list[Any] | None = None,
) -> list[CoverageItem]:
    data_layer_items = _l3_items_from_compliance(compliance_items)
    if data_layer_items:
        return data_layer_items
    items: list[CoverageItem] = []
    for ch in chapters:
        title = ch.get("title", "")
        if any(h in title for h in _DEVIATION_HINTS):
            items.append(
                CoverageItem(
                    CoverLayer.L3_RESPONSE,
                    title,
                    CoverStatus.PENDING,
                    "需逐条对照招标技术/商务条款填『响应』或『偏离』",
                )
            )
    return items


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------


_CONFIRMED_MATERIAL_STATUSES = {"confirmed", "verified", "valid", "active"}


def _available_material_texts(available_materials: list[Any] | None) -> list[str]:
    """Normalize material strings or EnterpriseMaterial/binding snapshots.

    The coverage core stays pure and DB-free, but callers can pass snapshots
    from EnterpriseMaterial / ComplianceEvidenceBinding. Unconfirmed snapshots
    are ignored so "material ready" never means merely "candidate exists".
    """
    texts: list[str] = []
    for raw in available_materials or []:
        if isinstance(raw, str):
            text = raw.strip()
            if text:
                texts.append(text)
            continue
        if not isinstance(raw, dict):
            continue
        status = str(
            raw.get("verification_status")
            or raw.get("status")
            or raw.get("confirmation_status")
            or ""
        ).strip()
        if status and status not in _CONFIRMED_MATERIAL_STATUSES:
            continue
        values = [
            raw.get("material_name"),
            raw.get("name"),
            raw.get("material_type"),
            raw.get("category"),
            raw.get("certificate_no"),
            raw.get("evidence_text"),
            raw.get("snippet"),
        ]
        text = " ".join(str(value).strip() for value in values if value not in (None, ""))
        if text:
            texts.append(text)
    return texts


def compute_coverage(
    *,
    text: str,
    templates: dict[str, FormTemplate],
    chapters: list[dict[str, Any]],
    facts: dict[str, Any],
    available_materials: list[Any] | None = None,
    compliance_items: list[Any] | None = None,
) -> CoverageReport:
    """汇总 L1/L2/L3 三层覆盖。

    available_materials：企业材料库中可用材料的名称/类别列表（来自 EnterpriseMaterial）。
        传 None 或空 → 所有需材料附件标 needs_material（原型/未接材料库时的默认）。
    """
    mats = _available_material_texts(available_materials)
    report = CoverageReport()
    report.items.extend(_l1_items(templates, chapters, facts, mats))
    report.items.extend(_l2_items(text, compliance_items=compliance_items))
    report.items.extend(_l3_items(chapters, compliance_items=compliance_items))
    return report
