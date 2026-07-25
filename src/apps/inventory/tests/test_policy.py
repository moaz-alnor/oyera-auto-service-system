"""Tests for inventory role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles
from apps.inventory.constants import (
    InventoryPermissionName,
)


def _inventory_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return inventory permissions assigned to one role."""

    group = Group.objects.get(name=role.value)

    return {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="inventory").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }


@pytest.mark.django_db
def test_manager_can_control_inventory() -> None:
    """Allow managers to manage and transact stock."""

    ensure_default_roles()

    permissions = _inventory_permissions(role=RoleName.MANAGER)

    assert {
        InventoryPermissionName.VIEW_INVENTORY_ITEM.value,
        InventoryPermissionName.RECEIVE_STOCK.value,
        InventoryPermissionName.RESERVE_STOCK.value,
        InventoryPermissionName.ISSUE_STOCK.value,
        InventoryPermissionName.RETURN_STOCK.value,
        InventoryPermissionName.ADJUST_STOCK.value,
    } <= permissions


@pytest.mark.django_db
def test_senior_technician_can_issue_workshop_stock() -> None:
    """Allow senior technicians to coordinate workshop parts."""

    ensure_default_roles()

    permissions = _inventory_permissions(role=RoleName.SENIOR_TECHNICIAN)

    assert {
        InventoryPermissionName.VIEW_INVENTORY_ITEM.value,
        InventoryPermissionName.RESERVE_STOCK.value,
        InventoryPermissionName.ISSUE_STOCK.value,
        InventoryPermissionName.RETURN_STOCK.value,
    } <= permissions

    assert InventoryPermissionName.RECEIVE_STOCK.value not in permissions
    assert InventoryPermissionName.ADJUST_STOCK.value not in permissions


@pytest.mark.django_db
def test_technician_has_read_only_inventory_access() -> None:
    """Prevent ordinary technicians from changing stock."""

    ensure_default_roles()

    permissions = _inventory_permissions(role=RoleName.TECHNICIAN)

    assert {
        InventoryPermissionName.VIEW_STOCK_LOCATION.value,
        InventoryPermissionName.VIEW_INVENTORY_ITEM.value,
        InventoryPermissionName.VIEW_RESERVATION.value,
    } <= permissions

    assert InventoryPermissionName.RECEIVE_STOCK.value not in permissions
    assert InventoryPermissionName.ISSUE_STOCK.value not in permissions
