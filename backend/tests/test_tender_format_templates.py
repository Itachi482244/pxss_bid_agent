"""tender_format_templates 单测：模板抽取、填空位识别、事实填充、上下文消歧。

用内存文本样本（复刻真实磋商文件「响应文件组成格式」章的关键模板与填空位形态），
不依赖具体 .docx，保证行为可回归。
"""

from __future__ import annotations

from app.services.tender_format_templates import extract_format_templates, fill_template

# 复刻真实格式章：目录式列举 + 带模板正文（声明内部复用『一、二、…』分句序号）
SAMPLE = """第五章 响应文件组成
供应商的响应文件应包含以下部分：
一、磋商响应声明
二、供应商的资格证明资料
三、技术/商务响应与偏离表
一、磋商响应声明
致 （采购人、采购代理机构）：
根据贵方为 （项目名称）的磋商邀请（采购代理编号： ），签字代表 （姓名、职务）经正式授权并代表供应商 （供应商名称）提交响应文件正本一份,副本 份；响应文件电子文档：一份，参加采购项目第 包磋商，并在此声明，所递交的响应文件内容完整、真实。
一、我方已详细审查磋商文件。
四、我方同意在磋商文件中规定的提交首次响应文件截止时间起 日内（响应文件有效期）遵守本响应文件中的承诺。
七、我方的联系方式：
地址： ；邮编： ；电话： ；电子邮箱： 。
供应商名称（盖单位公章）：
日期： 年 月 日
附件1-2
法定代表人授权委托书
本人 （姓名、职务）系 （供应商名称）的法定代表人（单位负责人），现授权 （姓名、职务）为我方代理人。
委托期限： 。
本授权书于 年 月 日签字生效，特此声明。
供应商名称（盖单位公章）：
日期： 年 月 日
二、供应商的资格证明资料
须知
供应商应提供营业执照等证明材料。
"""

TOP_TITLES = ["磋商响应声明", "供应商的资格证明资料", "技术/商务响应与偏离表"]

FACTS = {
    "purchaser": "岳阳市粮食购销有限公司",
    "project_name": "OP1-OP8仓顶面吊顶隔热降温改造",
    "agent_code": "HNZJ(FW)-202603",
    "signatory": "胡扩军 总经理",
    "supplier_name": "湖南远发建筑工程有限公司",
    "copies_duplicate": "贰",
    "package_no": "1",
    "bid_validity_days": "90",
    "address": "岳阳经济技术开发区巴陵东路君临国际新城一栋1616室",
    "postcode": "414100",
    "phone": "0730-8888888",
    "email": "35968426@QQ.com",
    "date": "2026-3-31",
    "legal_representative": "胡凯军",
    "agent_person": "胡扩军 总经理",
    "delegation_period": "90天",
}


def test_extract_keys_and_full_body():
    tpls = extract_format_templates(SAMPLE, TOP_TITLES)
    # 语义键命中声明与委托书
    assert "bid_commitment" in tpls
    assert "authorization_letter" in tpls
    decl = tpls["bid_commitment"]
    # 声明 body 应包含内部分句与盖章/日期，未被『一、…七、』分句切断
    assert "我方已详细审查磋商文件" in decl.body
    assert "我方的联系方式" in decl.body
    assert "盖单位公章" in decl.body


def test_declaration_slots_and_fill():
    tpls = extract_format_templates(SAMPLE, TOP_TITLES)
    decl = tpls["bid_commitment"]
    filled = fill_template(decl, FACTS)
    body = "\n".join(filled.lines)
    assert "致 岳阳市粮食购销有限公司 （采购人" in body
    assert "OP1-OP8仓顶面吊顶隔热降温改造 （项目名称）" in body
    assert "采购代理编号：HNZJ(FW)-202603" in body
    assert "副本贰份" in body
    assert "第1包磋商" in body
    assert "截止时间起90日内" in body
    assert "日期：2026年3月31日" in body
    assert filled.seal_required is True
    assert filled.unfilled == []  # FACTS 覆盖全部 slot


def test_unfilled_keeps_placeholder():
    tpls = extract_format_templates(SAMPLE, TOP_TITLES)
    decl = tpls["bid_commitment"]
    partial = {k: v for k, v in FACTS.items() if k != "phone"}
    partial.pop("email")  # 去掉邮箱触发未填
    filled = fill_template(decl, partial)
    body = "\n".join(filled.lines)
    assert "［待填:电子邮箱］" in body
    assert any(u.field_key == "email" for u in filled.unfilled)


def test_authorization_dual_name_disambiguation():
    tpls = extract_format_templates(SAMPLE, TOP_TITLES)
    auth = tpls["authorization_letter"]
    filled = fill_template(auth, FACTS)
    body = "\n".join(filled.lines)
    # 本人=法定代表人(胡凯军)，现授权=代理人(胡扩军)
    assert "本人 胡凯军 （姓名、职务）" in body
    assert "现授权 胡扩军 总经理 （姓名、职务）为我方代理人" in body
    assert "委托期限：90天" in body


def test_no_format_chapter_returns_empty():
    assert extract_format_templates("一份没有响应文件格式章的普通文本。", []) == {}
