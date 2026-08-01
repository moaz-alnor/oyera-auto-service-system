"""Read-only queries for shared operational dashboards."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.billing.constants import InvoiceStatus
from apps.billing.models import Invoice
from apps.inventory.selectors import get_low_stock_items
from apps.jobs.constants import ACTIVE_JOB_STATUSES
from apps.jobs.models import JobCard
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    SupplierInvoiceStatus,
)
from apps.purchasing.models import (
    PurchaseOrder,
    SupplierInvoice,
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
