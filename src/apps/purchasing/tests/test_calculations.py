"""Tests for purchasing financial calculations."""

from decimal import Decimal

from apps.purchasing.calculations import (
    calculate_line_total,
    calculate_purchase_order_totals,
)


def test_purchase_line_total_rounds_money() -> None:
    """Round line values using commercial rounding."""

    assert calculate_line_total(
        quantity=Decimal("3.000"),
        unit_cost=Decimal("10.555"),
    ) == Decimal("31.67")


def test_purchase_order_totals_include_all_costs() -> None:
    """Calculate discount, tax and delivery cost."""

    totals = calculate_purchase_order_totals(
        line_totals=(
            Decimal("100000.00"),
            Decimal("50000.00"),
        ),
        discount_percentage=Decimal("10.00"),
        tax_percentage=Decimal("18.00"),
        delivery_cost=Decimal("5000.00"),
    )

    assert totals.line_subtotal == Decimal("150000.00")
    assert totals.discount_amount == Decimal("15000.00")
    assert totals.net_subtotal == Decimal("135000.00")
    assert totals.tax_amount == Decimal("24300.00")
    assert totals.delivery_cost == Decimal("5000.00")
    assert totals.total == Decimal("164300.00")


def test_empty_order_can_preserve_delivery_cost() -> None:
    """Calculate an empty draft without losing delivery."""

    totals = calculate_purchase_order_totals(
        line_totals=(),
        discount_percentage=Decimal("0.00"),
        tax_percentage=Decimal("0.00"),
        delivery_cost=Decimal("2500.00"),
    )

    assert totals.line_subtotal == Decimal("0.00")
    assert totals.total == Decimal("2500.00")
