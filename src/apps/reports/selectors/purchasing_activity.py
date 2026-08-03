"""Read-only selectors for purchasing activity reports."""

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
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    GoodsReceipt,
    PurchaseOrder,
    SupplierInvoice,
    SupplierPayment,
)
from apps.reports.date_ranges import ReportDateRange

_ACTIVE_SUPPLIER_INVOICE_STATUSES = (
    SupplierInvoiceStatus.POSTED,
    SupplierInvoiceStatus.PARTIALLY_PAID,
)

_MONEY_FIELD = DecimalField(
    max_digits=14,
    decimal_places=2,
)


@dataclass(frozen=True, slots=True)
class PurchasingActivitySummary:
    """Contain purchasing activity and liability totals."""

    currency: str
    purchase_orders_created_count: int
    purchase_orders_submitted_count: int
    purchase_orders_approved_count: int
    purchase_orders_cancelled_count: int
    goods_receipts_count: int
    supplier_invoices_posted_count: int
    supplier_invoices_voided_count: int
    supplier_payments_posted_count: int
    supplier_payments_voided_count: int
    supplier_payment_total: Decimal
    current_open_invoice_count: int
    current_outstanding_liability: Decimal
    current_overdue_invoice_count: int


@dataclass(frozen=True, slots=True)
class PurchasingActivityReport:
    """Contain Purchasing period activity and current risk."""

    summary: PurchasingActivitySummary
    purchase_orders: tuple[PurchaseOrder, ...]
    goods_receipts: tuple[GoodsReceipt, ...]
    supplier_invoices: tuple[SupplierInvoice, ...]
    supplier_payments: tuple[SupplierPayment, ...]
    open_supplier_invoices: tuple[
        SupplierInvoice,
        ...,
    ]


def _normalise_currency(currency: str) -> str:
    """Return a validated three-letter currency."""

    normalised_currency = currency.strip().upper()

    if len(normalised_currency) != 3 or not normalised_currency.isalpha():
        raise ValueError("Currency must use a three-letter code.")

    return normalised_currency


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


