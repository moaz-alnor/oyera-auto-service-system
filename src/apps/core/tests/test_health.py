"""Tests for operational health-check endpoints."""

import pytest
from django.db import OperationalError
from django.urls import reverse

from apps.core import health


def test_liveness_returns_ok_without_authentication(client) -> None:
    """Report that the web process is alive without touching business data."""
    response = client.get(reverse("core:health_live"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "oyera",
        "check": "liveness",
    }
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.django_db
def test_readiness_returns_ok_when_database_is_available(
    client,
) -> None:
    """Report ready when the primary database accepts a query."""
    response = client.get(reverse("core:health_ready"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "oyera",
        "checks": {
            "database": "ok",
        },
    }
    assert "no-store" in response.headers["Cache-Control"]


def test_readiness_returns_503_when_database_is_unavailable(
    client,
    monkeypatch,
) -> None:
    """Report unavailable without exposing database error details."""

    class UnavailableConnection:
        """Database connection that always fails."""

        def cursor(self):
            """Raise the database availability error."""
            raise OperationalError("Private database connection details.")

    monkeypatch.setattr(
        health,
        "connection",
        UnavailableConnection(),
    )

    response = client.get(reverse("core:health_ready"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "service": "oyera",
        "checks": {
            "database": "unavailable",
        },
    }
    assert b"Private database connection details" not in response.content
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.parametrize(
    "route_name",
    [
        "core:health_live",
        "core:health_ready",
    ],
)
def test_health_endpoints_reject_non_get_methods(
    client,
    route_name: str,
) -> None:
    """Health endpoints should remain read-only."""
    response = client.post(reverse(route_name))

    assert response.status_code == 405
