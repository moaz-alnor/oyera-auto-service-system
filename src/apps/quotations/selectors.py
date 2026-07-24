"""Read-only database queries for quotation workflows."""

from django.db.models import Prefetch, Q, QuerySet

from apps.jobs.constants import JobStatus
from apps.jobs.models import JobCard
from apps.product_catalogue.models import Product
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)
from apps.service_catalogue.models import Service


def search_quotations(
    *,
    query: str = "",
    status: str = "",
    current_only: bool = False,
) -> QuerySet[Quotation]:
    """Return quotations matching the supplied filters.

    Args:
        query: Quotation number, job number, customer, or vehicle.
        status: Optional exact quotation-status filter.
        current_only: Whether to return only current revisions.

    Returns:
        A lazily evaluated quotation queryset.
    """

    quotations = Quotation.objects.select_related(
        "job_card",
        "job_card__customer",
        "job_card__vehicle",
        "created_by",
        "updated_by",
        "decision_recorded_by",
    )

    if status:
        quotations = quotations.filter(status=status)

    if current_only:
        quotations = quotations.filter(is_current=True)

    search_value = query.strip()

    if not search_value:
        return quotations

    return quotations.filter(
        Q(quotation_number__icontains=search_value)
        | Q(job_card__job_number__icontains=search_value)
        | Q(job_card__customer_name_snapshot__icontains=(search_value))
        | Q(job_card__vehicle_registration_snapshot__icontains=(search_value))
        | Q(job_card__customer_phone_snapshot__icontains=(search_value))
    )


def get_quotation_by_id(
    *,
    quotation_id: int,
) -> Quotation:
    """Return one quotation with all display relationships loaded.

    Args:
        quotation_id: Primary key of the requested quotation.

    Returns:
        The matching quotation.

    Raises:
        Quotation.DoesNotExist: If the quotation does not exist.
    """

    service_lines = QuotationServiceLine.objects.select_related(
        "service",
        "created_by",
    ).order_by(
        "position",
        "pk",
    )
    product_lines = QuotationProductLine.objects.select_related(
        "product",
        "created_by",
    ).order_by(
        "position",
        "pk",
    )

    return (
        Quotation.objects.select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
            "created_by",
            "updated_by",
            "decision_recorded_by",
        )
        .prefetch_related(
            Prefetch(
                "service_lines",
                queryset=service_lines,
            ),
            Prefetch(
                "product_lines",
                queryset=product_lines,
            ),
        )
        .get(pk=quotation_id)
    )


def get_current_quotation_for_job(
    *,
    job_card_id: int,
) -> Quotation | None:
    """Return the current quotation revision for one job."""

    return (
        Quotation.objects.select_related(
            "job_card",
            "created_by",
            "updated_by",
        )
        .filter(
            job_card_id=job_card_id,
            is_current=True,
        )
        .first()
    )


def get_quotation_history_for_job(
    *,
    job_card_id: int,
) -> QuerySet[Quotation]:
    """Return every quotation revision for one job."""

    return (
        Quotation.objects.filter(job_card_id=job_card_id)
        .select_related(
            "created_by",
            "updated_by",
            "decision_recorded_by",
        )
        .order_by(
            "-revision_number",
            "-created_at",
        )
    )


def get_jobs_available_for_quotation() -> QuerySet[JobCard]:
    """Return active jobs without a current quotation."""

    return (
        JobCard.objects.exclude(status=JobStatus.CANCELLED)
        .exclude(quotations__is_current=True)
        .select_related(
            "customer",
            "vehicle",
        )
        .order_by(
            "-arrival_at",
            "-created_at",
        )
    )


def get_services_available_for_quotation(
    *,
    quotation: Quotation,
) -> QuerySet[Service]:
    """Return applicable active services with matching prices."""

    vehicle_category = quotation.job_card.vehicle.category

    return (
        Service.objects.filter(
            is_active=True,
            applicabilities__vehicle_category=(vehicle_category),
            price_history__effective_until__isnull=True,
            price_history__currency=quotation.currency,
        )
        .distinct()
        .order_by(
            "name",
            "code",
        )
    )


def get_products_available_for_quotation(
    *,
    quotation: Quotation,
) -> QuerySet[Product]:
    """Return active products with matching current prices."""

    return (
        Product.objects.filter(
            is_active=True,
            category__is_active=True,
            price_history__effective_until__isnull=True,
            price_history__currency=quotation.currency,
        )
        .select_related("category")
        .distinct()
        .order_by(
            "name",
            "sku",
        )
    )
