"""招标文件目录推导（tender_directory）+ 章节映射（tender_outline）单元测试。

文本片段贴近真实政府采购竞争性磋商文件（仓顶隔热改造）与工程招标文件结构。
"""

from app.services.template_profile import get_template_profile
from app.services.tender_directory import derive_directory
from app.services.tender_outline import map_nodes_to_chapters

# 竞争性磋商（政府采购）样例——含"响应文件组成"权威骨架 + 附件 + 前附表信号
CONSULTATION_TEXT = """
第五章 响应文件组成

供应商的响应文件应包含以下部分：
一、磋商响应声明
二、供应商的资格证明资料
三、技术/商务响应与偏离表
四、报价一览表及分项价格表
五、供应商认为需提供的资料及说明
六、评分索引
七、最后报价
 一、磋商响应声明
致采购人：
附件1-1
法定代表人身份证明
附件1-2
法定代表人授权委托书
二、供应商的资格证明资料
附件2-1 法人或者其他组织的营业执照等主体资格证明文件
附件2-2 信用查询
四、报价一览表及分项价格表
附件4-1 报价一览表
附件4-2 分项报价明细表
磋商保证金
■ 不要求提供
本次磋商采购不接受联合体投标。
响应文件有效期不少于90日。
"""

# 工程招标样例——投标文件组成，话术为"投标文件"
TENDER_TEXT = """
第六章 投标文件格式

投标文件应包含以下部分：
一、投标函及投标函附录
二、法定代表人身份证明
三、授权委托书
四、已标价工程量清单
五、项目管理机构

投标保证金：投标人须缴纳投标保证金人民币2万元。
本次招标接受联合体投标。
"""


def test_consultation_skeleton_and_signals():
    outline = derive_directory(CONSULTATION_TEXT)
    assert outline.procurement_method == "consultation"
    assert outline.document_term == "响应文件"

    titles = [n.title for n in outline.nodes]
    assert titles == [
        "磋商响应声明",
        "供应商的资格证明资料",
        "技术/商务响应与偏离表",
        "报价一览表及分项价格表",
        "供应商认为需提供的资料及说明",
        "评分索引",
        "最后报价",
    ]

    # 附件按编号挂到对应章节
    by_title = {n.title: n for n in outline.nodes}
    assert len(by_title["磋商响应声明"].children) == 2
    assert len(by_title["供应商的资格证明资料"].children) == 2
    assert len(by_title["报价一览表及分项价格表"].children) == 2

    # 信号（含跨行表格键值对）
    assert outline.signals["bid_security_required"] is False
    assert outline.signals["consortium_allowed"] is False
    assert outline.signals["deviation_table_required"] is True
    assert outline.signals["scoring_index_required"] is True
    assert outline.signals["bid_validity_days"] == 90


def test_tender_procurement_and_signals():
    outline = derive_directory(TENDER_TEXT)
    assert outline.procurement_method == "tender"
    assert outline.document_term == "投标文件"
    assert outline.signals["bid_security_required"] is True
    assert outline.signals["consortium_allowed"] is True
    assert [n.title for n in outline.nodes] == [
        "投标函及投标函附录",
        "法定代表人身份证明",
        "授权委托书",
        "已标价工程量清单",
        "项目管理机构",
    ]


def test_mapping_to_outline_chapters():
    profile = get_template_profile()
    outline = derive_directory(TENDER_TEXT)
    chapters = map_nodes_to_chapters(outline.nodes, profile)

    by_title = {c["title"]: c for c in chapters}
    # 通用法定项命中模板章节
    assert by_title["法定代表人身份证明"]["section_type"] == "legal_representative_identity"
    assert by_title["法定代表人身份证明"]["custom"] is False
    assert by_title["授权委托书"]["section_type"] == "authorization_letter"
    # 标题始终保留招标原文
    assert all(c["title"] for c in chapters)
    # custom 章节 section_type 唯一且非空
    section_types = [c["section_type"] for c in chapters]
    assert len(section_types) == len(set(section_types))
    assert all(st for st in section_types)


def test_no_format_chapter_falls_back_empty():
    outline = derive_directory("第一章 招标公告\n本项目进行公开招标。\n")
    assert outline.nodes == []
    assert any("基线兜底" in d for d in outline.diagnostics)
