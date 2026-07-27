"""Tests for read-only vehicle-release administration."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.jobs.models import VehicleRelease
from apps.jobs.tests.conftest import ReleaseTestContext


def test_vehicle_release_is_registered() -> None:
    """Register vehicle handovers in Django Admin."""

    assert admin.site.is_registered(VehicleRelease)


@pytest.mark.django_db
def test_vehicle_release_admin_is_read_only(
    release_context: ReleaseTestContext,
) -> None:
    """Prevent direct release writes through Admin."""

    request = RequestFactory().get("/admin/")
    request.user = release_context.manager

    model_admin = admin.site._registry[VehicleRelease]

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
