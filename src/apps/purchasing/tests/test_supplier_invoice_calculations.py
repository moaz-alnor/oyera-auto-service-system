"""Tests for supplier-invoice financial calculations."""

from decimal import Decimal

import pytest

from apps.purchasing.calculations import (
    calculate_line_total,
    calculate_supplier_invoice_balance,
    calculate_supplier_invoice_totals,
)


def test_supplier_invoice_line_total_is_rounded() -> None:
    """Round quantity multiplied by supplier cost."""

    assert calculate_line_total(
        quantity=Decimal("3.000"),
        unit_cost=Decimal("1234.567"),
    ) == Decimal("3703.70")


def test_calculate_supplier_invoice_totals() -> None:
    """Combine lines, tax, and additional charges."""

    totals = calculate_supplier_invoice_totals(
        line_totals=(
            Decimal("100000.00"),
            Decimal("50000.00"),
        ),
        tax_amount=Decimal("27000.00"),
        other_charges=Decimal("5000.00"),
    )

    assert totals.line_subtotal == Decimal("150000.00")
    assert totals.tax_amount == Decimal("27000.00")
    assert totals.other_charges == Decimal("5000.00")
    assert totals.total == Decimal("182000.00")


def test_supplier_invoice_totals_normalise_money() -> None:
    """Round tax and charges to two decimal places."""

    totals = calculate_supplier_invoice_totals(
        line_totals=(
            Decimal("100.005"),
            Decimal("20.004"),
        ),
        tax_amount=Decimal("5.555"),
        other_charges=Decimal("1.005"),
    )

    assert totals.line_subtotal == Decimal("120.01")
    assert totals.tax_amount == Decimal("5.56")
    assert totals.other_charges == Decimal("1.01")
    assert totals.total == Decimal("126.58")


@pytest.mark.parametrize(
    ("tax_amount", "other_charges"),
    (
        (
            Decimal("-1.00"),
            Decimal("0.00"),
        ),
        (
            Decimal("0.00"),
            Decimal("-1.00"),
        ),
    ),
)
def test_supplier_invoice_totals_reject_negative_values(
    tax_amount: Decimal,
    other_charges: Decimal,
) -> None:
    """Reject negative tax and additional charges."""

    with pytest.raises(ValueError):
        calculate_supplier_invoice_totals(
            line_totals=(Decimal("100.00"),),
            tax_amount=tax_amount,
            other_charges=other_charges,
        )


def test_calculate_partial_supplier_invoice_balance() -> None:
    """Return paid and outstanding supplier amounts."""

    balance = calculate_supplier_invoice_balance(
        supplier_invoice_id=7,
        currency="ugx",
        total=Decimal("182000.00"),
        paid_amount=Decimal("50000.00"),
    )

    assert balance.supplier_invoice_id == 7
    assert balance.currency == "UGX"
    assert balance.total == Decimal("182000.00")
    assert balance.paid_amount == Decimal("50000.00")
    assert balance.outstanding_amount == Decimal("132000.00")
    assert not balance.is_paid


def test_calculate_paid_supplier_invoice_balance() -> None:
    """Recognise a fully paid supplier invoice."""

    balance = calculate_supplier_invoice_balance(
        supplier_invoice_id=8,
        currency="UGX",
        total=Decimal("182000.00"),
        paid_amount=Decimal("182000.00"),
    )

    assert balance.outstanding_amount == Decimal("0.00")
    assert balance.is_paid


def test_supplier_invoice_balance_rejects_overpayment() -> None:
    """Prevent payment above the supplier balance."""

    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        calculate_supplier_invoice_balance(
            supplier_invoice_id=9,
            currency="UGX",
            total=Decimal("100000.00"),
            paid_amount=Decimal("100000.01"),
        )


def test_supplier_invoice_balance_rejects_negative_payment() -> None:
    """Prevent a negative supplier payment."""

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        calculate_supplier_invoice_balance(
            supplier_invoice_id=10,
            currency="UGX",
            total=Decimal("100000.00"),
            paid_amount=Decimal("-1.00"),
        )
