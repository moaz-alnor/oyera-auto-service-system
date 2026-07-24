"""Centralized financial calculations for quotations."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.quotations.models import Quotation


_MONEY_INCREMENT = Decimal("0.01")
_PERCENT_DIVISOR = Decimal("100")


@dataclass(frozen=True, slots=True)
class QuotationTotals:
    """Contain the calculated financial values of a quotation."""

    service_subtotal: Decimal
    product_subtotal: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    total: Decimal


def round_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""

    return value.quantize(
        _MONEY_INCREMENT,
        rounding=ROUND_HALF_UP,
    )


def calculate_line_total(
    *,
    quantity: Decimal,
    unit_price: Decimal,
) -> Decimal:
    """Calculate one quotation-line total."""

    return round_money(quantity * unit_price)


def calculate_totals(
    *,
    service_line_totals: Iterable[Decimal],
    product_line_totals: Iterable[Decimal],
    discount_percentage: Decimal,
    tax_percentage: Decimal,
) -> QuotationTotals:
    """Calculate all financial totals using one canonical formula."""

    service_subtotal = round_money(sum(service_line_totals, Decimal("0")))
    product_subtotal = round_money(sum(product_line_totals, Decimal("0")))
    subtotal = round_money(service_subtotal + product_subtotal)
    discount_amount = round_money(subtotal * discount_percentage / _PERCENT_DIVISOR)
    taxable_amount = round_money(subtotal - discount_amount)
    tax_amount = round_money(taxable_amount * tax_percentage / _PERCENT_DIVISOR)
    total = round_money(taxable_amount + tax_amount)

    return QuotationTotals(
        service_subtotal=service_subtotal,
        product_subtotal=product_subtotal,
        subtotal=subtotal,
        discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        total=total,
    )


def calculate_quotation_totals(
    quotation: "Quotation",
) -> QuotationTotals:
    """Calculate totals from a quotation and its snapshot lines."""

    return calculate_totals(
        service_line_totals=(line.line_total for line in quotation.service_lines.all()),
        product_line_totals=(line.line_total for line in quotation.product_lines.all()),
        discount_percentage=quotation.discount_percentage,
        tax_percentage=quotation.tax_percentage,
    )
