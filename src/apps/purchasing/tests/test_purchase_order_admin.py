"""Tests for purchase-order Django Admin protection."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderLine,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def test_purchase_order_models_are_registered() -> None:
    """Register orders and lines in Django Admin."""

    assert admin.site.is_registered(PurchaseOrder)
    assert admin.site.is_registered(PurchaseOrderLine)


@pytest.mark.django_db
def test_purchase_order_admins_are_read_only(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent direct purchasing mutations in Admin."""

    request = RequestFactory().get("/admin/")
    request.user = purchasing_context.manager

    for model in (
        PurchaseOrder,
        PurchaseOrderLine,
    ):
        model_admin = admin.site._registry[model]

        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
