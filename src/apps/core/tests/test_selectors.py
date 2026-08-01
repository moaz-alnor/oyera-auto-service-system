"""Tests for operational dashboard selectors."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import (
    MagicMock,
    call,
    patch,
)

import pytest

from apps.billing.constants import InvoiceStatus
from apps.core.selectors import (
    _ACTIVE_WORK_ORDER_STATUSES,
    _RELEASE_READY_INVOICE_STATUSES,
    OperationalDashboardAlerts,
    OperationalDashboardMetrics,
    get_operational_dashboard_alerts,
    get_operational_dashboard_metrics,
)
from apps.jobs.constants import ACTIVE_JOB_STATUSES
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    SupplierInvoiceStatus,
)
from apps.workshop.constants import WorkOrderStatus


def test_dashboard_metrics_return_expected_counts() -> None:
    """Return counts supplied by business queries."""

    vehicle_count = MagicMock()
    vehicle_count.count.return_value = 4

    active_job_count = MagicMock()
    active_job_count.count.return_value = 7

    release_ready_count = MagicMock()
    release_ready_count.count.return_value = 2

    work_order_count = MagicMock()
    work_order_count.count.return_value = 5

    invoice_count = MagicMock()
    invoice_count.count.return_value = 3

    purchase_order_count = MagicMock()
    purchase_order_count.count.return_value = 6

    supplier_invoice_count = MagicMock()
    supplier_invoice_count.count.return_value = 4

    with (
        patch(
            "apps.core.selectors.JobCard.objects.filter",
            side_effect=(
                vehicle_count,
                active_job_count,
                release_ready_count,
            ),
        ) as job_filter,
        patch(
            "apps.core.selectors.WorkOrder.objects.filter",
            return_value=work_order_count,
        ) as work_order_filter,
        patch(
            "apps.core.selectors.Invoice.objects.filter",
            return_value=invoice_count,
        ) as invoice_filter,
        patch(
            "apps.core.selectors.PurchaseOrder.objects.filter",
            return_value=purchase_order_count,
        ) as purchase_order_filter,
        patch(
            "apps.core.selectors.SupplierInvoice.objects.filter",
            return_value=supplier_invoice_count,
        ) as supplier_invoice_filter,
        patch(
            "apps.core.selectors.get_low_stock_items",
            return_value=[
                object(),
                object(),
                object(),
            ],
        ) as low_stock_selector,
    ):
        metrics = get_operational_dashboard_metrics()

    assert metrics == OperationalDashboardMetrics(
        vehicles_received_today=4,
        open_job_cards=7,
        active_work_orders=5,
        vehicles_ready_for_release=2,
        invoices_awaiting_payment=3,
        low_stock_items=3,
        purchase_orders_awaiting_approval=6,
        supplier_invoices_awaiting_payment=4,
    )

    assert job_filter.call_count == 3

    intake_filters = job_filter.call_args_list[0].kwargs

    assert "arrival_at__gte" in intake_filters
    assert "arrival_at__lt" in intake_filters

    assert job_filter.call_args_list[1] == call(status__in=ACTIVE_JOB_STATUSES)

    assert job_filter.call_args_list[2] == call(
        status__in=ACTIVE_JOB_STATUSES,
        work_order__status=(WorkOrderStatus.COMPLETED),
        work_order__invoice__status__in=(_RELEASE_READY_INVOICE_STATUSES),
        vehicle_release__isnull=True,
    )

    work_order_filter.assert_called_once_with(status__in=_ACTIVE_WORK_ORDER_STATUSES)

    invoice_filter.assert_called_once_with(
        status__in=(
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
        )
    )

    purchase_order_filter.assert_called_once_with(status=PurchaseOrderStatus.SUBMITTED)

    supplier_invoice_filter.assert_called_once_with(
        status__in=(
            SupplierInvoiceStatus.POSTED,
            SupplierInvoiceStatus.PARTIALLY_PAID,
        )
    )

    low_stock_selector.assert_called_once_with()


def test_dashboard_status_groups_exclude_closed_states() -> None:
    """Exclude completed, cancelled and void records."""

    assert WorkOrderStatus.COMPLETED not in _ACTIVE_WORK_ORDER_STATUSES
    assert WorkOrderStatus.CANCELLED not in _ACTIVE_WORK_ORDER_STATUSES

    assert InvoiceStatus.DRAFT not in _RELEASE_READY_INVOICE_STATUSES
    assert InvoiceStatus.VOIDED not in _RELEASE_READY_INVOICE_STATUSES


def test_dashboard_metrics_are_immutable() -> None:
    """Keep dashboard result values immutable."""

    metrics = OperationalDashboardMetrics(
        vehicles_received_today=1,
        open_job_cards=2,
        active_work_orders=3,
        vehicles_ready_for_release=4,
        invoices_awaiting_payment=5,
        low_stock_items=6,
        purchase_orders_awaiting_approval=7,
        supplier_invoices_awaiting_payment=8,
    )

    assert metrics.vehicles_received_today == 1
    assert metrics.open_job_cards == 2
    assert metrics.active_work_orders == 3
    assert metrics.vehicles_ready_for_release == 4
    assert metrics.invoices_awaiting_payment == 5
    assert metrics.low_stock_items == 6
    assert metrics.purchase_orders_awaiting_approval == 7
    assert metrics.supplier_invoices_awaiting_payment == 8


def test_dashboard_alerts_return_limited_records() -> None:
    """Return prioritised records for dashboard queues."""

    release_job = object()
    purchase_order = object()
    supplier_invoice = object()

    release_queryset = MagicMock()
    release_ordered = release_queryset.select_related.return_value.order_by.return_value
    release_ordered.__getitem__.return_value = [release_job]

    purchase_order_queryset = MagicMock()
    purchase_order_ordered = (
        purchase_order_queryset.select_related.return_value.order_by.return_value
    )
    purchase_order_ordered.__getitem__.return_value = [purchase_order]

    supplier_invoice_queryset = MagicMock()
    supplier_invoice_ordered = (
        supplier_invoice_queryset.select_related.return_value.order_by.return_value
    )
    supplier_invoice_ordered.__getitem__.return_value = [supplier_invoice]

    high_balance = SimpleNamespace(
        available_quantity=Decimal("2.000"),
        inventory_item=SimpleNamespace(product=SimpleNamespace(name="Oil Filter")),
    )
    urgent_balance = SimpleNamespace(
        available_quantity=Decimal("0.000"),
        inventory_item=SimpleNamespace(product=SimpleNamespace(name="Brake Pad")),
    )

    with (
        patch(
            "apps.core.selectors.JobCard.objects.filter",
            return_value=release_queryset,
        ),
        patch(
            "apps.core.selectors.PurchaseOrder.objects.filter",
            return_value=(purchase_order_queryset),
        ),
        patch(
            "apps.core.selectors.SupplierInvoice.objects.filter",
            return_value=(supplier_invoice_queryset),
        ),
        patch(
            "apps.core.selectors.get_low_stock_items",
            return_value=[
                high_balance,
                urgent_balance,
            ],
        ),
    ):
        alerts = get_operational_dashboard_alerts(limit=1)

    assert alerts == OperationalDashboardAlerts(
        release_ready_jobs=(release_job,),
        low_stock_balances=(urgent_balance,),
        submitted_purchase_orders=(purchase_order,),
        unpaid_supplier_invoices=(supplier_invoice,),
    )


def test_dashboard_alerts_reject_invalid_limit() -> None:
    """Reject an empty or negative queue limit."""

    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        get_operational_dashboard_alerts(limit=0)
