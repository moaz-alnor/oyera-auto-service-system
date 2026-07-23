"""Tests for vehicle read and search queries."""

import pytest

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle
from apps.vehicles.selectors import search_vehicles


@pytest.fixture
def actor() -> User:
    """Create an employee for vehicle selector tests."""

    return User.objects.create_user(
        username="vehicle.selector.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.fixture
def owners(
    actor: User,
) -> tuple[Customer, Customer]:
    """Create two vehicle owners."""

    first_owner = Customer.objects.create(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        normalized_phone_number="0700123456",
        created_by=actor,
        updated_by=actor,
    )
    second_owner = Customer.objects.create(
        customer_number="CUS-000002",
        customer_type=CustomerType.INDIVIDUAL,
        name="Grace Namusoke",
        phone_number="0770123456",
        normalized_phone_number="0770123456",
        created_by=actor,
        updated_by=actor,
    )

    return first_owner, second_owner


@pytest.fixture
def vehicles(
    actor: User,
    owners: tuple[Customer, Customer],
) -> tuple[Vehicle, Vehicle]:
    """Create active and inactive vehicles."""

    first_owner, second_owner = owners

    active_vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        is_active=True,
        created_by=actor,
        updated_by=actor,
    )
    inactive_vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000002",
        registration_number="UBE 990Y",
        normalized_registration_number="UBE990Y",
        current_owner=second_owner,
        category=VehicleCategory.COMMERCIAL,
        make="Isuzu",
        model="NPR",
        is_active=False,
        created_by=actor,
        updated_by=actor,
    )

    return active_vehicle, inactive_vehicle


@pytest.mark.django_db
def test_search_finds_formatted_registration(
    vehicles: tuple[Vehicle, Vehicle],
) -> None:
    """Find a registration despite search formatting."""

    active_vehicle, _ = vehicles

    results = search_vehicles(query="ubd-245")

    assert list(results) == [active_vehicle]


@pytest.mark.django_db
def test_search_finds_current_owner_name(
    vehicles: tuple[Vehicle, Vehicle],
) -> None:
    """Find vehicles through current-owner information."""

    active_vehicle, _ = vehicles

    results = search_vehicles(query="Daniel")

    assert list(results) == [active_vehicle]


@pytest.mark.django_db
def test_search_excludes_inactive_vehicles_by_default(
    vehicles: tuple[Vehicle, Vehicle],
) -> None:
    """Hide inactive vehicles from ordinary searches."""

    _, inactive_vehicle = vehicles

    default_results = search_vehicles(query="Isuzu")
    historical_results = search_vehicles(
        query="Isuzu",
        include_inactive=True,
    )

    assert inactive_vehicle not in default_results
    assert inactive_vehicle in historical_results


@pytest.mark.django_db
def test_search_can_filter_by_current_owner(
    vehicles: tuple[Vehicle, Vehicle],
    owners: tuple[Customer, Customer],
) -> None:
    """Return only vehicles belonging to the selected customer."""

    active_vehicle, _ = vehicles
    first_owner, _ = owners

    results = search_vehicles(owner_id=first_owner.pk)

    assert list(results) == [active_vehicle]
