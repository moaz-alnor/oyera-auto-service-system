"""Tests for goods-receipt Django Admin protection."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def test_goods_receipt_models_are_registered() -> None:
    """Register receipt records in Django Admin."""

    assert admin.site.is_registered(GoodsReceipt)
    assert admin.site.is_registered(GoodsReceiptLine)


@pytest.mark.django_db
def test_goods_receipt_admins_are_read_only(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent direct receipt mutations in Admin."""

    request = RequestFactory().get("/admin/")
    request.user = purchasing_context.manager

    for model in (
        GoodsReceipt,
        GoodsReceiptLine,
    ):
        model_admin = admin.site._registry[model]

        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
