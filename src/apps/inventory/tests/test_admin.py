"""Tests for read-only inventory administration."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
    StockReservation,
)

_INVENTORY_MODELS = (
    StockLocation,
    InventoryItem,
    StockReservation,
    StockMovement,
)


@pytest.mark.django_db
def test_inventory_models_are_registered_in_admin() -> None:
    """Expose inventory history for administrative inspection."""

    for model in _INVENTORY_MODELS:
        assert model in admin.site._registry


@pytest.mark.django_db
def test_inventory_admin_is_read_only() -> None:
    """Prevent admin operations that bypass inventory services."""

    request = RequestFactory().get("/admin/")

    for model in _INVENTORY_MODELS:
        model_admin = admin.site._registry[model]

        assert isinstance(
            model_admin,
            ReadOnlyAdminMixin,
        )
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
