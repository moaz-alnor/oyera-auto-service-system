"""Tests for vehicle application services."""

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import VehicleOwnership
from apps.vehicles.services.vehicles import (
    RegisterVehicleCommand,
    TransferVehicleOwnershipCommand,
    register_vehicle,
    transfer_vehicle_ownership,
)


def create_customer(
    *,
    actor: User,
    number: str,
    name: str,
    phone: str,
) -> Customer:
    """Create a customer for a vehicle service test."""

    return Customer.objects.create(
        customer_number=number,
        customer_type=CustomerType.INDIVIDUAL,
        name=name,
        phone_number=phone,
        normalized_phone_number=phone,
        created_by=actor,
        updated_by=actor,
    )


@pytest.mark.django_db
def test_receptionist_can_register_vehicle() -> None:
    """Register a vehicle with an initial ownership record."""

    ensure_default_roles()

    receptionist = User.objects.create_user(
        username="vehicle.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    owner = create_customer(
        actor=receptionist,
        number="CUS-000001",
        name="Daniel Kato",
        phone="0700123456",
    )

    vehicle = register_vehicle(
        actor=receptionist,
        command=RegisterVehicleCommand(
            owner_id=owner.pk,
            registration_number="UBD-245X",
            category=VehicleCategory.SMALL,
            make="Toyota",
            model="Corolla",
            year=2020,
            current_mileage=45000,
        ),
    )

    ownership = VehicleOwnership.objects.get(
        vehicle=vehicle,
        ended_at__isnull=True,
    )

    assert vehicle.vehicle_number == "VEH-000001"
    assert vehicle.normalized_registration_number == "UBD245X"
    assert vehicle.current_owner == owner
    assert ownership.owner == owner


@pytest.mark.django_db
def test_duplicate_registration_is_rejected() -> None:
    """Reject differently formatted versions of one registration."""

    ensure_default_roles()

    receptionist = User.objects.create_user(
        username="duplicate.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    owner = create_customer(
        actor=receptionist,
        number="CUS-000001",
        name="Daniel Kato",
        phone="0700123456",
    )

    register_vehicle(
        actor=receptionist,
        command=RegisterVehicleCommand(
            owner_id=owner.pk,
            registration_number="UBD 245X",
            category=VehicleCategory.SMALL,
            make="Toyota",
            model="Corolla",
        ),
    )

    with pytest.raises(ValidationError):
        register_vehicle(
            actor=receptionist,
            command=RegisterVehicleCommand(
                owner_id=owner.pk,
                registration_number="ubd-245x",
                category=VehicleCategory.SMALL,
                make="Toyota",
                model="Corolla",
            ),
        )


@pytest.mark.django_db
def test_technician_cannot_register_vehicle() -> None:
    """Reject vehicle registration by a technician."""

    ensure_default_roles()

    administrator = User.objects.create_user(
        username="vehicle.owner.creator",
        password="Strong-Test-Password-2026",
    )
    administrator.groups.add(Group.objects.get(name=RoleName.ADMINISTRATOR.value))

    technician = User.objects.create_user(
        username="vehicle.technician",
        password="Strong-Test-Password-2026",
    )
    technician.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    owner = create_customer(
        actor=administrator,
        number="CUS-000001",
        name="Daniel Kato",
        phone="0700123456",
    )

    with pytest.raises(PermissionDenied):
        register_vehicle(
            actor=technician,
            command=RegisterVehicleCommand(
                owner_id=owner.pk,
                registration_number="UBD 245X",
                category=VehicleCategory.SMALL,
                make="Toyota",
                model="Corolla",
            ),
        )


@pytest.mark.django_db
def test_receptionist_can_transfer_vehicle_ownership() -> None:
    """Close the previous ownership and create a new active one."""

    ensure_default_roles()

    receptionist = User.objects.create_user(
        username="transfer.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    first_owner = create_customer(
        actor=receptionist,
        number="CUS-000001",
        name="Daniel Kato",
        phone="0700123456",
    )
    second_owner = create_customer(
        actor=receptionist,
        number="CUS-000002",
        name="Grace Namusoke",
        phone="0770123456",
    )

    vehicle = register_vehicle(
        actor=receptionist,
        command=RegisterVehicleCommand(
            owner_id=first_owner.pk,
            registration_number="UBD 245X",
            category=VehicleCategory.SMALL,
            make="Toyota",
            model="Corolla",
        ),
    )

    transferred_vehicle = transfer_vehicle_ownership(
        actor=receptionist,
        vehicle_id=vehicle.pk,
        command=TransferVehicleOwnershipCommand(
            new_owner_id=second_owner.pk,
            notes="Vehicle sold to the new owner.",
        ),
    )

    ownership_history = VehicleOwnership.objects.filter(vehicle=vehicle).order_by(
        "started_at"
    )

    assert transferred_vehicle.current_owner == second_owner
    assert ownership_history.count() == 2
    assert ownership_history.filter(
        owner=first_owner,
        ended_at__isnull=False,
    ).exists()
    assert ownership_history.filter(
        owner=second_owner,
        ended_at__isnull=True,
    ).exists()
