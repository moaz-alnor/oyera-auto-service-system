"""Tests for shared application views."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_requires_authentication(client) -> None:
    """Redirect an unauthenticated visitor to the login page."""

    response = client.get(reverse("core:dashboard"))

    expected_login_url = f"{reverse('accounts:login')}?next={reverse('core:dashboard')}"

    assert response.status_code == 302
    assert response.url == expected_login_url


@pytest.mark.django_db
def test_authenticated_employee_can_view_dashboard(client) -> None:
    """Allow an authenticated employee to open the dashboard."""

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="employee",
        password="Strong-Test-Password-2026",
    )
    client.force_login(employee)

    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 200
    assert "Dashboard" in response.content.decode()
