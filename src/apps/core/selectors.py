"""Read-only queries for shared operational dashboards."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.billing.constants import InvoiceStatus
from apps.billing.models import Invoice
from apps.jobs.constants import ACTIVE_JOB_STATUSES
from apps.jobs.models import JobCard


@dataclass(frozen=True, slots=True)
class OperationalDashboardMetrics:
    """Contain the primary operational dashboard values."""

    vehicles_received_today: int
    open_job_cards: int
    invoices_awaiting_payment: int


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

    invoices_awaiting_payment = Invoice.objects.filter(
        status__in=(
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
        )
    ).count()

    return OperationalDashboardMetrics(
        vehicles_received_today=(vehicles_received_today),
        open_job_cards=open_job_cards,
        invoices_awaiting_payment=(invoices_awaiting_payment),
    )
