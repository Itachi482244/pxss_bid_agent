"""一次性验证脚本：用仓顶招标文件装配投标文件 docx，打印诊断与合规自检摘要。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.parsers.word import parse_docx_bytes  # noqa: E402
from app.services.tender_directory import derive_directory  # noqa: E402
from app.services.tender_format_assembler import assemble_format_docx, build_form_facts  # noqa: E402
from app.services.tender_outline import map_nodes_to_chapters  # noqa: E402
from app.services.template_profile import get_template_profile  # noqa: E402

TENDER = ROOT / "仓顶面吊顶隔热降温改造招标文件.docx"
OUT = ROOT / "仓顶_投标文件_装配示例.docx"

# 模拟项目事实（与样张企业一致）
PROJECT_FACTS = {
    "tenderer_name": "岳阳市粮食购销有限公司",
    "project_name": "OP1-OP8仓顶面吊顶隔热降温改造",
    "tender_project_no": "HNZJ(FW)-202603",
    "bidder_name": "湖南远发建筑工程有限公司",
    "legal_representative_name": "胡凯军",
    "authorized_agent_name": "胡扩军 总经理",
    "unified_social_credit_code": "91430600MA4RC8A1XB",
    "bidder_address": "岳阳经济技术开发区巴陵东路·君临国际新城一栋1616室",
    "bid_date": "2026年6月2日",
}
# 模拟企业材料库已有材料（用于合规自检：营业执照/信用已备，业绩缺）
AVAILABLE_MATERIALS = ["营业执照副本（三证合一）", "信用中国查询截图"]


def main() -> None:
    chunks = parse_docx_bytes(TENDER.read_bytes())
    text = "\n".join(c.content_text for c in chunks if c.content_text)

    outline = derive_directory(text)
    profile = get_template_profile(None)
    chapters = map_nodes_to_chapters(outline.nodes, profile)

    facts = build_form_facts(PROJECT_FACTS, outline.signals)

    data, diag = assemble_format_docx(
        text=text, chapters=chapters, facts=facts,
        available_materials=AVAILABLE_MATERIALS,
    )
    OUT.write_bytes(data)

    print(f"字节 {len(data)}  → {OUT.name}")
    print("章节渲染：")
    for r in diag["rendered"]:
        print(f"  {r['title']} -> {r['as']}")
    print("合规覆盖：")
    for layer, counts in diag["coverage"].items():
        print(f"  {layer}: {counts}")
    print("废标风险缺口：", diag["disqualifying_gaps"] or "无")


if __name__ == "__main__":
    main()