def _is_within_period(
    *,
    value: datetime | None,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    """Return whether a timestamp falls in the period."""

    return value is not None and start_at <= value < end_at


def _invoice_outstanding_amount(
    supplier_invoice: SupplierInvoice,
) -> Decimal:
    """Return one annotated invoice balance."""

    annotated_outstanding = getattr(
        supplier_invoice,
        "outstanding_amount",
        None,
    )

    if annotated_outstanding is not None:
        return max(
            annotated_outstanding,
            Decimal("0.00"),
        )

    posted_payment_total = getattr(
        supplier_invoice,
        "posted_payment_total",
        Decimal("0.00"),
    )

    return max(
        supplier_invoice.total - posted_payment_total,
        Decimal("0.00"),
    )


def get_purchasing_activity_report(
    *,
    date_range: ReportDateRange,
    currency: str = "UGX",
    as_of_date: date | None = None,
) -> PurchasingActivityReport:
    """Return purchasing activity and current liability."""

    normalised_currency = _normalise_currency(currency)
    effective_as_of_date = as_of_date or timezone.localdate()

    start_at, end_at = _local_date_bounds(date_range=date_range)

    purchase_orders = tuple(
        PurchaseOrder.objects.filter(
            currency=normalised_currency,
        )
        .filter(
            Q(
                created_at__gte=start_at,
                created_at__lt=end_at,
            )
            | Q(
                submitted_at__gte=start_at,
                submitted_at__lt=end_at,
            )
            | Q(
                approved_at__gte=start_at,
                approved_at__lt=end_at,
            )
            | Q(
                cancelled_at__gte=start_at,
                cancelled_at__lt=end_at,
            )
        )
        .select_related(
            "supplier",
            "created_by",
            "submitted_by",
            "approved_by",
            "cancelled_by",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )

    goods_receipts = tuple(
        GoodsReceipt.objects.filter(
            purchase_order__currency=(normalised_currency),
            received_at__gte=start_at,
            received_at__lt=end_at,
        )
        .select_related(
            "purchase_order",
            "purchase_order__supplier",
            "received_by",
        )
        .order_by(
            "-received_at",
            "-pk",
        )
    )

    supplier_invoices = tuple(
        SupplierInvoice.objects.filter(
            currency=normalised_currency,
        )
        .filter(
            Q(
                invoice_date__gte=(date_range.start_date),
                invoice_date__lte=(date_range.end_date),
            )
            | Q(
                posted_at__gte=start_at,
                posted_at__lt=end_at,
            )
            | Q(
                voided_at__gte=start_at,
                voided_at__lt=end_at,
            )
        )
        .select_related(
            "supplier",
            "purchase_order",
            "posted_by",
            "voided_by",
        )
        .order_by(
            "-invoice_date",
            "-pk",
        )
    )

    supplier_payments = tuple(
        SupplierPayment.objects.filter(
            currency=normalised_currency,
        )
        .filter(
            Q(
                paid_at__gte=start_at,
                paid_at__lt=end_at,
            )
            | Q(
                voided_at__gte=start_at,
                voided_at__lt=end_at,
            )
        )
        .select_related(
            "supplier_invoice",
            "supplier_invoice__supplier",
            "recorded_by",
            "voided_by",
        )
        .order_by(
            "-paid_at",
            "-pk",
        )
    )

    open_supplier_invoices = tuple(
        SupplierInvoice.objects.filter(
            currency=normalised_currency,
            status__in=(_ACTIVE_SUPPLIER_INVOICE_STATUSES),
        )
        .annotate(
            posted_payment_total=Coalesce(
                Sum(
                    "payments__amount",
                    filter=Q(payments__status=(SupplierPaymentStatus.POSTED)),
                ),
                Value(
                    Decimal("0.00"),
                    output_field=_MONEY_FIELD,
                ),
                output_field=_MONEY_FIELD,
            )
        )
        .annotate(
            outstanding_amount=ExpressionWrapper(
                F("total") - F("posted_payment_total"),
                output_field=_MONEY_FIELD,
            )
        )
        .select_related(
            "supplier",
            "purchase_order",
        )
        .order_by(
            "due_date",
            "pk",
        )
    )

    supplier_payment_total = sum(
        (
            payment.amount
            for payment in supplier_payments
            if (
                payment.status == SupplierPaymentStatus.POSTED
                and _is_within_period(
                    value=payment.paid_at,
                    start_at=start_at,
                    end_at=end_at,
                )
            )
        ),
        Decimal("0.00"),
    )

    current_outstanding_liability = sum(
        (
            _invoice_outstanding_amount(supplier_invoice)
            for supplier_invoice in open_supplier_invoices
        ),
        Decimal("0.00"),
    )

    current_overdue_invoice_count = sum(
        (
            supplier_invoice.due_date < effective_as_of_date
            and _invoice_outstanding_amount(supplier_invoice) > Decimal("0.00")
        )
        for supplier_invoice in open_supplier_invoices
    )

    summary = PurchasingActivitySummary(
        currency=normalised_currency,
        purchase_orders_created_count=sum(
            _is_within_period(
                value=purchase_order.created_at,
                start_at=start_at,
                end_at=end_at,
            )
            for purchase_order in purchase_orders
        ),
        purchase_orders_submitted_count=sum(
            _is_within_period(
                value=purchase_order.submitted_at,
                start_at=start_at,
                end_at=end_at,
            )
            for purchase_order in purchase_orders
        ),
        purchase_orders_approved_count=sum(
            _is_within_period(
                value=purchase_order.approved_at,
                start_at=start_at,
                end_at=end_at,
            )
            for purchase_order in purchase_orders
        ),
        purchase_orders_cancelled_count=sum(
            _is_within_period(
                value=purchase_order.cancelled_at,
                start_at=start_at,
                end_at=end_at,
            )
            for purchase_order in purchase_orders
        ),
        goods_receipts_count=len(goods_receipts),
        supplier_invoices_posted_count=sum(
            _is_within_period(
                value=supplier_invoice.posted_at,
                start_at=start_at,
                end_at=end_at,
            )
            for supplier_invoice in supplier_invoices
        ),
        supplier_invoices_voided_count=sum(
            _is_within_period(
                value=supplier_invoice.voided_at,
                start_at=start_at,
                end_at=end_at,
            )
            for supplier_invoice in supplier_invoices
        ),
        supplier_payments_posted_count=sum(
            (
                payment.status == SupplierPaymentStatus.POSTED
                and _is_within_period(
                    value=payment.paid_at,
                    start_at=start_at,
                    end_at=end_at,
                )
            )
            for payment in supplier_payments
        ),
        supplier_payments_voided_count=sum(
            (
                payment.status == SupplierPaymentStatus.VOIDED
                and _is_within_period(
                    value=payment.voided_at,
                    start_at=start_at,
                    end_at=end_at,
                )
            )
            for payment in supplier_payments
        ),
        supplier_payment_total=(supplier_payment_total),
        current_open_invoice_count=len(open_supplier_invoices),
        current_outstanding_liability=(current_outstanding_liability),
        current_overdue_invoice_count=(current_overdue_invoice_count),
    )

    return PurchasingActivityReport(
        summary=summary,
        purchase_orders=purchase_orders,
        goods_receipts=goods_receipts,
        supplier_invoices=supplier_invoices,
        supplier_payments=supplier_payments,
        open_supplier_invoices=(open_supplier_invoices),
    )
