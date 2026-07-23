"""Read-only database queries for service-catalogue information."""

from django.db.models import Q, QuerySet

from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
    ServicePrice,
)
from apps.service_catalogue.normalization import (
    normalize_service_code_search,
)


def search_services(
    *,
    query: str = "",
    include_inactive: bool = False,
    vehicle_category: str = "",
) -> QuerySet[Service]:
    """Return services matching catalogue search criteria.

    Args:
        query: Full or partial code, name, or description.
        include_inactive: Whether inactive services are included.
        vehicle_category: Optional applicable vehicle category.

    Returns:
        A lazily evaluated service queryset.
    """

    services = Service.objects.select_related(
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        services = services.filter(is_active=True)

    if vehicle_category:
        services = services.filter(applicabilities__vehicle_category=vehicle_category)

    search_value = query.strip()

    if not search_value:
        return services.distinct()

    normalized_code = normalize_service_code_search(search_value)

    search_filter = (
        Q(code__icontains=search_value)
        | Q(name__icontains=search_value)
        | Q(description__icontains=search_value)
    )

    if normalized_code:
        search_filter |= Q(normalized_code__icontains=normalized_code)

    return services.filter(search_filter).distinct()


def get_service_by_id(
    *,
    service_id: int,
) -> Service:
    """Return one service with employee information.

    Args:
        service_id: Primary key of the requested service.

    Returns:
        The matching service.

    Raises:
        Service.DoesNotExist: If no matching service exists.
    """

    return Service.objects.select_related(
        "created_by",
        "updated_by",
    ).get(pk=service_id)


def get_service_applicabilities(
    *,
    service_id: int,
) -> QuerySet[ServiceApplicability]:
    """Return vehicle categories supported by a service."""

    return (
        ServiceApplicability.objects.filter(service_id=service_id)
        .select_related("service")
        .order_by("vehicle_category")
    )


def get_current_service_price(
    *,
    service_id: int,
) -> ServicePrice | None:
    """Return the current open-ended service price."""

    return (
        ServicePrice.objects.filter(
            service_id=service_id,
            effective_until__isnull=True,
        )
        .select_related(
            "service",
            "changed_by",
        )
        .first()
    )


def get_service_price_history(
    *,
    service_id: int,
) -> QuerySet[ServicePrice]:
    """Return all price periods from newest to oldest."""

    return (
        ServicePrice.objects.filter(service_id=service_id)
        .select_related(
            "service",
            "changed_by",
        )
        .order_by(
            "-effective_from",
            "-created_at",
        )
    )
