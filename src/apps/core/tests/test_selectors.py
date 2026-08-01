"""Tests for operational dashboard selectors."""

from unittest.mock import (
    MagicMock,
    call,
    patch,
)

from apps.billing.constants import InvoiceStatus
from apps.core.selectors import (
    OperationalDashboardMetrics,
    get_operational_dashboard_metrics,
)
from apps.jobs.constants import ACTIVE_JOB_STATUSES


def test_dashboard_metrics_return_expected_counts() -> None:
    """Return counts supplied by the business queries."""

    vehicle_count = MagicMock()
    vehicle_count.count.return_value = 4

    active_job_count = MagicMock()
    active_job_count.count.return_value = 7

    invoice_count = MagicMock()
    invoice_count.count.return_value = 3

    with (
        patch(
            "apps.core.selectors.JobCard.objects.filter",
            side_effect=(
                vehicle_count,
                active_job_count,
            ),
        ) as job_filter,
        patch(
            "apps.core.selectors.Invoice.objects.filter",
            return_value=invoice_count,
        ) as invoice_filter,
    ):
        metrics = get_operational_dashboard_metrics()

    assert metrics == OperationalDashboardMetrics(
        vehicles_received_today=4,
        open_job_cards=7,
        invoices_awaiting_payment=3,
    )

    assert job_filter.call_count == 2

    intake_filters = job_filter.call_args_list[0].kwargs

    assert "arrival_at__gte" in intake_filters
    assert "arrival_at__lt" in intake_filters

    assert job_filter.call_args_list[1] == call(status__in=ACTIVE_JOB_STATUSES)

    invoice_filter.assert_called_once_with(
        status__in=(
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
        )
    )


def test_dashboard_metrics_are_immutable() -> None:
    """Keep dashboard result values immutable."""

    metrics = OperationalDashboardMetrics(
        vehicles_received_today=1,
        open_job_cards=2,
        invoices_awaiting_payment=3,
    )

    assert metrics.vehicles_received_today == 1
    assert metrics.open_job_cards == 2
    assert metrics.invoices_awaiting_payment == 3
