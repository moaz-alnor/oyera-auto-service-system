"""Financial calculations used by invoices and payments."""

from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
)

MONEY_QUANTUM = Decimal("0.01")
PERCENT_DIVISOR = Decimal("100")


@dataclass(frozen=True, slots=True)
class InvoiceTotals:
    """Contain calculated invoice totals."""

    service_subtotal: Decimal
    product_subtotal: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class InvoiceBalance:
    """Contain the current payment balance of an invoice."""

    invoice_id: int
    currency: str
    total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal

    @property
    def is_paid(self) -> bool:
        """Return whether nothing remains outstanding."""

        return self.outstanding_amount == Decimal("0.00")


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""

    return value.quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def calculate_line_total(
    *,
    quantity: Decimal,
    unit_price: Decimal,
) -> Decimal:
    """Return quantity multiplied by its unit price."""

    return quantize_money(quantity * unit_price)


def calculate_invoice_totals(
    *,
    service_subtotal: Decimal,
    product_subtotal: Decimal,
    discount_percentage: Decimal,
    tax_percentage: Decimal,
) -> InvoiceTotals:
    """Calculate frozen invoice totals."""

    normalized_service_subtotal = quantize_money(service_subtotal)
    normalized_product_subtotal = quantize_money(product_subtotal)

    subtotal = quantize_money(normalized_service_subtotal + normalized_product_subtotal)

    discount_amount = quantize_money(subtotal * discount_percentage / PERCENT_DIVISOR)

    taxable_amount = quantize_money(subtotal - discount_amount)

    tax_amount = quantize_money(taxable_amount * tax_percentage / PERCENT_DIVISOR)

    total = quantize_money(taxable_amount + tax_amount)

    return InvoiceTotals(
        service_subtotal=normalized_service_subtotal,
        product_subtotal=normalized_product_subtotal,
        subtotal=subtotal,
        discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        total=total,
    )


def calculate_invoice_balance(
    *,
    invoice_id: int,
    currency: str,
    total: Decimal,
    paid_amount: Decimal,
) -> InvoiceBalance:
    """Calculate the outstanding amount of an invoice."""

    normalized_total = quantize_money(total)
    normalized_paid_amount = quantize_money(paid_amount)
    outstanding_amount = quantize_money(normalized_total - normalized_paid_amount)

    if normalized_paid_amount < Decimal("0.00"):
        raise ValueError("Paid amount cannot be negative.")

    if outstanding_amount < Decimal("0.00"):
        raise ValueError("Paid amount cannot exceed invoice total.")

    return InvoiceBalance(
        invoice_id=invoice_id,
        currency=currency,
        total=normalized_total,
        paid_amount=normalized_paid_amount,
        outstanding_amount=outstanding_amount,
    )
