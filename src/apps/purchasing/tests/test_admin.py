"""Tests for supplier Django Admin protection."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.purchasing.models import Supplier
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def test_supplier_is_registered() -> None:
    """Register suppliers in Django Admin."""

    assert admin.site.is_registered(Supplier)


@pytest.mark.django_db
def test_supplier_admin_is_read_only(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent direct supplier writes through Admin."""

    request = RequestFactory().get("/admin/")
    request.user = purchasing_context.manager

    model_admin = admin.site._registry[Supplier]

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
