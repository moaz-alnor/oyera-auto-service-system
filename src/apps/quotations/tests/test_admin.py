"""Tests for read-only quotation administration."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.models import User
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)


@pytest.mark.django_db
def test_quotation_models_are_registered_in_admin() -> None:
    """Register all quotation records for inspection."""

    assert Quotation in admin.site._registry
    assert QuotationServiceLine in admin.site._registry
    assert QuotationProductLine in admin.site._registry


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    (
        Quotation,
        QuotationServiceLine,
        QuotationProductLine,
    ),
)
def test_quotation_admin_disables_write_actions(
    model,
) -> None:
    """Prevent quotation changes through Django admin."""

    administrator = User.objects.create_superuser(
        username="quotation.admin",
        email="quotation.admin@example.com",
        password="Strong-Test-Password-2026",
    )

    request = RequestFactory().get("/admin/")
    request.user = administrator

    model_admin = admin.site._registry[model]

    assert model_admin.has_view_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
