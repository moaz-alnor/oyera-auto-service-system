"""Tests for read-only workshop administration."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.models import User
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
    WorkTaskNote,
)

WORKSHOP_MODELS = (
    WorkOrder,
    WorkTask,
    TechnicianAssignment,
    WorkProductRequirement,
    WorkTaskNote,
)


@pytest.mark.django_db
def test_workshop_models_are_registered_in_admin() -> None:
    """Register every workshop record for inspection."""

    for model in WORKSHOP_MODELS:
        assert model in admin.site._registry


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model",
    WORKSHOP_MODELS,
)
def test_workshop_admin_disables_write_actions(
    model,
) -> None:
    """Prevent workshop changes through Django admin."""

    administrator = User.objects.create_superuser(
        username="workshop.admin",
        email="workshop.admin@example.com",
        password="Strong-Test-Password-2026",
    )

    request = RequestFactory().get("/admin/")
    request.user = administrator

    model_admin = admin.site._registry[model]

    assert model_admin.has_view_permission(request)
    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
