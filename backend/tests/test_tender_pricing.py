from __future__ import annotations

from decimal import Decimal

from app.services.tender_pricing import build_pricing_report, extract_boq_rows, validate_pricing_rows


BOQ_TEXT = """第四章 工程量清单
序号 | 项目名称 | 单位 | 数量 | 综合单价 | 合价
1 | DN100燃气管道安装 | 米 | 120.5 | 100 | 12050
2 | 阀门井砌筑 | 座 | 2
"""


def test_extract_boq_rows_and_missing_unit_price_issue() -> None:
    rows = extract_boq_rows(BOQ_TEXT)
    assert len(rows) == 2
    assert rows[0].item_name == "DN100燃气管道安装"
    assert rows[0].quantity == Decimal("120.5000")
    assert rows[0].unit_price == Decimal("100.00")

    report = validate_pricing_rows(rows, budget_amount="20000")
    assert report.rows[0].total_status == "matched"
    assert report.rows[1].total_status == "missing_unit_price"
    assert report.total_amount is None
    assert report.budget_status == "pending_prices"
    assert any("缺综合单价" in issue for issue in report.issues)


def test_validate_pricing_rows_computes_totals_and_budget_status() -> None:
    report = build_pricing_report(
        text="",
        pricing_rows=[
            {"item_name": "管道安装", "unit": "米", "quantity": "10", "unit_price": "200"},
            {"item_name": "阀门安装", "unit": "个", "quantity": "2", "unit_price": "300"},
        ],
        budget_amount="3000",
    )

    assert report.rows[0].line_total == Decimal("2000.00")
    assert report.rows[0].total_status == "computed_total"
    assert report.total_amount == Decimal("2600.00")
    assert report.budget_status == "within_budget"
    assert report.issues == []


def test_validate_pricing_rows_flags_mismatch_and_over_budget() -> None:
    report = build_pricing_report(
        text="",
        pricing_rows=[
            {
                "item_name": "管道安装",
                "unit": "米",
                "quantity": "10",
                "unit_price": "200",
                "line_total": "1999",
            }
        ],
        budget_amount="1000",
    )

    assert report.rows[0].expected_total == Decimal("2000.00")
    assert report.rows[0].total_status == "total_mismatch"
    assert report.total_amount == Decimal("1999.00")
    assert report.budget_status == "over_budget"
    assert any("合价与数量" in issue for issue in report.issues)
    assert any("超过预算" in issue for issue in report.issues)
