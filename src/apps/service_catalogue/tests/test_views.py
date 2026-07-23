"""Tests for service-catalogue HTTP workflows."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.service_catalogue.models import (
    Service,
    ServicePrice,
)
from apps.service_catalogue.services.catalogue import (
    CreateServiceCommand,
    create_service,
)
from apps.vehicles.constants import VehicleCategory


@pytest.fixture
def manager() -> User:
    """Create an employee with catalogue-management permission."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="catalogue.view.manager",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create an employee with read-only catalogue permission."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="catalogue.view.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def catalogue_service(
    manager: User,
) -> Service:
    """Create a service through the application service."""

    return create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="OIL-CHANGE",
            name="Engine Oil Change",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("75000.00"),
        ),
    )


@pytest.mark.django_db
def test_service_list_requires_authentication(client) -> None:
    """Redirect anonymous visitors to employee login."""

    response = client.get(reverse("service_catalogue:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_technician_can_view_service_list(
    client,
    technician: User,
) -> None:
    """Allow technicians to inspect the service catalogue."""

    client.force_login(technician)

    response = client.get(reverse("service_catalogue:list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_technician_cannot_create_service(
    client,
    technician: User,
) -> None:
    """Return HTTP 403 for unauthorized creation attempts."""

    client.force_login(technician)

    response = client.get(reverse("service_catalogue:create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_can_create_service(
    client,
    manager: User,
) -> None:
    """Create a service through the HTTP workflow."""

    client.force_login(manager)

    response = client.post(
        reverse("service_catalogue:create"),
        {
            "code": "WHEEL-ALIGNMENT",
            "name": "Wheel Alignment",
            "description": "Align all vehicle wheels.",
            "estimated_duration_minutes": 60,
            "applicable_categories": [
                VehicleCategory.SMALL,
                VehicleCategory.COMMERCIAL,
            ],
            "initial_price": "30000.00",
            "currency": "UGX",
            "price_notes": "Opening catalogue price.",
        },
    )

    service = Service.objects.get(normalized_code="WHEELALIGNMENT")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "service_catalogue:detail",
        args=(service.pk,),
    )


@pytest.mark.django_db
def test_manager_can_change_service_price(
    client,
    manager: User,
    catalogue_service: Service,
) -> None:
    """Create a new historical price period through the interface."""

    client.force_login(manager)

    response = client.post(
        reverse(
            "service_catalogue:change_price",
            args=(catalogue_service.pk,),
        ),
        {
            "amount": "85000.00",
            "currency": "UGX",
            "notes": "Updated supplier costs.",
        },
    )

    prices = ServicePrice.objects.filter(service=catalogue_service)

    assert response.status_code == 302
    assert prices.count() == 2
    assert prices.filter(
        amount=Decimal("75000.00"),
        effective_until__isnull=False,
    ).exists()
    assert prices.filter(
        amount=Decimal("85000.00"),
        effective_until__isnull=True,
    ).exists()


@pytest.mark.django_db
def test_technician_cannot_change_service_price(
    client,
    technician: User,
    catalogue_service: Service,
) -> None:
    """Return HTTP 403 for unauthorized price changes."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "service_catalogue:change_price",
            args=(catalogue_service.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_service_detail_displays_price_history(
    client,
    technician: User,
    catalogue_service: Service,
) -> None:
    """Display current and historical price information."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "service_catalogue:detail",
            args=(catalogue_service.pk,),
        )
    )

    assert response.status_code == 200
    assert b"OIL-CHANGE" in response.content
    assert b"75000.00" in response.content


@pytest.mark.django_db
def test_technician_cannot_edit_service(
    client,
    technician: User,
    catalogue_service: Service,
) -> None:
    """Return HTTP 403 for service-edit attempts."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "service_catalogue:update",
            args=(catalogue_service.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_can_update_service(
    client,
    manager: User,
    catalogue_service: Service,
) -> None:
    """Update a service through the HTTP workflow."""

    client.force_login(manager)

    response = client.post(
        reverse(
            "service_catalogue:update",
            args=(catalogue_service.pk,),
        ),
        {
            "code": "ENGINE-OIL",
            "name": "Engine Oil and Filter Change",
            "description": "Replace oil and filter.",
            "estimated_duration_minutes": 60,
            "applicable_categories": [
                VehicleCategory.SMALL,
                VehicleCategory.COMMERCIAL,
            ],
        },
    )

    catalogue_service.refresh_from_db()

    assert response.status_code == 302
    assert catalogue_service.code == "ENGINE-OIL"
    assert catalogue_service.name == ("Engine Oil and Filter Change")
    assert ServicePrice.objects.filter(service=catalogue_service).count() == 1


@pytest.mark.django_db
def test_service_deactivation_requires_post(
    client,
    manager: User,
    catalogue_service: Service,
) -> None:
    """Reject GET requests to the status-changing endpoint."""

    client.force_login(manager)

    response = client.get(
        reverse(
            "service_catalogue:deactivate",
            args=(catalogue_service.pk,),
        )
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_manager_can_deactivate_and_reactivate_service(
    client,
    manager: User,
    catalogue_service: Service,
) -> None:
    """Change catalogue status through protected POST actions."""

    client.force_login(manager)

    deactivate_response = client.post(
        reverse(
            "service_catalogue:deactivate",
            args=(catalogue_service.pk,),
        )
    )

    catalogue_service.refresh_from_db()

    assert deactivate_response.status_code == 302
    assert not catalogue_service.is_active

    reactivate_response = client.post(
        reverse(
            "service_catalogue:reactivate",
            args=(catalogue_service.pk,),
        )
    )

    catalogue_service.refresh_from_db()

    assert reactivate_response.status_code == 302
    assert catalogue_service.is_active
