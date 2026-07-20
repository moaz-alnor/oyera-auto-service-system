"""Tests for customer role-permission assignments."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_receptionist_receives_customer_permissions() -> None:
    """Allow receptionists to register and maintain customers."""

    ensure_default_roles()

    receptionist = Group.objects.get(name=RoleName.RECEPTIONIST.value)

    permission_codes = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            receptionist.permissions.filter(
                content_type__app_label="customers"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permission_codes == {
        "customers.view_customer",
        "customers.add_customer",
        "customers.change_customer",
    }


@pytest.mark.django_db
def test_technician_receives_no_customer_permissions() -> None:
    """Prevent technicians from managing customer records."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    assert not technician.permissions.filter(
        content_type__app_label="customers"
    ).exists()
