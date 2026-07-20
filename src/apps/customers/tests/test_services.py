"""Tests for customer application services."""

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.customers.services.customers import (
    RegisterCustomerCommand,
    UpdateCustomerCommand,
    deactivate_customer,
    reactivate_customer,
    register_customer,
    update_customer,
)


@pytest.mark.django_db
def test_receptionist_can_register_customer() -> None:
    """Register a customer and generate a stable customer number."""

    ensure_default_roles()

    receptionist = User.objects.create_user(
        username="receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    customer = register_customer(
        actor=receptionist,
        command=RegisterCustomerCommand(
            customer_type=CustomerType.INDIVIDUAL,
            name="Daniel Kato",
            phone_number="0700 123 456",
            email="Daniel@Example.com",
        ),
    )

    assert customer.customer_number == "CUS-000001"
    assert customer.normalized_phone_number == "0700123456"
    assert customer.email == "daniel@example.com"
    assert customer.created_by == receptionist
    assert Customer.objects.filter(pk=customer.pk).exists()


@pytest.mark.django_db
def test_technician_cannot_register_customer() -> None:
    """Reject customer registration by an unauthorized technician."""

    ensure_default_roles()

    technician = User.objects.create_user(
        username="technician",
        password="Strong-Test-Password-2026",
    )
    technician.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    with pytest.raises(PermissionDenied):
        register_customer(
            actor=technician,
            command=RegisterCustomerCommand(
                customer_type=CustomerType.INDIVIDUAL,
                name="Daniel Kato",
                phone_number="0700123456",
            ),
        )


@pytest.mark.django_db
def test_administrator_can_deactivate_and_reactivate_customer() -> None:
    """Change customer activity without deleting the record."""

    ensure_default_roles()

    administrator = User.objects.create_user(
        username="administrator",
        password="Strong-Test-Password-2026",
    )
    administrator.groups.add(Group.objects.get(name=RoleName.ADMINISTRATOR.value))

    customer = register_customer(
        actor=administrator,
        command=RegisterCustomerCommand(
            customer_type=CustomerType.COMPANY,
            name="Oyera Transport Ltd",
            phone_number="0700123456",
        ),
    )

    deactivated_customer = deactivate_customer(
        actor=administrator,
        customer_id=customer.pk,
    )

    assert not deactivated_customer.is_active
    assert Customer.objects.filter(pk=customer.pk).exists()

    reactivated_customer = reactivate_customer(
        actor=administrator,
        customer_id=customer.pk,
    )

    assert reactivated_customer.is_active


@pytest.mark.django_db
def test_receptionist_can_update_customer() -> None:
    """Update customer information through the application service."""

    ensure_default_roles()

    receptionist = User.objects.create_user(
        username="update.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    customer = register_customer(
        actor=receptionist,
        command=RegisterCustomerCommand(
            customer_type=CustomerType.INDIVIDUAL,
            name="Daniel Kato",
            phone_number="0700123456",
        ),
    )

    updated_customer = update_customer(
        actor=receptionist,
        customer_id=customer.pk,
        command=UpdateCustomerCommand(
            customer_type=CustomerType.INDIVIDUAL,
            name="Daniel Kato Junior",
            phone_number="+256 700 999 888",
            email="DANIEL.JR@EXAMPLE.COM",
        ),
    )

    assert updated_customer.name == "Daniel Kato Junior"
    assert updated_customer.normalized_phone_number == "256700999888"
    assert updated_customer.email == "daniel.jr@example.com"
    assert updated_customer.updated_by == receptionist


@pytest.mark.django_db
def test_technician_cannot_update_customer() -> None:
    """Reject customer updates by unauthorized technicians."""

    ensure_default_roles()

    administrator = User.objects.create_user(
        username="customer.owner",
        password="Strong-Test-Password-2026",
    )
    administrator.groups.add(Group.objects.get(name=RoleName.ADMINISTRATOR.value))

    technician = User.objects.create_user(
        username="update.technician",
        password="Strong-Test-Password-2026",
    )
    technician.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    customer = register_customer(
        actor=administrator,
        command=RegisterCustomerCommand(
            customer_type=CustomerType.COMPANY,
            name="Oyera Transport Ltd",
            phone_number="0700123456",
        ),
    )

    with pytest.raises(PermissionDenied):
        update_customer(
            actor=technician,
            customer_id=customer.pk,
            command=UpdateCustomerCommand(
                customer_type=CustomerType.COMPANY,
                name="Unauthorized Change",
                phone_number="0700999999",
            ),
        )
