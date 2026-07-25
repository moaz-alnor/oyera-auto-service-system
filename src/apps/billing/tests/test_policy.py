"""Tests for billing role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles
from apps.billing.constants import BillingPermissionName


def _billing_permissions(
    *,
    role: RoleName,
) -> set[str]:
    """Return billing permissions assigned to one role."""

    group = Group.objects.get(name=role.value)

    return {
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="billing").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }


@pytest.mark.django_db
def test_manager_controls_billing_lifecycle() -> None:
    """Allow managers to control invoices and payments."""

    ensure_default_roles()

    permissions = _billing_permissions(role=RoleName.MANAGER)

    assert {
        BillingPermissionName.VIEW_INVOICE.value,
        BillingPermissionName.ADD_INVOICE.value,
        BillingPermissionName.ISSUE_INVOICE.value,
        BillingPermissionName.VOID_INVOICE.value,
        BillingPermissionName.VIEW_PAYMENT.value,
        BillingPermissionName.RECORD_PAYMENT.value,
        BillingPermissionName.VOID_PAYMENT.value,
    } <= permissions


@pytest.mark.django_db
def test_cashier_can_invoice_and_receive_payment() -> None:
    """Allow cashiers to bill without void authority."""

    ensure_default_roles()

    permissions = _billing_permissions(role=RoleName.CASHIER)

    assert {
        BillingPermissionName.VIEW_INVOICE.value,
        BillingPermissionName.ADD_INVOICE.value,
        BillingPermissionName.ISSUE_INVOICE.value,
        BillingPermissionName.VIEW_PAYMENT.value,
        BillingPermissionName.RECORD_PAYMENT.value,
    } <= permissions

    assert BillingPermissionName.VOID_INVOICE.value not in permissions
    assert BillingPermissionName.VOID_PAYMENT.value not in permissions


@pytest.mark.django_db
def test_technician_has_no_billing_permissions() -> None:
    """Keep customer billing outside technician duties."""

    ensure_default_roles()

    permissions = _billing_permissions(role=RoleName.TECHNICIAN)

    assert permissions == set()
