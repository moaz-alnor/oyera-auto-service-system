"""Tests for service-catalogue application services."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.service_catalogue.models import (
    ServiceApplicability,
    ServicePrice,
)
from apps.service_catalogue.services.catalogue import (
    ChangeServicePriceCommand,
    CreateServiceCommand,
    change_service_price,
    create_service,
)
from apps.vehicles.constants import VehicleCategory


@pytest.mark.django_db
def test_manager_can_create_service_with_initial_price() -> None:
    """Create a service, applicability, and current price."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="catalogue.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="OIL-CHANGE",
            name="Engine Oil Change",
            applicable_categories=(
                VehicleCategory.SMALL,
                VehicleCategory.COMMERCIAL,
            ),
            initial_price=Decimal("75000.00"),
            estimated_duration_minutes=45,
        ),
    )

    current_price = ServicePrice.objects.get(
        service=service,
        effective_until__isnull=True,
    )

    assert service.code == "OIL-CHANGE"
    assert current_price.amount == Decimal("75000.00")
    assert ServiceApplicability.objects.filter(service=service).count() == 2


@pytest.mark.django_db
def test_manager_can_change_service_price() -> None:
    """Close the old price and create a new current price."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="price.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="WHEEL-ALIGNMENT",
            name="Wheel Alignment",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("30000.00"),
        ),
    )

    previous_price = ServicePrice.objects.get(
        service=service,
        effective_until__isnull=True,
    )

    new_price = change_service_price(
        actor=manager,
        service_id=service.pk,
        command=ChangeServicePriceCommand(
            amount=Decimal("35000.00"),
            notes="Updated catalogue price.",
        ),
    )

    previous_price.refresh_from_db()

    assert previous_price.effective_until is not None
    assert new_price.amount == Decimal("35000.00")
    assert new_price.effective_until is None
    assert previous_price.effective_until == new_price.effective_from


@pytest.mark.django_db
def test_receptionist_cannot_change_service_price() -> None:
    """Prevent receptionists from modifying catalogue prices."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="catalogue.owner",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    receptionist = User.objects.create_user(
        username="catalogue.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="GENERAL-SERVICE",
            name="General Service",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("120000.00"),
        ),
    )

    with pytest.raises(PermissionDenied):
        change_service_price(
            actor=receptionist,
            service_id=service.pk,
            command=ChangeServicePriceCommand(
                amount=Decimal("130000.00"),
            ),
        )
