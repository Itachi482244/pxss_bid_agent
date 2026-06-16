"""工程量/报价清单抽取与算术校验。

该模块保持纯函数、无 I/O / 无 DB。它只做确定性工作：
  · 从招标正文中保守抽取明显的工程量清单行；
  · 对已有数量、综合单价、合价做 Decimal 算术校验；
  · 缺单价/缺合价时输出缺口，绝不补造报价数字。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


MONEY_QUANT = Decimal("0.01")
QTY_QUANT = Decimal("0.0001")


@dataclass(frozen=True)
class PricingRow:
    item_no: str
    item_name: str
    unit: str = ""
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    expected_total: Decimal | None = None
    total_status: str = "pending_price"
    source: str = "input"


@dataclass(frozen=True)
class PricingValidationReport:
    rows: list[PricingRow]
    total_amount: Decimal | None
    budget_amount: Decimal | None
    budget_status: str
    issues: list[str]

    @property
    def has_blocking_issue(self) -> bool:
        return bool(self.issues)


_UNIT_RE = r"(?:m2|m3|m|㎡|m²|立方米|平方米|米|公里|km|项|套|个|台|宗|批|处|座|樘)"
_SPACED_ROW_RE = re.compile(
    rf"^\s*(\d+)\s*[、.．\s]\s*(.+?)\s+({_UNIT_RE})\s+"
    r"([0-9]+(?:[.,，][0-9]+)?)"
    r"(?:\s+([0-9]+(?:[.,，][0-9]+)?(?:\s*万?元?)?))?"
    r"(?:\s+([0-9]+(?:[.,，][0-9]+)?(?:\s*万?元?)?))?\s*$",
    re.IGNORECASE,
)


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _parse_decimal(value: object, *, money: bool) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int | float):
        amount = Decimal(str(value))
    else:
        text = _clean_text(value)
        if not text:
            return None
        multiplier = Decimal("10000") if money and "万" in text else Decimal("1")
        text = (
            text.replace(",", "")
            .replace("，", "")
            .replace("￥", "")
            .replace("人民币", "")
            .replace("元", "")
            .replace("万元", "")
            .replace("万", "")
            .strip()
        )
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            amount = Decimal(match.group(0)) * multiplier
        except InvalidOperation:
            return None
    quant = MONEY_QUANT if money else QTY_QUANT
    return amount.quantize(quant, rounding=ROUND_HALF_UP)


def _money(value: object) -> Decimal | None:
    return _parse_decimal(value, money=True)


def _quantity(value: object) -> Decimal | None:
    return _parse_decimal(value, money=False)


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def normalize_pricing_rows(rows: list[Any] | None) -> list[PricingRow]:
    out: list[PricingRow] = []
    for index, raw in enumerate(rows or [], start=1):
        if not isinstance(raw, dict):
            continue
        item_name = _clean_text(_first_present(raw, ("item_name", "project_name", "name", "title")))
        if not item_name:
            continue
        out.append(
            PricingRow(
                item_no=_clean_text(_first_present(raw, ("item_no", "no", "sequence", "index"))) or str(index),
                item_name=item_name,
                unit=_clean_text(raw.get("unit")),
                quantity=_quantity(_first_present(raw, ("quantity", "qty", "工程量", "数量"))),
                unit_price=_money(_first_present(raw, ("unit_price", "price", "综合单价", "单价"))),
                line_total=_money(_first_present(raw, ("line_total", "total", "合价", "amount"))),
                source=_clean_text(raw.get("source")) or "input",
            )
        )
    return out


def _split_table_line(line: str) -> list[str]:
    if "|" in line:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t")]
    return []


def _row_from_cells(cells: list[str], *, source: str) -> PricingRow | None:
    cells = [cell for cell in cells if cell]
    if len(cells) < 4:
        return None
    if not re.fullmatch(r"\d+", cells[0]):
        return None
    if any(h in cells[1] for h in ("项目名称", "工程名称", "清单名称")):
        return None
    return PricingRow(
        item_no=cells[0],
        item_name=cells[1],
        unit=cells[2],
        quantity=_quantity(cells[3]),
        unit_price=_money(cells[4]) if len(cells) >= 5 else None,
        line_total=_money(cells[5]) if len(cells) >= 6 else None,
        source=source,
    )


def extract_boq_rows(text: str, *, limit: int = 80) -> list[PricingRow]:
    rows: list[PricingRow] = []
    in_boq_region = False
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if any(signal in line for signal in ("工程量清单", "分项报价", "报价明细", "已标价")):
            in_boq_region = True
            continue
        if not in_boq_region:
            continue
        cells = _split_table_line(line)
        parsed = _row_from_cells(cells, source=f"text:{line_no}") if cells else None
        if parsed is None:
            match = _SPACED_ROW_RE.match(line)
            if match:
                parsed = PricingRow(
                    item_no=match.group(1),
                    item_name=match.group(2).strip(),
                    unit=match.group(3),
                    quantity=_quantity(match.group(4)),
                    unit_price=_money(match.group(5)),
                    line_total=_money(match.group(6)),
                    source=f"text:{line_no}",
                )
        if parsed is not None and parsed.item_name:
            rows.append(parsed)
        if len(rows) >= limit:
            break
    return rows


def validate_pricing_rows(
    rows: list[PricingRow],
    *,
    budget_amount: object = None,
) -> PricingValidationReport:
    budget = _money(budget_amount)
    validated: list[PricingRow] = []
    issues: list[str] = []
    total = Decimal("0.00")
    all_totals_known = bool(rows)

    if not rows:
        return PricingValidationReport(
            rows=[],
            total_amount=None,
            budget_amount=budget,
            budget_status="no_rows",
            issues=["未识别到工程量清单行"],
        )

    for row in rows:
        expected = None
        status = "pending_price"
        effective_total = row.line_total
        if row.quantity is None:
            status = "missing_quantity"
            all_totals_known = False
            issues.append(f"{row.item_no} {row.item_name} 缺工程数量")
        elif row.unit_price is None:
            status = "missing_unit_price"
            all_totals_known = False
            issues.append(f"{row.item_no} {row.item_name} 缺综合单价")
        else:
            expected = (row.quantity * row.unit_price).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            if row.line_total is None:
                status = "computed_total"
                effective_total = expected
            elif abs(row.line_total - expected) <= MONEY_QUANT:
                status = "matched"
            else:
                status = "total_mismatch"
                issues.append(f"{row.item_no} {row.item_name} 合价与数量×单价不一致")
        if effective_total is not None:
            total += effective_total
        else:
            all_totals_known = False
        validated.append(
            replace(
                row,
                expected_total=expected,
                line_total=effective_total if row.line_total is None and expected is not None else row.line_total,
                total_status=status,
            )
        )

    total_amount = total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP) if all_totals_known else None
    if total_amount is None:
        budget_status = "pending_prices"
    elif budget is None:
        budget_status = "unknown_budget"
    elif total_amount > budget:
        budget_status = "over_budget"
        issues.append(f"投标总价 {total_amount} 超过预算/最高限价 {budget}")
    else:
        budget_status = "within_budget"

    return PricingValidationReport(
        rows=validated,
        total_amount=total_amount,
        budget_amount=budget,
        budget_status=budget_status,
        issues=issues,
    )


def build_pricing_report(
    *,
    text: str,
    pricing_rows: list[Any] | None = None,
    budget_amount: object = None,
) -> PricingValidationReport:
    rows = normalize_pricing_rows(pricing_rows)
    if not rows:
        rows = extract_boq_rows(text)
    return validate_pricing_rows(rows, budget_amount=budget_amount)
