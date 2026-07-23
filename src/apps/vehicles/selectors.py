"""Read-only database queries for vehicle information."""

from django.db.models import Q, QuerySet

from apps.vehicles.models import Vehicle, VehicleOwnership
from apps.vehicles.normalization import (
    normalize_registration_search,
)


def search_vehicles(
    *,
    query: str = "",
    include_inactive: bool = False,
    owner_id: int | None = None,
) -> QuerySet[Vehicle]:
    """Return vehicles matching operational search criteria.

    Vehicles can be found by vehicle number, registration number, make,
    model, or current-owner information.

    Args:
        query: Full or partial vehicle search value.
        include_inactive: Whether inactive vehicles should be included.
        owner_id: Optional current-owner customer primary key.

    Returns:
        A lazily evaluated vehicle queryset.
    """

    vehicles = Vehicle.objects.select_related(
        "current_owner",
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        vehicles = vehicles.filter(is_active=True)

    if owner_id is not None:
        vehicles = vehicles.filter(current_owner_id=owner_id)

    search_value = query.strip()

    if not search_value:
        return vehicles

    registration_search = normalize_registration_search(search_value)

    search_filter = (
        Q(vehicle_number__icontains=search_value)
        | Q(registration_number__icontains=search_value)
        | Q(make__icontains=search_value)
        | Q(model__icontains=search_value)
        | Q(current_owner__name__icontains=search_value)
        | Q(current_owner__customer_number__icontains=(search_value))
    )

    if registration_search:
        search_filter |= Q(
            normalized_registration_number__icontains=(registration_search)
        )

    return vehicles.filter(search_filter).distinct()


def get_vehicle_by_id(
    *,
    vehicle_id: int,
) -> Vehicle:
    """Return one vehicle with ownership and employee information.

    Args:
        vehicle_id: Primary key of the requested vehicle.

    Returns:
        The matching vehicle.

    Raises:
        Vehicle.DoesNotExist: If no matching vehicle exists.
    """

    return Vehicle.objects.select_related(
        "current_owner",
        "created_by",
        "updated_by",
    ).get(pk=vehicle_id)


def get_vehicle_ownership_history(
    *,
    vehicle_id: int,
) -> QuerySet[VehicleOwnership]:
    """Return a vehicle's ownership history.

    Args:
        vehicle_id: Primary key of the requested vehicle.

    Returns:
        Ownership records ordered from newest to oldest.
    """

    return (
        VehicleOwnership.objects.filter(vehicle_id=vehicle_id)
        .select_related(
            "owner",
            "changed_by",
        )
        .order_by(
            "-started_at",
            "-created_at",
        )
    )
