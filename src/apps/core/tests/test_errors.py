"""Tests for custom HTTP error handlers."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.urls import get_resolver

from apps.core.errors import (
    bad_request,
    page_not_found,
    permission_denied,
    server_error,
)


def test_bad_request_handler_returns_400(rf) -> None:
    """Render a safe, branded HTTP 400 response."""
    request = rf.get("/invalid-request/")

    response = bad_request(
        request,
        Exception("Unsafe details must not be displayed."),
    )

    assert response.status_code == 400
    assert b"Request could not be processed" in response.content
    assert b"Unsafe details" not in response.content


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
    assert b"Test permission denial" not in response.content


def test_page_not_found_handler_returns_404(rf) -> None:
    """Render a safe, branded HTTP 404 response."""
    request = rf.get("/missing/")

    response = page_not_found(
        request,
        Exception("Private routing details."),
    )

    assert response.status_code == 404
    assert b"Page not found" in response.content
    assert b"Private routing details" not in response.content


def test_server_error_handler_returns_500(rf) -> None:
    """Render a safe, branded HTTP 500 response."""
    request = rf.get("/broken/")

    response = server_error(request)

    assert response.status_code == 500
    assert b"Something went wrong" in response.content
    assert b"Traceback" not in response.content


def test_root_urlconf_registers_custom_error_handlers() -> None:
    """Register every production error handler in the root URLconf."""
    resolver = get_resolver()

    assert resolver.resolve_error_handler(400) is bad_request
    assert resolver.resolve_error_handler(403) is permission_denied
    assert resolver.resolve_error_handler(404) is page_not_found
    assert resolver.resolve_error_handler(500) is server_error


@override_settings(DEBUG=False)
def test_unknown_route_uses_custom_404_page(client) -> None:
    """Use the branded 404 response for an unknown application route."""
    response = client.get("/release-readiness-missing-page/")

    assert response.status_code == 404
    assert b"Page not found" in response.content
    assert b"release-readiness-missing-page" not in response.content
