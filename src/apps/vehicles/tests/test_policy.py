"""Tests for vehicle role-permission assignments."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_receptionist_receives_vehicle_permissions() -> None:
    """Allow receptionists to register and maintain vehicles."""

    ensure_default_roles()

    receptionist = Group.objects.get(name=RoleName.RECEPTIONIST.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            receptionist.permissions.filter(
                content_type__app_label="vehicles"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "vehicles.view_vehicle",
        "vehicles.add_vehicle",
        "vehicles.change_vehicle",
        "vehicles.transfer_vehicle_owner",
    }


@pytest.mark.django_db
def test_technician_can_only_view_vehicle_records() -> None:
    """Prevent technicians from changing vehicle records."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            technician.permissions.filter(
                content_type__app_label="vehicles"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "vehicles.view_vehicle",
    }
