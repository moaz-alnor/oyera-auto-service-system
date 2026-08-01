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


@pytest.mark.django_db
def test_dashboard_displays_operational_metrics(
    client,
    monkeypatch,
) -> None:
    """Display values returned by the dashboard selector."""

    from apps.core.selectors import (
        OperationalDashboardMetrics,
    )

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="dashboard.employee",
        password="Strong-Test-Password-2026",
    )
    client.force_login(employee)

    metrics = OperationalDashboardMetrics(
        vehicles_received_today=4,
        open_job_cards=7,
        invoices_awaiting_payment=3,
    )

    monkeypatch.setattr(
        "apps.core.views.get_operational_dashboard_metrics",
        lambda: metrics,
    )

    response = client.get(reverse("core:dashboard"))

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["metrics"] == metrics

    assert "Vehicles received today" in content
    assert "Open job cards" in content
    assert "Awaiting payment" in content

    assert ">4<" in "".join(content.split())
    assert ">7<" in "".join(content.split())
    assert ">3<" in "".join(content.split())
