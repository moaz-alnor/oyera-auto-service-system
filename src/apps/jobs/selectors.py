"""Read-only database queries for job-card workflows."""

from django.db.models import Q, QuerySet

from apps.customers.models import Customer
from apps.jobs.models import (
    Inspection,
    JobCard,
    JobNote,
    VehicleRelease,
)
from apps.vehicles.models import Vehicle


def search_job_cards(
    *,
    query: str = "",
    status: str = "",
    priority: str = "",
) -> QuerySet[JobCard]:
    """Return job cards matching the supplied search filters.

    Args:
        query: Job number, customer, vehicle, or complaint text.
        status: Optional exact job-status filter.
        priority: Optional exact priority filter.

    Returns:
        A lazily evaluated job-card queryset.
    """

    job_cards = JobCard.objects.select_related(
        "customer",
        "vehicle",
        "created_by",
        "updated_by",
    )

    if status:
        job_cards = job_cards.filter(status=status)

    if priority:
        job_cards = job_cards.filter(priority=priority)

    search_value = query.strip()

    if not search_value:
        return job_cards

    return job_cards.filter(
        Q(job_number__icontains=search_value)
        | Q(customer_name_snapshot__icontains=search_value)
        | Q(customer_phone_snapshot__icontains=search_value)
        | Q(vehicle_registration_snapshot__icontains=search_value)
        | Q(vehicle_make_snapshot__icontains=search_value)
        | Q(vehicle_model_snapshot__icontains=search_value)
        | Q(customer_complaint__icontains=search_value)
    )


def get_job_card_by_id(
    *,
    job_card_id: int,
) -> JobCard:
    """Return one job card with its related visit records.

    Args:
        job_card_id: Primary key of the requested job card.

    Returns:
        The matching job card.

    Raises:
        JobCard.DoesNotExist: If the record does not exist.
    """

    return JobCard.objects.select_related(
        "customer",
        "vehicle",
        "created_by",
        "updated_by",
    ).get(pk=job_card_id)


def get_job_inspections(
    *,
    job_card_id: int,
) -> QuerySet[Inspection]:
    """Return inspections for one job, newest first."""

    return (
        Inspection.objects.filter(job_card_id=job_card_id)
        .select_related(
            "job_card",
            "inspected_by",
        )
        .order_by(
            "-inspected_at",
            "-created_at",
        )
    )


def get_job_notes(
    *,
    job_card_id: int,
) -> QuerySet[JobNote]:
    """Return append-only notes for one job, newest first."""

    return (
        JobNote.objects.filter(job_card_id=job_card_id)
        .select_related(
            "job_card",
            "created_by",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_active_customers() -> QuerySet[Customer]:
    """Return active customers available for job intake."""

    return Customer.objects.filter(is_active=True).order_by(
        "name",
        "customer_number",
    )


def get_active_vehicles() -> QuerySet[Vehicle]:
    """Return active vehicles belonging to active customers."""

    return (
        Vehicle.objects.filter(
            is_active=True,
            current_owner__is_active=True,
        )
        .select_related("current_owner")
        .order_by(
            "registration_number",
            "vehicle_number",
        )
    )


def get_active_vehicles_for_customer(
    *,
    customer_id: int,
) -> QuerySet[Vehicle]:
    """Return active vehicles owned by one active customer."""

    return get_active_vehicles().filter(current_owner_id=customer_id)


def vehicle_release_list_queryset() -> QuerySet[VehicleRelease]:
    """Return vehicle releases with handover relations."""

    return (
        VehicleRelease.objects.select_related(
            "job_card",
            "job_card__customer",
            "job_card__vehicle",
            "released_by",
            "payment_override_by",
        )
        .all()
        .order_by(
            "-released_at",
            "-pk",
        )
    )


def get_vehicle_release_by_id(
    *,
    release_id: int,
) -> VehicleRelease:
    """Return one vehicle release by primary key."""

    return vehicle_release_list_queryset().get(pk=release_id)


def get_vehicle_release_for_job(
    *,
    job_card_id: int,
) -> VehicleRelease:
    """Return the handover record for one job card."""

    return vehicle_release_list_queryset().get(job_card_id=job_card_id)
