"""Tests for workshop operations report selectors."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.jobs.constants import (
    JobPriority,
    JobStatus,
)
from apps.jobs.models import (
    JobCard,
    VehicleRelease,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.workshop_operations import (
    WorkshopOperationsSummary,
    get_workshop_operations_report,
)
from apps.workshop.constants import (
    WorkOrderStatus,
)
from apps.workshop.models import WorkOrder
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


@pytest.mark.django_db
def test_workshop_report_calculates_activity(
    workshop_execution_context: (WorkshopExecutionContext),
) -> None:
    """Calculate intake, workflow, and release activity."""

    context = workshop_execution_context
    now = timezone.now()
    today = timezone.localdate()

    JobCard.objects.filter(pk=context.job_card.pk).update(
        priority=JobPriority.URGENT,
        status=JobStatus.RELEASED,
    )

    WorkOrder.objects.filter(pk=context.work_order.pk).update(
        status=WorkOrderStatus.COMPLETED,
        started_at=(now - timedelta(hours=3)),
        completed_at=(now - timedelta(hours=1)),
    )

    context.job_card.refresh_from_db()

    release = VehicleRelease.objects.create(
        release_number="REL-REPORT-001",
        job_card=context.job_card,
        released_at=now,
        final_mileage=(context.job_card.arrival_mileage),
        final_condition="Vehicle released.",
        received_by_name="Daniel Kato",
        invoice_number_snapshot=("INV-REPORT-001"),
        invoice_status_snapshot="PAID",
        invoice_currency_snapshot="UGX",
        invoice_total_snapshot=(Decimal("0.00")),
        paid_amount_snapshot=Decimal("0.00"),
        outstanding_amount_snapshot=(Decimal("0.00")),
        payment_override=False,
        released_by=context.manager,
    )

    report = get_workshop_operations_report(
        date_range=ReportDateRange(
            start_date=today,
            end_date=today,
        )
    )

    assert report.summary == (
        WorkshopOperationsSummary(
            vehicles_received_count=1,
            urgent_job_count=1,
            cancelled_job_count=0,
            work_orders_created_count=1,
            work_orders_started_count=1,
            work_orders_completed_count=1,
            vehicles_released_count=1,
            payment_override_release_count=0,
        )
    )

    assert report.job_cards == (context.job_card,)
    assert report.work_orders[0].pk == (context.work_order.pk)
    assert report.releases == (release,)


@pytest.mark.django_db
def test_workshop_report_counts_cancelled_jobs(
    workshop_execution_context: (WorkshopExecutionContext),
) -> None:
    """Count cancelled vehicle visits in the period."""

    context = workshop_execution_context
    today = timezone.localdate()

    JobCard.objects.filter(pk=context.job_card.pk).update(
        status=JobStatus.CANCELLED,
        cancellation_reason=("Customer cancelled the repair."),
    )

    report = get_workshop_operations_report(
        date_range=ReportDateRange(
            start_date=today,
            end_date=today,
        )
    )

    assert report.summary.cancelled_job_count == 1
    assert report.summary.vehicles_received_count == 1


@pytest.mark.django_db
def test_workshop_report_excludes_outside_period(
    workshop_execution_context: (WorkshopExecutionContext),
) -> None:
    """Exclude activity outside the selected range."""

    context = workshop_execution_context
    today = timezone.localdate()

    old_timestamp = timezone.now() - timedelta(days=10)

    JobCard.objects.filter(pk=context.job_card.pk).update(arrival_at=old_timestamp)

    WorkOrder.objects.filter(pk=context.work_order.pk).update(
        created_at=old_timestamp,
    )

    report = get_workshop_operations_report(
        date_range=ReportDateRange(
            start_date=today,
            end_date=today,
        )
    )

    assert report.summary == (
        WorkshopOperationsSummary(
            vehicles_received_count=0,
            urgent_job_count=0,
            cancelled_job_count=0,
            work_orders_created_count=0,
            work_orders_started_count=0,
            work_orders_completed_count=0,
            vehicles_released_count=0,
            payment_override_release_count=0,
        )
    )

    assert report.job_cards == ()
    assert report.work_orders == ()
    assert report.releases == ()


@pytest.mark.django_db
def test_workshop_report_uses_three_queries(
    workshop_execution_context: (WorkshopExecutionContext),
    django_assert_num_queries,
) -> None:
    """Keep workshop reporting query-bounded."""

    context = workshop_execution_context
    today = timezone.localdate()

    with django_assert_num_queries(3):
        report = get_workshop_operations_report(
            date_range=ReportDateRange(
                start_date=today,
                end_date=today,
            )
        )

        assert report.job_cards[0].customer.name == context.job_card.customer.name
        assert report.job_cards[0].vehicle.registration_number == (
            context.job_card.vehicle.registration_number
        )
        assert report.work_orders[0].job_card.job_number == context.job_card.job_number

    assert report.summary.vehicles_received_count == 1
