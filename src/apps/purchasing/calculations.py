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


@dataclass(frozen=True, slots=True)
class SupplierInvoiceTotals:
    """Contain calculated supplier-invoice totals."""

    line_subtotal: Decimal
    tax_amount: Decimal
    other_charges: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class SupplierInvoiceBalance:
    """Contain the current supplier-invoice balance."""

    supplier_invoice_id: int
    currency: str
    total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal

    @property
    def is_paid(self) -> bool:
        """Return whether the invoice has no balance."""

        return self.outstanding_amount == Decimal("0.00")


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


def calculate_supplier_invoice_totals(
    *,
    line_totals: Iterable[Decimal],
    tax_amount: Decimal,
    other_charges: Decimal,
) -> SupplierInvoiceTotals:
    """Calculate supplier-invoice financial totals."""

    line_subtotal = round_money(
        sum(
            line_totals,
            Decimal("0.00"),
        )
    )
    normalised_tax_amount = round_money(tax_amount)
    normalised_other_charges = round_money(other_charges)

    if normalised_tax_amount < Decimal("0.00"):
        raise ValueError("Supplier-invoice tax cannot be negative.")

    if normalised_other_charges < Decimal("0.00"):
        raise ValueError("Supplier-invoice charges cannot be negative.")

    total = round_money(
        line_subtotal + normalised_tax_amount + normalised_other_charges
    )

    return SupplierInvoiceTotals(
        line_subtotal=line_subtotal,
        tax_amount=normalised_tax_amount,
        other_charges=normalised_other_charges,
        total=total,
    )


def calculate_supplier_invoice_balance(
    *,
    supplier_invoice_id: int,
    currency: str,
    total: Decimal,
    paid_amount: Decimal,
) -> SupplierInvoiceBalance:
    """Calculate an outstanding supplier balance."""

    normalised_total = round_money(total)
    normalised_paid_amount = round_money(paid_amount)
    outstanding_amount = round_money(normalised_total - normalised_paid_amount)

    if normalised_total < Decimal("0.00"):
        raise ValueError("Supplier-invoice total cannot be negative.")

    if normalised_paid_amount < Decimal("0.00"):
        raise ValueError("Paid amount cannot be negative.")

    if outstanding_amount < Decimal("0.00"):
        raise ValueError("Paid amount cannot exceed the supplier-invoice total.")

    return SupplierInvoiceBalance(
        supplier_invoice_id=supplier_invoice_id,
        currency=currency.strip().upper(),
        total=normalised_total,
        paid_amount=normalised_paid_amount,
        outstanding_amount=outstanding_amount,
    )
