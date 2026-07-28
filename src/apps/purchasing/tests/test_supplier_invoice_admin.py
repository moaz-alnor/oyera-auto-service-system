"""Tests for supplier-finance Django Admin protection."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.purchasing.models import (
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierPayment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def test_supplier_finance_models_are_registered() -> None:
    """Register supplier financial records in Admin."""

    for model in (
        SupplierInvoice,
        SupplierInvoiceLine,
        SupplierPayment,
    ):
        assert admin.site.is_registered(model)


@pytest.mark.django_db
def test_supplier_finance_admins_are_read_only(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent direct supplier-finance mutations."""

    request = RequestFactory().get("/admin/")
    request.user = purchasing_context.manager

    for model in (
        SupplierInvoice,
        SupplierInvoiceLine,
        SupplierPayment,
    ):
        model_admin = admin.site._registry[model]

        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
