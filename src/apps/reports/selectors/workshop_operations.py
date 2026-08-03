"""Read-only selectors for workshop operations reports."""

from dataclasses import dataclass
from datetime import (
    datetime,
    time,
    timedelta,
)

from django.db.models import Q
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
from apps.workshop.models import WorkOrder


@dataclass(frozen=True, slots=True)
class WorkshopOperationsSummary:
    """Contain workshop activity totals for one period."""

    vehicles_received_count: int
    urgent_job_count: int
    cancelled_job_count: int
    work_orders_created_count: int
    work_orders_started_count: int
    work_orders_completed_count: int
    vehicles_released_count: int
    payment_override_release_count: int


@dataclass(frozen=True, slots=True)
class WorkshopOperationsReport:
    """Contain workshop summaries and audit records."""

    summary: WorkshopOperationsSummary
    job_cards: tuple[JobCard, ...]
    work_orders: tuple[WorkOrder, ...]
    releases: tuple[VehicleRelease, ...]


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


def get_workshop_operations_report(
    *,
    date_range: ReportDateRange,
) -> WorkshopOperationsReport:
    """Return workshop activity for a reporting period."""

    start_at, end_at = _local_date_bounds(date_range=date_range)

    job_cards = tuple(
        JobCard.objects.filter(
            arrival_at__gte=start_at,
            arrival_at__lt=end_at,
        )
        .select_related(
            "customer",
            "vehicle",
        )
        .order_by(
            "-arrival_at",
            "-pk",
        )
    )

    work_orders = tuple(
        WorkOrder.objects.filter(
            Q(
                created_at__gte=start_at,
                created_at__lt=end_at,
            )
            | Q(
                started_at__gte=start_at,
                started_at__lt=end_at,
            )
            | Q(
                completed_at__gte=start_at,
                completed_at__lt=end_at,
            )
        )
        .select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
            "approved_quotation",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )

    releases = tuple(
        VehicleRelease.objects.filter(
            released_at__gte=start_at,
            released_at__lt=end_at,
        )
        .select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
            "released_by",
            "payment_override_by",
        )
        .order_by(
            "-released_at",
            "-pk",
        )
    )

    summary = WorkshopOperationsSummary(
        vehicles_received_count=len(job_cards),
        urgent_job_count=sum(
            job_card.priority == JobPriority.URGENT for job_card in job_cards
        ),
        cancelled_job_count=sum(
            job_card.status == JobStatus.CANCELLED for job_card in job_cards
        ),
        work_orders_created_count=sum(
            _is_within_period(
                value=work_order.created_at,
                start_at=start_at,
                end_at=end_at,
            )
            for work_order in work_orders
        ),
        work_orders_started_count=sum(
            _is_within_period(
                value=work_order.started_at,
                start_at=start_at,
                end_at=end_at,
            )
            for work_order in work_orders
        ),
        work_orders_completed_count=sum(
            _is_within_period(
                value=work_order.completed_at,
                start_at=start_at,
                end_at=end_at,
            )
            for work_order in work_orders
        ),
        vehicles_released_count=len(releases),
        payment_override_release_count=sum(
            release.payment_override for release in releases
        ),
    )

    return WorkshopOperationsReport(
        summary=summary,
        job_cards=job_cards,
        work_orders=work_orders,
        releases=releases,
    )
