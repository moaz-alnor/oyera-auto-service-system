"""Centralised financial calculations for purchasing."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_MONEY_INCREMENT = Decimal("0.01")
_PERCENT_DIVISOR = Decimal("100")


@dataclass(frozen=True, slots=True)
class PurchaseOrderTotals:
    """Contain calculated purchase-order financial values."""

    line_subtotal: Decimal
    discount_amount: Decimal
    net_subtotal: Decimal
    tax_amount: Decimal
    delivery_cost: Decimal
    total: Decimal


def round_money(value: Decimal) -> Decimal:
    """Round one monetary value to two decimal places."""

    return value.quantize(
        _MONEY_INCREMENT,
        rounding=ROUND_HALF_UP,
    )


def calculate_line_total(
    *,
    quantity: Decimal,
    unit_cost: Decimal,
) -> Decimal:
    """Return quantity multiplied by supplier unit cost."""

    return round_money(quantity * unit_cost)


def calculate_purchase_order_totals(
    *,
    line_totals: Iterable[Decimal],
    discount_percentage: Decimal,
    tax_percentage: Decimal,
    delivery_cost: Decimal,
) -> PurchaseOrderTotals:
    """Calculate all purchase-order financial values."""

    line_subtotal = round_money(sum(line_totals, Decimal("0.00")))

    discount_amount = round_money(
        line_subtotal * discount_percentage / _PERCENT_DIVISOR
    )

    net_subtotal = round_money(line_subtotal - discount_amount)

    tax_amount = round_money(net_subtotal * tax_percentage / _PERCENT_DIVISOR)

    normalised_delivery_cost = round_money(delivery_cost)

    total = round_money(net_subtotal + tax_amount + normalised_delivery_cost)

    return PurchaseOrderTotals(
        line_subtotal=line_subtotal,
        discount_amount=discount_amount,
        net_subtotal=net_subtotal,
        tax_amount=tax_amount,
        delivery_cost=normalised_delivery_cost,
        total=total,
    )
