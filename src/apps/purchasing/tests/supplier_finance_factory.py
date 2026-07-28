"""Factories shared by supplier-finance tests."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.purchasing.constants import (
    SupplierPaymentMethod,
)
from apps.purchasing.models import (
    SupplierInvoice,
    SupplierPayment,
)
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    create_supplier_invoice,
    post_supplier_invoice,
)
from apps.purchasing.services.supplier_payments import (
    RecordSupplierPaymentCommand,
    record_supplier_payment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    PostedReceiptContext,
    create_posted_receipt,
)


@dataclass(frozen=True, slots=True)
class SupplierFinanceTestContext:
    """Contain posted supplier-finance test records."""

    receipt_context: PostedReceiptContext
    supplier_invoice: SupplierInvoice
    supplier_payment: SupplierPayment | None


def create_supplier_finance_context(
    *,
    context: PurchasingTestContext,
    supplier_reference: str = "SUP-SELECTOR-001",
    invoice_date: date | None = None,
    due_date: date | None = None,
    payment_amount: Decimal | None = None,
) -> SupplierFinanceTestContext:
    """Create a posted invoice and optional payment."""

    receipt_context = create_posted_receipt(context=context)

    effective_invoice_date = invoice_date or timezone.localdate()
    effective_due_date = due_date or effective_invoice_date + timedelta(days=30)

    supplier_invoice = create_supplier_invoice(
        actor=context.manager,
        command=CreateSupplierInvoiceCommand(
            purchase_order_id=(receipt_context.purchase_order.pk),
            supplier_reference=supplier_reference,
            invoice_date=effective_invoice_date,
            due_date=effective_due_date,
            lines=(
                SupplierInvoiceLineCommand(
                    goods_receipt_line_id=(receipt_context.goods_receipt_line.pk),
                    quantity_invoiced=Decimal("4.000"),
                    unit_cost=Decimal("25000.00"),
                ),
            ),
            notes="Supplier-finance selector test.",
        ),
    )

    supplier_invoice = post_supplier_invoice(
        actor=context.manager,
        supplier_invoice_id=supplier_invoice.pk,
    )

    supplier_payment: SupplierPayment | None = None

    if payment_amount is not None:
        supplier_payment = record_supplier_payment(
            actor=context.cashier,
            supplier_invoice_id=supplier_invoice.pk,
            command=RecordSupplierPaymentCommand(
                amount=payment_amount,
                method=(SupplierPaymentMethod.BANK_TRANSFER),
                external_reference="BANK-SELECTOR-001",
                notes="Supplier selector payment.",
            ),
        )

        supplier_invoice.refresh_from_db()

    return SupplierFinanceTestContext(
        receipt_context=receipt_context,
        supplier_invoice=supplier_invoice,
        supplier_payment=supplier_payment,
    )
