"""Tests for shared application views."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_requires_authentication(client) -> None:
    """Redirect an unauthenticated visitor to login."""

    response = client.get(reverse("core:dashboard"))

    expected_login_url = f"{reverse('accounts:login')}?next={reverse('core:dashboard')}"

    assert response.status_code == 302
    assert response.url == expected_login_url


@pytest.mark.django_db
def test_authenticated_employee_can_view_dashboard(
    client,
) -> None:
    """Allow an authenticated employee to open dashboard."""

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
    """Display values returned by dashboard selector."""

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
        vehicles_received_today=1,
        open_job_cards=2,
        active_work_orders=3,
        vehicles_ready_for_release=4,
        invoices_awaiting_payment=5,
        low_stock_items=6,
        purchase_orders_awaiting_approval=7,
        supplier_invoices_awaiting_payment=8,
    )

    monkeypatch.setattr(
        ("apps.core.views.get_operational_dashboard_metrics"),
        lambda: metrics,
    )

    response = client.get(reverse("core:dashboard"))

    content = response.content.decode()
    normalised_content = "".join(content.split())

    assert response.status_code == 200
    assert response.context["metrics"] == metrics

    expected_labels = (
        "Vehicles received today",
        "Open job cards",
        "Active workshop orders",
        "Vehicles ready for release",
        "Customer invoices awaiting payment",
        "Low-stock items",
        "Purchase orders awaiting approval",
        "Supplier invoices awaiting payment",
    )

    for label in expected_labels:
        assert label in content

    for value in range(1, 9):
        assert f">{value}<" in normalised_content
