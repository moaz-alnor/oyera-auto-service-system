"""Read-only queries for shared operational dashboards."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
)
from apps.inventory.selectors import (
    InventoryBalance,
    get_low_stock_items,
)
from apps.jobs.constants import ACTIVE_JOB_STATUSES
from apps.jobs.models import JobCard
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    SupplierInvoiceStatus,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    PurchaseOrder,
    SupplierInvoice,
    SupplierPayment,
)
from apps.workshop.constants import WorkOrderStatus
from apps.workshop.models import WorkOrder

_ACTIVE_WORK_ORDER_STATUSES = (
    WorkOrderStatus.PLANNED,
    WorkOrderStatus.READY,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
    WorkOrderStatus.AWAITING_REVIEW,
)

_RELEASE_READY_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
)


@dataclass(frozen=True, slots=True)
class OperationalDashboardMetrics:
    """Contain the primary operational dashboard values."""

    vehicles_received_today: int
    open_job_cards: int
    active_work_orders: int
    vehicles_ready_for_release: int
    invoices_awaiting_payment: int
    low_stock_items: int
    purchase_orders_awaiting_approval: int
    supplier_invoices_awaiting_payment: int


def _current_local_day_bounds() -> tuple[
    datetime,
    datetime,
]:
    """Return timezone-aware boundaries for today."""

    today = timezone.localdate()
    current_timezone = timezone.get_current_timezone()

    start_at = timezone.make_aware(
        datetime.combine(
            today,
            time.min,
        ),
        current_timezone,
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at


def get_operational_dashboard_metrics() -> OperationalDashboardMetrics:
    """Return live operational metrics for the dashboard."""

    start_at, end_at = _current_local_day_bounds()

    vehicles_received_today = JobCard.objects.filter(
        arrival_at__gte=start_at,
        arrival_at__lt=end_at,
    ).count()

    open_job_cards = JobCard.objects.filter(status__in=ACTIVE_JOB_STATUSES).count()

    active_work_orders = WorkOrder.objects.filter(
        status__in=_ACTIVE_WORK_ORDER_STATUSES
    ).count()

    vehicles_ready_for_release = JobCard.objects.filter(
        status__in=ACTIVE_JOB_STATUSES,
        work_order__status=(WorkOrderStatus.COMPLETED),
        work_order__invoice__status__in=(_RELEASE_READY_INVOICE_STATUSES),
        vehicle_release__isnull=True,
    ).count()

    invoices_awaiting_payment = Invoice.objects.filter(
        status__in=(
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
        )
    ).count()

    low_stock_items = len(get_low_stock_items())

    purchase_orders_awaiting_approval = PurchaseOrder.objects.filter(
        status=PurchaseOrderStatus.SUBMITTED
    ).count()

    supplier_invoices_awaiting_payment = SupplierInvoice.objects.filter(
        status__in=(
            SupplierInvoiceStatus.POSTED,
            SupplierInvoiceStatus.PARTIALLY_PAID,
        )
    ).count()

    return OperationalDashboardMetrics(
        vehicles_received_today=(vehicles_received_today),
        open_job_cards=open_job_cards,
        active_work_orders=active_work_orders,
        vehicles_ready_for_release=(vehicles_ready_for_release),
        invoices_awaiting_payment=(invoices_awaiting_payment),
        low_stock_items=low_stock_items,
        purchase_orders_awaiting_approval=(purchase_orders_awaiting_approval),
        supplier_invoices_awaiting_payment=(supplier_invoices_awaiting_payment),
    )


@dataclass(frozen=True, slots=True)
class OperationalDashboardAlerts:
    """Contain records requiring employee attention."""

    release_ready_jobs: tuple[JobCard, ...]
    low_stock_balances: tuple[InventoryBalance, ...]
    submitted_purchase_orders: tuple[
        PurchaseOrder,
        ...,
    ]
    unpaid_supplier_invoices: tuple[
        SupplierInvoice,
        ...,
    ]


def get_operational_dashboard_alerts(
    *,
    limit: int = 5,
) -> OperationalDashboardAlerts:
    """Return the highest-priority operational records."""

    if limit < 1:
        raise ValueError("Dashboard alert limit must be positive.")

    release_ready_jobs = tuple(
        JobCard.objects.filter(
            status__in=ACTIVE_JOB_STATUSES,
            work_order__status=(WorkOrderStatus.COMPLETED),
            work_order__invoice__status__in=(_RELEASE_READY_INVOICE_STATUSES),
            vehicle_release__isnull=True,
        )
        .select_related(
            "customer",
            "vehicle",
            "work_order",
            "work_order__invoice",
        )
        .order_by(
            "-arrival_at",
            "-pk",
        )[:limit]
    )

    low_stock_balances = tuple(
        sorted(
            get_low_stock_items(),
            key=lambda balance: (
                balance.available_quantity,
                balance.inventory_item.product.name,
            ),
        )[:limit]
    )

    submitted_purchase_orders = tuple(
        PurchaseOrder.objects.filter(status=PurchaseOrderStatus.SUBMITTED)
        .select_related(
            "supplier",
            "submitted_by",
        )
        .order_by(
            "submitted_at",
            "pk",
        )[:limit]
    )

    unpaid_supplier_invoices = tuple(
        SupplierInvoice.objects.filter(
            status__in=(
                SupplierInvoiceStatus.POSTED,
                SupplierInvoiceStatus.PARTIALLY_PAID,
            )
        )
        .select_related(
            "supplier",
            "purchase_order",
        )
        .order_by(
            "due_date",
            "pk",
        )[:limit]
    )

    return OperationalDashboardAlerts(
        release_ready_jobs=release_ready_jobs,
        low_stock_balances=low_stock_balances,
        submitted_purchase_orders=(submitted_purchase_orders),
        unpaid_supplier_invoices=(unpaid_supplier_invoices),
    )


_DASHBOARD_CURRENCY = "UGX"

_OPEN_CUSTOMER_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
)

_OPEN_SUPPLIER_INVOICE_STATUSES = (
    SupplierInvoiceStatus.POSTED,
    SupplierInvoiceStatus.PARTIALLY_PAID,
)


@dataclass(frozen=True, slots=True)
class FinancialDashboardMetrics:
    """Contain permission-aware financial dashboard values."""

    currency: str
    customer_outstanding_balance: Decimal
    supplier_outstanding_liability: Decimal
    overdue_customer_invoices: int
    overdue_supplier_invoices: int


def get_financial_dashboard_metrics(
    *,
    include_customer_finance: bool,
    include_supplier_finance: bool,
    currency: str = _DASHBOARD_CURRENCY,
) -> FinancialDashboardMetrics:
    """Return authorized customer and supplier balances."""

    normalized_currency = currency.strip().upper()

    if len(normalized_currency) != 3 or not normalized_currency.isalpha():
        raise ValueError("Dashboard currency must be a three-letter code.")

    zero = Decimal("0.00")
    today = timezone.localdate()

    customer_outstanding_balance = zero
    supplier_outstanding_liability = zero
    overdue_customer_invoices = 0
    overdue_supplier_invoices = 0

    if include_customer_finance:
        customer_invoices = Invoice.objects.filter(
            status__in=(_OPEN_CUSTOMER_INVOICE_STATUSES),
            currency=normalized_currency,
        )

        customer_invoice_total = (
            customer_invoices.aggregate(amount=Sum("total"))["amount"] or zero
        )

        customer_payment_total = (
            Payment.objects.filter(
                status=PaymentStatus.POSTED,
                invoice__status__in=(_OPEN_CUSTOMER_INVOICE_STATUSES),
                invoice__currency=(normalized_currency),
            ).aggregate(amount=Sum("amount"))["amount"]
            or zero
        )

        customer_outstanding_balance = max(
            customer_invoice_total - customer_payment_total,
            zero,
        )

        overdue_customer_invoices = customer_invoices.filter(due_date__lt=today).count()

    if include_supplier_finance:
        supplier_invoices = SupplierInvoice.objects.filter(
            status__in=(_OPEN_SUPPLIER_INVOICE_STATUSES),
            currency=normalized_currency,
        )

        supplier_invoice_total = (
            supplier_invoices.aggregate(amount=Sum("total"))["amount"] or zero
        )

        supplier_payment_total = (
            SupplierPayment.objects.filter(
                status=SupplierPaymentStatus.POSTED,
                supplier_invoice__status__in=(_OPEN_SUPPLIER_INVOICE_STATUSES),
                supplier_invoice__currency=(normalized_currency),
            ).aggregate(amount=Sum("amount"))["amount"]
            or zero
        )

        supplier_outstanding_liability = max(
            supplier_invoice_total - supplier_payment_total,
            zero,
        )

        overdue_supplier_invoices = supplier_invoices.filter(due_date__lt=today).count()

    return FinancialDashboardMetrics(
        currency=normalized_currency,
        customer_outstanding_balance=(customer_outstanding_balance),
        supplier_outstanding_liability=(supplier_outstanding_liability),
        overdue_customer_invoices=(overdue_customer_invoices),
        overdue_supplier_invoices=(overdue_supplier_invoices),
    )
