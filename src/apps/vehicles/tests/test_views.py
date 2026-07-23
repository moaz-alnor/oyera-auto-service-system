"""Tests for vehicle-management HTTP workflows."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle, VehicleOwnership


@pytest.fixture
def receptionist() -> User:
    """Create an employee with vehicle-management permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="vehicle.view.receptionist",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create an employee with read-only vehicle permission."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="vehicle.view.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def owners(
    receptionist: User,
) -> tuple[Customer, Customer]:
    """Create customers for vehicle-view tests."""

    first_owner = Customer.objects.create(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        normalized_phone_number="0700123456",
        created_by=receptionist,
        updated_by=receptionist,
    )
    second_owner = Customer.objects.create(
        customer_number="CUS-000002",
        customer_type=CustomerType.INDIVIDUAL,
        name="Grace Namusoke",
        phone_number="0770123456",
        normalized_phone_number="0770123456",
        created_by=receptionist,
        updated_by=receptionist,
    )

    return first_owner, second_owner


@pytest.mark.django_db
def test_vehicle_list_requires_authentication(client) -> None:
    """Redirect anonymous visitors to employee login."""

    response = client.get(reverse("vehicles:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_technician_can_view_vehicle_list(
    client,
    technician: User,
) -> None:
    """Allow technicians to inspect vehicle records."""

    client.force_login(technician)

    response = client.get(reverse("vehicles:list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_technician_cannot_register_vehicle(
    client,
    technician: User,
) -> None:
    """Return HTTP 403 for vehicle registration attempts."""

    client.force_login(technician)

    response = client.get(reverse("vehicles:create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_receptionist_can_register_vehicle(
    client,
    receptionist: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Register a vehicle through the HTTP workflow."""

    first_owner, _ = owners
    client.force_login(receptionist)

    response = client.post(
        reverse("vehicles:create"),
        {
            "current_owner": first_owner.pk,
            "registration_number": "UBD-245X",
            "category": VehicleCategory.SMALL,
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "color": "White",
            "current_mileage": 45000,
            "fuel_type": "",
            "engine_number": "",
            "chassis_number": "",
            "vin": "",
            "notes": "",
        },
    )

    vehicle = Vehicle.objects.get(normalized_registration_number="UBD245X")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "vehicles:detail",
        args=(vehicle.pk,),
    )
    assert VehicleOwnership.objects.filter(
        vehicle=vehicle,
        owner=first_owner,
        ended_at__isnull=True,
    ).exists()


@pytest.mark.django_db
def test_duplicate_registration_is_shown_as_form_error(
    client,
    receptionist: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Reject a duplicate registration without creating another row."""

    first_owner, _ = owners

    Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=receptionist,
        updated_by=receptionist,
    )

    client.force_login(receptionist)

    response = client.post(
        reverse("vehicles:create"),
        {
            "current_owner": first_owner.pk,
            "registration_number": "ubd-245x",
            "category": VehicleCategory.SMALL,
            "make": "Toyota",
            "model": "Corolla",
            "year": "",
            "color": "",
            "current_mileage": "",
            "fuel_type": "",
            "engine_number": "",
            "chassis_number": "",
            "vin": "",
            "notes": "",
        },
    )

    assert response.status_code == 200
    assert b"already exists" in response.content
    assert Vehicle.objects.count() == 1


@pytest.mark.django_db
def test_receptionist_can_transfer_ownership(
    client,
    receptionist: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Transfer ownership through the protected interface."""

    first_owner, second_owner = owners

    vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=receptionist,
        updated_by=receptionist,
    )
    VehicleOwnership.objects.create(
        vehicle=vehicle,
        owner=first_owner,
        changed_by=receptionist,
    )

    client.force_login(receptionist)

    response = client.post(
        reverse(
            "vehicles:transfer_owner",
            args=(vehicle.pk,),
        ),
        {
            "new_owner": second_owner.pk,
            "notes": "Vehicle sold.",
        },
    )

    vehicle.refresh_from_db()

    assert response.status_code == 302
    assert vehicle.current_owner == second_owner
    assert VehicleOwnership.objects.filter(
        vehicle=vehicle,
        owner=first_owner,
        ended_at__isnull=False,
    ).exists()
    assert VehicleOwnership.objects.filter(
        vehicle=vehicle,
        owner=second_owner,
        ended_at__isnull=True,
    ).exists()


@pytest.fixture
def administrator() -> User:
    """Create an employee with full vehicle permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="vehicle.view.administrator",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.ADMINISTRATOR.value))

    return employee


@pytest.mark.django_db
def test_technician_cannot_edit_vehicle(
    client,
    technician: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Return HTTP 403 for vehicle-edit attempts."""

    first_owner, _ = owners

    vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=technician,
        updated_by=technician,
    )

    client.force_login(technician)

    response = client.get(
        reverse(
            "vehicles:update",
            args=(vehicle.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_vehicle_deactivation_requires_post(
    client,
    administrator: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Reject GET requests to vehicle deactivation."""

    first_owner, _ = owners

    vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=administrator,
        updated_by=administrator,
    )

    client.force_login(administrator)

    response = client.get(
        reverse(
            "vehicles:deactivate",
            args=(vehicle.pk,),
        )
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_administrator_can_deactivate_and_reactivate_vehicle(
    client,
    administrator: User,
    owners: tuple[Customer, Customer],
) -> None:
    """Change vehicle status through protected POST actions."""

    first_owner, _ = owners

    vehicle = Vehicle.objects.create(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        normalized_registration_number="UBD245X",
        current_owner=first_owner,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=administrator,
        updated_by=administrator,
    )

    client.force_login(administrator)

    deactivate_response = client.post(
        reverse(
            "vehicles:deactivate",
            args=(vehicle.pk,),
        )
    )

    vehicle.refresh_from_db()

    assert deactivate_response.status_code == 302
    assert not vehicle.is_active

    reactivate_response = client.post(
        reverse(
            "vehicles:reactivate",
            args=(vehicle.pk,),
        )
    )

    vehicle.refresh_from_db()

    assert reactivate_response.status_code == 302
    assert vehicle.is_active
