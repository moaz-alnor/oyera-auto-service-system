"""Tests for workshop operations CSV exports."""

import csv
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import (
    ensure_default_roles,
)
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.workshop_operations import (
    build_workshop_operations_csv,
)
from apps.reports.selectors.workshop_operations import (
    WorkshopOperationsReport,
    WorkshopOperationsSummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create one employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"workshop.export.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


def _workshop_report(
    *,
    customer_name: str = "Export Customer",
    received_by: str = "Daniel Kato",
) -> WorkshopOperationsReport:
    """Return one workshop report fixture."""

    event_time = timezone.make_aware(datetime(2026, 7, 15, 10, 30))

    job_card = SimpleNamespace(
        pk=21,
        job_number="JOB-000021",
        customer_name_snapshot=customer_name,
        vehicle_registration_snapshot="UBX-921A",
        arrival_at=event_time,
        get_priority_display=lambda: "Urgent",
        get_status_display=lambda: "Released",
    )

    work_order = SimpleNamespace(
        pk=31,
        work_order_number="WO-000031",
        job_card=job_card,
        created_at=event_time,
        started_at=event_time,
        completed_at=None,
        get_status_display=lambda: "In progress",
    )

    release = SimpleNamespace(
        pk=41,
        release_number="REL-000041",
        job_card=job_card,
        released_at=event_time,
        received_by_name=received_by,
        invoice_number_snapshot="INV-000041",
        invoice_currency_snapshot="UGX",
        outstanding_amount_snapshot=(Decimal("0.00")),
        payment_override=True,
    )

    return WorkshopOperationsReport(
        summary=WorkshopOperationsSummary(
            vehicles_received_count=1,
            urgent_job_count=1,
            cancelled_job_count=0,
            work_orders_created_count=1,
            work_orders_started_count=1,
            work_orders_completed_count=0,
            vehicles_released_count=1,
            payment_override_release_count=1,
        ),
        job_cards=(job_card,),
        work_orders=(work_order,),
        releases=(release,),
    )


@pytest.mark.django_db
def test_workshop_export_requires_login(
    client,
) -> None:
    """Redirect anonymous export requests to login."""

    export_url = reverse("reports:workshop_operations_export")

    response = client.get(export_url)

    assert response.status_code == 302
    assert response.headers["Location"] == (
        f"{reverse('accounts:login')}?next={export_url}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.ADMINISTRATOR,
        RoleName.MANAGER,
    ),
)
def test_authorized_roles_export_workshop_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved export roles to download CSV."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:workshop_operations_export"))

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "attachment;" in response.headers["Content-Disposition"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.RECEPTIONIST,
        RoleName.SENIOR_TECHNICIAN,
        RoleName.CASHIER,
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_export_workshop_report(
    client,
    role: RoleName,
) -> None:
    """Require both workshop and export permissions."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:workshop_operations_export"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_workshop_export_contains_report_data(
    client,
    monkeypatch,
) -> None:
    """Export summary and operational audit rows."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    report = _workshop_report()

    selected_range: dict[
        str,
        ReportDateRange,
    ] = {}

    def fake_report(
        *,
        date_range: ReportDateRange,
    ) -> WorkshopOperationsReport:
        selected_range["value"] = date_range

        return report

    monkeypatch.setattr(
        ("apps.reports.views.get_workshop_operations_report"),
        fake_report,
    )

    response = client.get(
        reverse("reports:workshop_operations_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="workshop-operations-2026-07-01-to-2026-07-31.csv"'
    )

    assert selected_range["value"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    assert [
        "Vehicles received",
        "1",
    ] in rows

    assert [
        "JOB-000021",
        "Export Customer",
        "UBX-921A",
        "2026-07-15 10:30:00",
        "Urgent",
        "Released",
    ] in rows

    assert [
        "WO-000031",
        "JOB-000021",
        "UBX-921A",
        "2026-07-15 10:30:00",
        "2026-07-15 10:30:00",
        "",
        "In progress",
    ] in rows

    assert [
        "REL-000041",
        "JOB-000021",
        "UBX-921A",
        "2026-07-15 10:30:00",
        "Daniel Kato",
        "INV-000041",
        "UGX",
        "0.00",
        "Yes",
    ] in rows


@pytest.mark.django_db
def test_invalid_workshop_export_dates_skip_query(
    client,
    monkeypatch,
) -> None:
    """Return HTTP 400 without running the selector."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    selector_called = False

    def fail_if_called(**_kwargs):
        nonlocal selector_called
        selector_called = True

        raise AssertionError("Workshop selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_workshop_operations_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:workshop_operations_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    assert response.status_code == 400
    assert not selector_called
    assert "Invalid workshop operations report filters." in response.content.decode()


def test_workshop_csv_protects_formula_cells() -> None:
    """Prevent user-controlled cells becoming formulas."""

    report = _workshop_report(
        customer_name="=2+2",
        received_by="+COMMAND",
    )

    content = build_workshop_operations_csv(
        report=report,
        date_range=ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        ),
    )

    rows = list(csv.reader(StringIO(content.lstrip("\ufeff"))))

    job_row = next(row for row in rows if row and row[0] == "JOB-000021")
    release_row = next(row for row in rows if row and row[0] == "REL-000041")

    assert job_row[1] == "'=2+2"
    assert release_row[4] == "'+COMMAND"
