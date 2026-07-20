"""Tests for employee authentication workflows."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_login_page_is_available(client) -> None:
    """Allow an unauthenticated employee to open the login page."""

    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert "Employee Login" in response.content.decode()


@pytest.mark.django_db
def test_valid_employee_can_log_in(client) -> None:
    """Authenticate an active employee with valid credentials."""

    user_model = get_user_model()
    user_model.objects.create_user(
        username="employee",
        password="Strong-Test-Password-2026",
    )

    response = client.post(
        reverse("accounts:login"),
        {
            "username": "employee",
            "password": "Strong-Test-Password-2026",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("core:dashboard")


@pytest.mark.django_db
def test_invalid_credentials_are_rejected(client) -> None:
    """Reject an authentication attempt with an invalid password."""

    user_model = get_user_model()
    user_model.objects.create_user(
        username="employee",
        password="Strong-Test-Password-2026",
    )

    response = client.post(
        reverse("accounts:login"),
        {
            "username": "employee",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_inactive_employee_cannot_log_in(client) -> None:
    """Prevent an inactive employee account from authenticating."""

    user_model = get_user_model()
    user_model.objects.create_user(
        username="inactive.employee",
        password="Strong-Test-Password-2026",
        is_active=False,
    )

    response = client.post(
        reverse("accounts:login"),
        {
            "username": "inactive.employee",
            "password": "Strong-Test-Password-2026",
        },
    )

    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_authenticated_employee_can_log_out(client) -> None:
    """End an authenticated employee session."""

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="employee",
        password="Strong-Test-Password-2026",
    )
    client.force_login(employee)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
