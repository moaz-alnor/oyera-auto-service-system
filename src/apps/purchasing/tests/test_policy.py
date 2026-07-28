"""Tests for purchasing role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import (
    ensure_default_roles,
)
from apps.purchasing.constants import (
    PurchasingPermissionName,
)

_SUPPLIER_PERMISSIONS = {
    PurchasingPermissionName.VIEW_SUPPLIER.value,
    PurchasingPermissionName.ADD_SUPPLIER.value,
    PurchasingPermissionName.CHANGE_SUPPLIER.value,
    PurchasingPermissionName.DEACTIVATE_SUPPLIER.value,
    PurchasingPermissionName.REACTIVATE_SUPPLIER.value,
}

_PURCHASE_ORDER_PERMISSIONS = {
    PurchasingPermissionName.VIEW_PURCHASE_ORDER.value,
    PurchasingPermissionName.ADD_PURCHASE_ORDER.value,
    PurchasingPermissionName.CHANGE_PURCHASE_ORDER.value,
    PurchasingPermissionName.SUBMIT_PURCHASE_ORDER.value,
    PurchasingPermissionName.APPROVE_PURCHASE_ORDER.value,
    PurchasingPermissionName.CANCEL_PURCHASE_ORDER.value,
}


def _purchase_order_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return purchase-order permissions for one role."""

    group = Group.objects.get(name=role.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="purchasing").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    return permissions & _PURCHASE_ORDER_PERMISSIONS


def _supplier_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return supplier permissions assigned to a role."""

    group = Group.objects.get(name=role.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="purchasing").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    return permissions & _SUPPLIER_PERMISSIONS


@pytest.mark.django_db
def test_management_controls_suppliers() -> None:
    """Allow administrators and managers full control."""

    ensure_default_roles()

    assert _supplier_permissions(role=RoleName.ADMINISTRATOR) == _SUPPLIER_PERMISSIONS

    assert _supplier_permissions(role=RoleName.MANAGER) == _SUPPLIER_PERMISSIONS


@pytest.mark.django_db
def test_operational_roles_view_suppliers() -> None:
    """Allow selected roles to inspect suppliers."""

    ensure_default_roles()

    view_only = {PurchasingPermissionName.VIEW_SUPPLIER.value}

    for role in (
        RoleName.RECEPTIONIST,
        RoleName.SENIOR_TECHNICIAN,
        RoleName.CASHIER,
    ):
        assert _supplier_permissions(role=role) == view_only


@pytest.mark.django_db
def test_technician_has_no_supplier_permissions() -> None:
    """Keep purchasing data outside technician duties."""

    ensure_default_roles()

    assert _supplier_permissions(role=RoleName.TECHNICIAN) == set()


@pytest.mark.django_db
def test_management_controls_purchase_orders() -> None:
    """Allow management to control purchase orders."""

    ensure_default_roles()

    assert (
        _purchase_order_permissions(role=RoleName.ADMINISTRATOR)
        == _PURCHASE_ORDER_PERMISSIONS
    )

    assert (
        _purchase_order_permissions(role=RoleName.MANAGER)
        == _PURCHASE_ORDER_PERMISSIONS
    )


@pytest.mark.django_db
def test_operational_roles_view_purchase_orders() -> None:
    """Allow selected roles to inspect orders."""

    ensure_default_roles()

    view_only = {PurchasingPermissionName.VIEW_PURCHASE_ORDER.value}

    for role in (
        RoleName.RECEPTIONIST,
        RoleName.SENIOR_TECHNICIAN,
        RoleName.CASHIER,
    ):
        assert _purchase_order_permissions(role=role) == view_only


@pytest.mark.django_db
def test_technician_has_no_purchase_order_permissions() -> None:
    """Keep purchase ordering outside technician duties."""

    ensure_default_roles()

    assert _purchase_order_permissions(role=RoleName.TECHNICIAN) == set()
