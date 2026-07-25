"""Tests for read-only billing administration."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.billing.models import (
    Invoice,
    InvoiceProductLine,
    InvoiceServiceLine,
    Payment,
)
from apps.billing.tests.conftest import BillingTestContext

BILLING_MODELS = (
    Invoice,
    InvoiceServiceLine,
    InvoiceProductLine,
    Payment,
)


def test_billing_models_are_registered() -> None:
    """Register all billing records in Django Admin."""

    for model in BILLING_MODELS:
        assert admin.site.is_registered(model)


@pytest.mark.django_db
def test_billing_admin_is_read_only(
    billing_context: BillingTestContext,
) -> None:
    """Prevent direct billing writes through Django Admin."""

    request = RequestFactory().get("/admin/")
    request.user = billing_context.manager

    for model in BILLING_MODELS:
        model_admin = admin.site._registry[model]

        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
