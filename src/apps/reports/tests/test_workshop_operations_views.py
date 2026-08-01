"""Tests for the workshop operations report interface."""

from datetime import (
    date,
    datetime,
)
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
        username=(f"workshop.report.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


@pytest.mark.django_db
def test_workshop_report_requires_login(
    client,
) -> None:
    """Redirect anonymous users to login."""

    report_url = reverse("reports:workshop_operations")

    response = client.get(report_url)

    assert response.status_code == 302
    assert response.headers["Location"] == (
        f"{reverse('accounts:login')}?next={report_url}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.MANAGER,
        RoleName.RECEPTIONIST,
        RoleName.SENIOR_TECHNICIAN,
    ),
)
def test_authorized_roles_open_workshop_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved roles to view workshop reports."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:workshop_operations"))

    assert response.status_code == 200
    assert "Workshop operations report" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.CASHIER,
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_open_workshop_report(
    client,
    role: RoleName,
) -> None:
    """Deny workshop reporting without permission."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:workshop_operations"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_workshop_report_displays_summary_and_audit_rows(
    client,
    monkeypatch,
) -> None:
    """Display workshop totals and linked audit rows."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    event_time = timezone.make_aware(datetime(2026, 7, 15, 10, 30))

    job_card = SimpleNamespace(
        pk=21,
        job_number="JOB-000021",
        customer_name_snapshot=("Workshop Report Customer"),
        vehicle_registration_snapshot=("UBX-921A"),
        arrival_at=event_time,
        get_priority_display=lambda: "Urgent",
        get_status_display=lambda: "Open",
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
        received_by_name="Daniel Kato",
        invoice_number_snapshot="INV-000041",
        invoice_currency_snapshot="UGX",
        outstanding_amount_snapshot=0,
        payment_override=True,
    )

    report = WorkshopOperationsReport(
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
        reverse("reports:workshop_operations"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["report"] == report
    assert selected_range["value"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    assert "Vehicles received" in content
    assert "Urgent job cards" in content
    assert "Work orders completed" in content
    assert "Payment-override releases" in content

    assert "JOB-000021" in content
    assert "WO-000031" in content
    assert "REL-000041" in content
    assert "Workshop Report Customer" in content
    assert "UBX-921A" in content

    assert (
        reverse(
            "jobs:detail",
            args=(job_card.pk,),
        )
        in content
    )
    assert (
        reverse(
            "workshop:detail",
            args=(work_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "jobs:release_detail",
            args=(release.pk,),
        )
        in content
    )


@pytest.mark.django_db
def test_invalid_workshop_dates_skip_report_query(
    client,
    monkeypatch,
) -> None:
    """Render errors without running report queries."""

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
        reverse("reports:workshop_operations"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["report"] is None
    assert not selector_called
    assert "Start date must be on or before end date." in content
