"""Tests for quotation role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_manager_receives_complete_quotation_permissions() -> None:
    """Allow managers to supervise quotation workflows."""

    ensure_default_roles()

    manager = Group.objects.get(name=RoleName.MANAGER.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            manager.permissions.filter(
                content_type__app_label="quotations"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "quotations.view_quotation",
        "quotations.add_quotation",
        "quotations.change_quotation",
        "quotations.submit_quotation",
        "quotations.approve_quotation",
        "quotations.reject_quotation",
        "quotations.revise_quotation",
    }


@pytest.mark.django_db
def test_technician_has_read_only_quotation_access() -> None:
    """Allow technicians to view but not modify quotations."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            technician.permissions.filter(
                content_type__app_label="quotations"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "quotations.view_quotation",
    }
