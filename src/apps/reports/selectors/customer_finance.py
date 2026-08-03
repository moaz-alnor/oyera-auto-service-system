"""Read-only selectors for customer finance reports."""

from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from decimal import Decimal

from django.db.models import (
    DecimalField,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
)
from apps.reports.date_ranges import ReportDateRange

_MONEY_FIELD = DecimalField(
    max_digits=14,
    decimal_places=2,
)

_ZERO = Decimal("0.00")

_ACTIVE_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
)

_OPEN_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
)


@dataclass(frozen=True, slots=True)
class CustomerFinanceInvoiceRow:
    """Describe one invoice in the finance report."""

    invoice: Invoice
    paid_amount: Decimal
    outstanding_amount: Decimal
    is_overdue: bool


@dataclass(frozen=True, slots=True)
class CustomerFinanceSummary:
    """Contain customer-finance totals for one period."""

    currency: str
    invoice_count: int
    invoice_total: Decimal
    posted_payment_total: Decimal
    outstanding_balance: Decimal
    paid_invoice_count: int
    partially_paid_invoice_count: int
    overdue_invoice_count: int
    voided_invoice_count: int


@dataclass(frozen=True, slots=True)
class CustomerFinanceReport:
    """Contain customer finance summary and audit rows."""

    summary: CustomerFinanceSummary
    invoices: tuple[
        CustomerFinanceInvoiceRow,
        ...,
    ]


def _normalized_currency(value: str) -> str:
    """Return a validated three-letter currency code."""

    normalized = value.strip().upper()

    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Report currency must be a three-letter code.")

    return normalized


def _local_date_bounds(
    *,
    date_range: ReportDateRange,
) -> tuple[datetime, datetime]:
    """Return inclusive-start and exclusive-end times."""

    current_timezone = timezone.get_current_timezone()

    start_at = timezone.make_aware(
        datetime.combine(
            date_range.start_date,
            time.min,
        ),
        current_timezone,
    )

    end_at = timezone.make_aware(
        datetime.combine(
            (date_range.end_date + timedelta(days=1)),
            time.min,
        ),
        current_timezone,
    )

    return start_at, end_at


def get_customer_finance_report(
    *,
    date_range: ReportDateRange,
    currency: str = "UGX",
    as_of_date: date | None = None,
) -> CustomerFinanceReport:
    """Return customer invoice and payment activity."""

    normalized_currency = _normalized_currency(currency)
    effective_date = as_of_date or timezone.localdate()
    start_at, end_at = _local_date_bounds(date_range=date_range)

    invoices = tuple(
        Invoice.objects.filter(
            currency=normalized_currency,
            issued_at__gte=start_at,
            issued_at__lt=end_at,
        )
        .exclude(status=InvoiceStatus.DRAFT)
        .annotate(
            report_paid_amount=Coalesce(
                Sum(
                    "payments__amount",
                    filter=Q(payments__status=(PaymentStatus.POSTED)),
                ),
                Value(_ZERO),
                output_field=_MONEY_FIELD,
            )
        )
        .order_by(
            "-issued_at",
            "-pk",
        )
    )

    rows: list[CustomerFinanceInvoiceRow] = []

    for invoice in invoices:
        paid_amount = getattr(
            invoice,
            "report_paid_amount",
            _ZERO,
        )

        if invoice.status == InvoiceStatus.VOIDED:
            outstanding_amount = _ZERO
        else:
            outstanding_amount = max(
                invoice.total - paid_amount,
                _ZERO,
            )

        is_overdue = (
            invoice.status in _OPEN_INVOICE_STATUSES
            and invoice.due_date is not None
            and invoice.due_date < effective_date
            and outstanding_amount > _ZERO
        )

        rows.append(
            CustomerFinanceInvoiceRow(
                invoice=invoice,
                paid_amount=paid_amount,
                outstanding_amount=(outstanding_amount),
                is_overdue=is_overdue,
            )
        )

    posted_payment_total = Payment.objects.filter(
        status=PaymentStatus.POSTED,
        currency=normalized_currency,
        paid_at__gte=start_at,
        paid_at__lt=end_at,
    ).aggregate(
        total=Coalesce(
            Sum("amount"),
            Value(_ZERO),
            output_field=_MONEY_FIELD,
        )
    )["total"]

    active_rows = tuple(
        row for row in rows if row.invoice.status in _ACTIVE_INVOICE_STATUSES
    )

    invoice_total = sum(
        (row.invoice.total for row in active_rows),
        _ZERO,
    )

    outstanding_balance = sum(
        (row.outstanding_amount for row in active_rows),
        _ZERO,
    )

    summary = CustomerFinanceSummary(
        currency=normalized_currency,
        invoice_count=len(active_rows),
        invoice_total=invoice_total,
        posted_payment_total=(posted_payment_total),
        outstanding_balance=(outstanding_balance),
        paid_invoice_count=sum(
            row.invoice.status == InvoiceStatus.PAID for row in active_rows
        ),
        partially_paid_invoice_count=sum(
            row.invoice.status == InvoiceStatus.PARTIALLY_PAID for row in active_rows
        ),
        overdue_invoice_count=sum(row.is_overdue for row in active_rows),
        voided_invoice_count=sum(
            row.invoice.status == InvoiceStatus.VOIDED for row in rows
        ),
    )

    return CustomerFinanceReport(
        summary=summary,
        invoices=tuple(rows),
    )
