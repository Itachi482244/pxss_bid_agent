from __future__ import annotations

from app.services.tender_compliance_coverage import (
    CoverLayer,
    CoverStatus,
    compute_coverage,
)
from app.services.tender_format_templates import FormSlot, FormTemplate


def _tpl(key: str, title: str, slot_specs: list[tuple[str, str]]) -> FormTemplate:
    slots = [FormSlot(field_key=fk, label=lb, raw_hint=lb) for fk, lb in slot_specs]
    body = title + "\n" + "".join(f"（{lb}）" for _, lb in slot_specs)
    return FormTemplate(key=key, title=title, attachment_label=None, body=body, slots=slots)


def _scenario(
    facts: dict,
    available_materials: list[str] | None = None,
    compliance_items: list[dict] | None = None,
):
    templates = {
        "bid_commitment": _tpl(
            "bid_commitment",
            "磋商响应声明",
            [("purchaser", "采购人"), ("project_name", "项目名称"), ("supplier_name", "供应商名称")],
        ),
        "authorization_letter": _tpl(
            "authorization_letter",
            "法定代表人授权委托书",
            [("legal_representative", "法定代表人"), ("agent_person", "代理人")],
        ),
    }
    chapters = [
        {"section_type": "qualification", "title": "供应商的资格证明资料",
         "attachments": ["附件2-1 营业执照副本", "附件2-2 信用查询", "附件2-3 类似业绩合同"]},
        {"section_type": "deviation", "title": "技术/商务响应与偏离表", "attachments": []},
        {"section_type": "price", "title": "报价一览表", "attachments": []},
    ]
    text = (
        "第五章 评分办法\n"
        "综合评分法，满分100分。\n"
        "1 技术方案完整、合理的得10分。\n"
        "2 类似业绩每个得2分，最高得8分。\n"
        "3 报价采用低价优先法计算。\n"
    )
    return compute_coverage(
        text=text, templates=templates, chapters=chapters,
        facts=facts, available_materials=available_materials,
        compliance_items=compliance_items,
    )


def test_form_fillable_when_facts_complete():
    facts = {
        "purchaser": "甲方", "project_name": "某项目", "supplier_name": "我司",
        "legal_representative": "张三", "agent_person": "李四",
    }
    rep = _scenario(facts)
    forms = {i.title: i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "声明" in i.title or "委托书" in i.title}
    assert forms["磋商响应声明"].status == CoverStatus.FILLABLE
    assert forms["法定代表人授权委托书"].status == CoverStatus.FILLABLE


def test_form_partial_lists_missing_fields():
    facts = {"purchaser": "甲方", "project_name": "某项目"}  # 缺 supplier_name
    rep = _scenario(facts)
    decl = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if i.title == "磋商响应声明")
    assert decl.status == CoverStatus.PARTIAL
    assert "供应商名称" in decl.detail


def test_attachment_needs_material_and_disqualifying():
    rep = _scenario({}, available_materials=None)
    biz = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "营业执照" in i.title)
    assert biz.status == CoverStatus.NEEDS_MATERIAL
    assert biz.disqualifying is True
    # 业绩非核心资格
    perf = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "业绩" in i.title)
    assert perf.disqualifying is False
    # 营业执照 + 信用查询 是废标风险缺口
    titles = {i.title for i in rep.disqualifying_gaps}
    assert any("营业执照" in t for t in titles)
    assert any("信用" in t for t in titles)


def test_attachment_ready_when_material_available():
    rep = _scenario({}, available_materials=["营业执照副本（三证合一）", "信用中国查询截图"])
    biz = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "营业执照" in i.title)
    assert biz.status == CoverStatus.READY
    credit = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "信用" in i.title)
    assert credit.status == CoverStatus.READY
    assert rep.disqualifying_gaps == [] or all("业绩" in g.title for g in rep.disqualifying_gaps)


def test_material_snapshots_require_confirmed_status():
    rep = _scenario(
        {},
        available_materials=[
            {"material_name": "营业执照副本（三证合一）", "verification_status": "confirmed"},
            {"material_name": "信用中国查询截图", "verification_status": "candidate"},
        ],
    )

    biz = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "营业执照" in i.title)
    credit = next(i for i in rep.for_layer(CoverLayer.L1_FORMAT) if "信用" in i.title)

    assert biz.status == CoverStatus.READY
    assert credit.status == CoverStatus.NEEDS_MATERIAL
    assert any("信用" in item.title for item in rep.disqualifying_gaps)


def test_l2_scoring_points_extracted():
    rep = _scenario({})
    l2 = rep.for_layer(CoverLayer.L2_SCORING)
    assert len(l2) >= 2
    assert all(i.status == CoverStatus.PENDING for i in l2)
    assert any("技术方案" in i.title for i in l2)


def test_l2_prefers_data_layer_scoring_items_and_evidence_status():
    rep = _scenario(
        {},
        compliance_items=[
            {
                "item_type": "scoring",
                "requirement_text": "类似业绩每个得2分，最高8分。",
                "status": "confirmed",
                "evidence_bindings": [
                    {"status": "active", "material_name": "近三年类似业绩合同"}
                ],
            },
            {
                "item_type": "scoring",
                "requirement_text": "技术方案完整、合理得10分。",
                "status": "pending_confirm",
                "evidence_bindings": [],
            },
        ],
    )

    l2 = rep.for_layer(CoverLayer.L2_SCORING)
    assert [item.title for item in l2] == [
        "类似业绩每个得2分，最高8分。",
        "技术方案完整、合理得10分。",
    ]
    assert l2[0].status == CoverStatus.READY
    assert "近三年类似业绩合同" in l2[0].detail
    assert l2[1].status == CoverStatus.PENDING


def test_l3_deviation_chapters_flagged():
    rep = _scenario({})
    l3 = rep.for_layer(CoverLayer.L3_RESPONSE)
    assert any("偏离" in i.title for i in l3)
    assert all(i.status == CoverStatus.PENDING for i in l3)


def test_l3_prefers_data_layer_technical_response_items():
    rep = _scenario(
        {},
        compliance_items=[
            {
                "item_type": "technical_response",
                "requirement_text": "燃气管道设计压力应满足0.4MPa要求。",
                "status": "pending_confirm",
                "evidence_bindings": [],
            },
            {
                "item_type": "technical_response",
                "requirement_text": "管材应符合现行国家标准。",
                "status": "confirmed",
                "evidence_bindings": [
                    {"status": "active", "material_name": "管材检测报告"}
                ],
            },
        ],
    )

    l3 = rep.for_layer(CoverLayer.L3_RESPONSE)
    assert [item.title for item in l3] == [
        "燃气管道设计压力应满足0.4MPa要求。",
        "管材应符合现行国家标准。",
    ]
    assert l3[0].status == CoverStatus.PENDING
    assert l3[1].status == CoverStatus.READY


def test_summary_groups_by_layer_and_status():
    rep = _scenario({})
    summary = rep.summary()
    assert CoverLayer.L1_FORMAT.value in summary
    assert CoverLayer.L2_SCORING.value in summary
