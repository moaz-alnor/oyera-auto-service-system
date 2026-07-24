"""Tests for workshop role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles
from apps.workshop.constants import WorkshopPermissionName


def _workshop_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return workshop permissions assigned to one role."""

    group = Group.objects.get(name=role.value)

    return {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="workshop").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }


@pytest.mark.django_db
def test_manager_can_manage_workshop_execution() -> None:
    """Give managers commercial and operational control."""

    ensure_default_roles()

    permissions = _workshop_permissions(role=RoleName.MANAGER)

    assert {
        WorkshopPermissionName.VIEW_WORK_ORDER.value,
        WorkshopPermissionName.ADD_WORK_ORDER.value,
        WorkshopPermissionName.ASSIGN_TECHNICIAN.value,
        WorkshopPermissionName.START_WORK_ORDER.value,
        WorkshopPermissionName.COMPLETE_WORK_ORDER.value,
        WorkshopPermissionName.COMPLETE_WORK_TASK.value,
    } <= permissions


@pytest.mark.django_db
def test_senior_technician_can_coordinate_work() -> None:
    """Allow senior technicians to manage execution only."""

    ensure_default_roles()

    permissions = _workshop_permissions(role=RoleName.SENIOR_TECHNICIAN)

    assert {
        WorkshopPermissionName.VIEW_WORK_ORDER.value,
        WorkshopPermissionName.ASSIGN_TECHNICIAN.value,
        WorkshopPermissionName.START_WORK_ORDER.value,
        WorkshopPermissionName.START_WORK_TASK.value,
        WorkshopPermissionName.BLOCK_WORK_TASK.value,
        WorkshopPermissionName.COMPLETE_WORK_TASK.value,
    } <= permissions

    assert WorkshopPermissionName.ADD_WORK_ORDER.value not in permissions
    assert WorkshopPermissionName.COMPLETE_WORK_ORDER.value not in permissions


@pytest.mark.django_db
def test_technician_has_task_execution_permissions() -> None:
    """Allow technicians to operate assigned tasks only."""

    ensure_default_roles()

    permissions = _workshop_permissions(role=RoleName.TECHNICIAN)

    assert {
        WorkshopPermissionName.VIEW_WORK_ORDER.value,
        WorkshopPermissionName.VIEW_WORK_TASK.value,
        WorkshopPermissionName.ADD_TASK_NOTE.value,
        WorkshopPermissionName.START_WORK_TASK.value,
        WorkshopPermissionName.BLOCK_WORK_TASK.value,
        WorkshopPermissionName.COMPLETE_WORK_TASK.value,
    } <= permissions

    assert WorkshopPermissionName.ADD_WORK_ORDER.value not in permissions
    assert WorkshopPermissionName.ASSIGN_TECHNICIAN.value not in permissions
