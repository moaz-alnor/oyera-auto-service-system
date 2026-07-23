"""Tests for vehicle-domain models."""

import pytest

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


@pytest.fixture
def actor() -> User:
    """Create an employee for vehicle model tests."""

    return User.objects.create_user(
        username="vehicle.model.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.fixture
def owner(actor: User) -> Customer:
    """Create a customer who owns a vehicle."""

    return Customer.objects.create(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        normalized_phone_number="0700123456",
        created_by=actor,
        updated_by=actor,
    )


@pytest.mark.django_db
def test_vehicle_information_is_normalized(
    actor: User,
    owner: Customer,
) -> None:
    """Normalize registration, make, model, and identifiers."""

    vehicle = Vehicle(
        current_owner=owner,
        registration_number="  ubd-245x  ",
        category=VehicleCategory.SMALL,
        make="  Toyota  ",
        model="  Corolla   Cross ",
        engine_number=" eng 123 ",
        chassis_number=" chs 456 ",
        created_by=actor,
    )

    vehicle.full_clean()

    assert vehicle.registration_number == "UBD-245X"
    assert vehicle.normalized_registration_number == "UBD245X"
    assert vehicle.make == "Toyota"
    assert vehicle.model == "Corolla Cross"
    assert vehicle.engine_number == "ENG 123"
    assert vehicle.chassis_number == "CHS 456"


@pytest.mark.django_db
def test_unsaved_vehicle_has_readable_description(
    actor: User,
    owner: Customer,
) -> None:
    """Display registration, make, and model before saving."""

    vehicle = Vehicle(
        current_owner=owner,
        registration_number="UBD 245X",
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=actor,
    )

    assert str(vehicle) == "UBD 245X — Toyota Corolla"
