"""Tests for service-catalogue role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_manager_receives_catalogue_management_permissions() -> None:
    """Allow managers to maintain services and prices."""

    ensure_default_roles()

    manager = Group.objects.get(name=RoleName.MANAGER.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            manager.permissions.filter(
                content_type__app_label="service_catalogue"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "service_catalogue.view_service",
        "service_catalogue.add_service",
        "service_catalogue.change_service",
        "service_catalogue.change_service_price",
        "service_catalogue.deactivate_service",
        "service_catalogue.reactivate_service",
    }


@pytest.mark.django_db
def test_technician_can_only_view_catalogue_services() -> None:
    """Give technicians read-only catalogue access."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            technician.permissions.filter(
                content_type__app_label="service_catalogue"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "service_catalogue.view_service",
    }
