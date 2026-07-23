"""Tests for employee-account administration rules."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.admin import UserAdmin
from apps.accounts.models import User


@pytest.mark.django_db
def test_user_admin_prevents_permanent_deletion() -> None:
    """Preserve employee accounts referenced by historical records."""

    administrator = User.objects.create_superuser(
        username="admin.lifecycle",
        password="Strong-Test-Password-2026",
        email="admin@example.com",
    )
    employee = User.objects.create_user(
        username="historical.employee",
        password="Strong-Test-Password-2026",
    )

    request = RequestFactory().get("/admin/accounts/user/")
    request.user = administrator

    user_admin = UserAdmin(User, admin.site)

    assert not user_admin.has_delete_permission(
        request,
        employee,
    )
    assert "delete_selected" not in user_admin.get_actions(request)
