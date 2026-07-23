"""Tests for product-catalogue role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_manager_receives_product_management_permissions() -> None:
    """Allow managers to maintain products and prices."""

    ensure_default_roles()

    manager = Group.objects.get(name=RoleName.MANAGER.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            manager.permissions.filter(
                content_type__app_label="product_catalogue"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "product_catalogue.view_productcategory",
        "product_catalogue.add_productcategory",
        "product_catalogue.change_productcategory",
        "product_catalogue.view_product",
        "product_catalogue.add_product",
        "product_catalogue.change_product",
        "product_catalogue.change_product_price",
        "product_catalogue.deactivate_product",
        "product_catalogue.reactivate_product",
    }


@pytest.mark.django_db
def test_technician_has_read_only_product_access() -> None:
    """Give technicians read-only product-catalogue access."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            technician.permissions.filter(
                content_type__app_label="product_catalogue"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "product_catalogue.view_productcategory",
        "product_catalogue.view_product",
    }
