"""Tests for service-catalogue read queries."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
    ServicePrice,
)
from apps.service_catalogue.selectors import (
    get_current_service_price,
    search_services,
)
from apps.vehicles.constants import VehicleCategory


@pytest.fixture
def actor() -> User:
    """Create an employee for catalogue selector tests."""

    return User.objects.create_user(
        username="catalogue.selector.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.fixture
def services(
    actor: User,
) -> tuple[Service, Service]:
    """Create active and inactive catalogue services."""

    active_service = Service.objects.create(
        code="OIL-CHANGE",
        normalized_code="OILCHANGE",
        name="Engine Oil Change",
        description="Replace the engine oil.",
        created_by=actor,
        updated_by=actor,
    )
    ServiceApplicability.objects.create(
        service=active_service,
        vehicle_category=VehicleCategory.SMALL,
    )
    ServicePrice.objects.create(
        service=active_service,
        amount=Decimal("75000.00"),
        currency="UGX",
        changed_by=actor,
    )

    inactive_service = Service.objects.create(
        code="WHEEL-ALIGNMENT",
        normalized_code="WHEELALIGNMENT",
        name="Wheel Alignment",
        is_active=False,
        created_by=actor,
        updated_by=actor,
    )
    ServiceApplicability.objects.create(
        service=inactive_service,
        vehicle_category=VehicleCategory.COMMERCIAL,
    )

    return active_service, inactive_service


@pytest.mark.django_db
def test_search_finds_formatted_service_code(
    services: tuple[Service, Service],
) -> None:
    """Find a service despite code formatting."""

    active_service, _ = services

    results = search_services(query="oil change")

    assert list(results) == [active_service]


@pytest.mark.django_db
def test_search_filters_by_vehicle_category(
    services: tuple[Service, Service],
) -> None:
    """Return services applicable to the selected category."""

    active_service, _ = services

    results = search_services(
        vehicle_category=VehicleCategory.SMALL,
    )

    assert list(results) == [active_service]


@pytest.mark.django_db
def test_search_excludes_inactive_services_by_default(
    services: tuple[Service, Service],
) -> None:
    """Hide inactive services from ordinary searches."""

    _, inactive_service = services

    default_results = search_services(query="Wheel Alignment")
    historical_results = search_services(
        query="Wheel Alignment",
        include_inactive=True,
    )

    assert inactive_service not in default_results
    assert inactive_service in historical_results


@pytest.mark.django_db
def test_current_price_selector_returns_open_price(
    services: tuple[Service, Service],
) -> None:
    """Return the service's open-ended current price."""

    active_service, _ = services

    price = get_current_service_price(service_id=active_service.pk)

    assert price is not None
    assert price.amount == Decimal("75000.00")
