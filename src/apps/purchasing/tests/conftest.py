"""Shared fixtures for purchasing tests."""

from dataclasses import dataclass

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import (
    ensure_default_roles,
)


@dataclass(frozen=True, slots=True)
class PurchasingTestContext:
    """Contain employees used by purchasing tests."""

    manager: User
    cashier: User
    receptionist: User
    technician: User


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create one employee with a default role."""

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def purchasing_context() -> PurchasingTestContext:
    """Create employees for supplier tests."""

    ensure_default_roles()

    return PurchasingTestContext(
        manager=_create_employee(
            username="purchasing.manager",
            role=RoleName.MANAGER,
        ),
        cashier=_create_employee(
            username="purchasing.cashier",
            role=RoleName.CASHIER,
        ),
        receptionist=_create_employee(
            username="purchasing.receptionist",
            role=RoleName.RECEPTIONIST,
        ),
        technician=_create_employee(
            username="purchasing.technician",
            role=RoleName.TECHNICIAN,
        ),
    )
