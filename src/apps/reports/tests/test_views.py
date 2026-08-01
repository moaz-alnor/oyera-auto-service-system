"""Tests for operational-report views."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import (
    ensure_default_roles,
)
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange


def _create_role_user(
    *,
    role: RoleName,
):
    """Create one employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"reports.{role.value.casefold()}".replace(" ", ".")),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


@pytest.mark.django_db
def test_reports_require_authentication(client) -> None:
    """Redirect anonymous users to login."""

    response = client.get(reverse("reports:index"))

    expected_location = f"{reverse('accounts:login')}?next={reverse('reports:index')}"

    assert response.status_code == 302
    assert response.headers["Location"] == expected_location


@pytest.mark.django_db
def test_technician_cannot_access_reports(
    client,
) -> None:
    """Deny reporting access to technicians."""

    technician = _create_role_user(role=RoleName.TECHNICIAN)
    client.force_login(technician)

    response = client.get(reverse("reports:index"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_sees_all_report_categories(
    client,
) -> None:
    """Display every report category to managers."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    response = client.get(reverse("reports:index"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Customer finance report" in content
    assert reverse("reports:customer_finance") in content
    assert "Workshop operations report" in content
    assert "Inventory report" in content
    assert "Purchasing report" in content


@pytest.mark.django_db
def test_cashier_sees_financial_reports(
    client,
) -> None:
    """Show finance and purchasing reports to cashiers."""

    cashier = _create_role_user(role=RoleName.CASHIER)
    client.force_login(cashier)

    response = client.get(reverse("reports:index"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Customer finance report" in content
    assert "Purchasing report" in content
    assert "Workshop operations report" not in content
    assert "Inventory report" not in content


@pytest.mark.django_db
def test_receptionist_sees_workshop_report(
    client,
) -> None:
    """Show only the operations report to receptionists."""

    receptionist = _create_role_user(role=RoleName.RECEPTIONIST)
    client.force_login(receptionist)

    response = client.get(reverse("reports:index"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Workshop operations report" in content
    assert "Customer finance report" not in content
    assert "Inventory report" not in content
    assert "Purchasing report" not in content


@pytest.mark.django_db
def test_reports_resolve_custom_date_range(
    client,
) -> None:
    """Expose a validated custom range to reports."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    response = client.get(
        reverse("reports:index"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert response.context["date_range"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )


@pytest.mark.django_db
def test_reports_display_date_validation_errors(
    client,
) -> None:
    """Render invalid custom dates without crashing."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    response = client.get(
        reverse("reports:index"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["date_range"] is None
    assert "Start date must be on or before end date." in content
