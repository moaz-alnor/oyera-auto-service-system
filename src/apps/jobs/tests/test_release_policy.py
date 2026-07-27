"""Tests for vehicle-release role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles
from apps.jobs.constants import JobPermissionName

_RELEASE_PERMISSIONS = {
    JobPermissionName.VIEW_VEHICLE_RELEASE.value,
    JobPermissionName.RELEASE_VEHICLE.value,
    JobPermissionName.OVERRIDE_VEHICLE_RELEASE_PAYMENT.value,
}


def _release_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return release permissions assigned to one role."""

    group = Group.objects.get(name=role.value)

    all_permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="jobs").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    return all_permissions & _RELEASE_PERMISSIONS


@pytest.mark.django_db
def test_manager_and_administrator_control_release() -> None:
    """Allow management to release and override payment."""

    ensure_default_roles()

    assert _release_permissions(role=RoleName.MANAGER) == _RELEASE_PERMISSIONS

    assert _release_permissions(role=RoleName.ADMINISTRATOR) == _RELEASE_PERMISSIONS


@pytest.mark.django_db
def test_receptionist_releases_without_override() -> None:
    """Allow normal paid handover by reception staff."""

    ensure_default_roles()

    assert _release_permissions(role=RoleName.RECEPTIONIST) == {
        JobPermissionName.VIEW_VEHICLE_RELEASE.value,
        JobPermissionName.RELEASE_VEHICLE.value,
    }


@pytest.mark.django_db
def test_release_visibility_is_role_restricted() -> None:
    """Separate viewing from operational release rights."""

    ensure_default_roles()

    view_permission = {JobPermissionName.VIEW_VEHICLE_RELEASE.value}

    assert _release_permissions(role=RoleName.CASHIER) == view_permission

    assert _release_permissions(role=RoleName.SENIOR_TECHNICIAN) == view_permission

    assert _release_permissions(role=RoleName.TECHNICIAN) == set()
