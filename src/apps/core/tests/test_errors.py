"""Tests for custom HTTP error handlers."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.core.errors import permission_denied


@pytest.mark.django_db
def test_permission_denied_handler_returns_403(rf) -> None:
    """Render the branded access-denied page with HTTP status 403."""

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="denied.employee",
        password="Strong-Test-Password-2026",
    )

    request = rf.get("/forbidden/")
    request.user = employee

    response = permission_denied(
        request,
        PermissionDenied("Test permission denial."),
    )

    assert response.status_code == 403
    assert b"Access denied" in response.content
