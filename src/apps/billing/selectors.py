"""Read-only queries for invoices and payment balances."""

from datetime import date
from decimal import Decimal

from django.db.models import (
    QuerySet,
    Sum,
)
from django.utils import timezone

from apps.billing.calculations import (
    InvoiceBalance,
    calculate_invoice_balance,
)
from apps.billing.constants import (
    InvoiceStatus,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
)


def invoice_list_queryset() -> QuerySet[Invoice]:
    """Return invoices with their principal workflow records."""

    return (
        Invoice.objects.select_related(
            "work_order",
            "work_order__job_card",
            "work_order__approved_quotation",
            "created_by",
            "updated_by",
            "voided_by",
        )
        .all()
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_invoice_detail(
    *,
    invoice_id: int,
) -> Invoice:
    """Return one invoice with lines and payment history."""

    return (
        Invoice.objects.select_related(
            "work_order",
            "work_order__job_card",
            "work_order__approved_quotation",
            "created_by",
            "updated_by",
            "voided_by",
        )
        .prefetch_related(
            "service_lines",
            "product_lines",
            "payments",
        )
        .get(pk=invoice_id)
    )


def payment_list_queryset(
    *,
    invoice_id: int | None = None,
) -> QuerySet[Payment]:
    """Return payment history, optionally for one invoice."""

    payments = Payment.objects.select_related(
        "invoice",
        "received_by",
        "voided_by",
    )

    if invoice_id is not None:
        payments = payments.filter(invoice_id=invoice_id)

    return payments.order_by(
        "-paid_at",
        "-pk",
    )


def get_invoice_balance(
    *,
    invoice_id: int,
) -> InvoiceBalance:
    """Return posted payments and outstanding balance."""

    invoice = Invoice.objects.only(
        "pk",
        "currency",
        "total",
    ).get(pk=invoice_id)

    paid_amount = Payment.objects.filter(
        invoice_id=invoice_id,
        status=PaymentStatus.POSTED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return calculate_invoice_balance(
        invoice_id=invoice.pk,
        currency=invoice.currency,
        total=invoice.total,
        paid_amount=paid_amount,
    )


def invoice_is_overdue(
    *,
    invoice: Invoice,
    on_date: date | None = None,
) -> bool:
    """Return whether an unpaid invoice is past its due date."""

    outstanding_statuses = {
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
    }

    if invoice.status not in outstanding_statuses:
        return False

    if invoice.due_date is None:
        return False

    effective_date = on_date or timezone.localdate()

    if invoice.due_date >= effective_date:
        return False

    balance = get_invoice_balance(invoice_id=invoice.pk)

    return balance.outstanding_amount > Decimal("0.00")
