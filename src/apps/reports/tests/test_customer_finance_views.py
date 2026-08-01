"""Tests for the customer finance report interface."""

from datetime import (
    date,
    datetime,
)
from decimal import Decimal
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
from apps.billing.constants import InvoiceStatus
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.customer_finance import (
    CustomerFinanceInvoiceRow,
    CustomerFinanceReport,
    CustomerFinanceSummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create one employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"customer.report.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


@pytest.mark.django_db
def test_customer_finance_report_requires_login(
    client,
) -> None:
    """Redirect anonymous users to login."""

    report_url = reverse("reports:customer_finance")

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
        RoleName.CASHIER,
    ),
)
def test_authorized_roles_open_customer_finance_report(
    client,
    role: RoleName,
) -> None:
    """Allow financial-report roles to open the page."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:customer_finance"))

    assert response.status_code == 200
    assert "Customer finance report" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.RECEPTIONIST,
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_open_customer_finance_report(
    client,
    role: RoleName,
) -> None:
    """Deny customer financial reporting access."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:customer_finance"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_finance_report_displays_summary_and_invoice(
    client,
    monkeypatch,
) -> None:
    """Display the selected finance report and audit row."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    issued_at = timezone.make_aware(datetime(2026, 7, 15, 10, 30))

    invoice = SimpleNamespace(
        pk=17,
        invoice_number="INV-000017",
        customer_name_snapshot=("Finance Report Customer"),
        vehicle_registration_snapshot=("UBX-717A"),
        issued_at=issued_at,
        due_date=date(2026, 7, 20),
        status=InvoiceStatus.PARTIALLY_PAID,
        currency="UGX",
        total=Decimal("80000.00"),
        get_status_display=lambda: "Partially paid",
    )

    report = CustomerFinanceReport(
        summary=CustomerFinanceSummary(
            currency="UGX",
            invoice_count=1,
            invoice_total=Decimal("80000.00"),
            posted_payment_total=(Decimal("30000.00")),
            outstanding_balance=(Decimal("50000.00")),
            paid_invoice_count=0,
            partially_paid_invoice_count=1,
            overdue_invoice_count=1,
            voided_invoice_count=0,
        ),
        invoices=(
            CustomerFinanceInvoiceRow(
                invoice=invoice,
                paid_amount=Decimal("30000.00"),
                outstanding_amount=(Decimal("50000.00")),
                is_overdue=True,
            ),
        ),
    )

    selected_range: dict[
        str,
        ReportDateRange,
    ] = {}

    def fake_report(
        *,
        date_range: ReportDateRange,
        currency: str = "UGX",
        as_of_date=None,
    ) -> CustomerFinanceReport:
        selected_range["value"] = date_range

        assert currency == "UGX"
        assert as_of_date is None

        return report

    monkeypatch.setattr(
        ("apps.reports.views.get_customer_finance_report"),
        fake_report,
    )

    response = client.get(
        reverse("reports:customer_finance"),
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

    assert "Invoice total" in content
    assert "Posted payments" in content
    assert "Outstanding balance" in content
    assert "Overdue invoices" in content
    assert "INV-000017" in content
    assert "Finance Report Customer" in content
    assert "UBX-717A" in content
    assert "Overdue" in content

    assert (
        reverse(
            "billing:detail",
            args=(invoice.pk,),
        )
        in content
    )


@pytest.mark.django_db
def test_invalid_customer_finance_dates_skip_report_query(
    client,
    monkeypatch,
) -> None:
    """Render validation errors without running report queries."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    selector_mock = SimpleNamespace(called=False)

    def fail_if_called(**_kwargs):
        selector_mock.called = True

        raise AssertionError("Report selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_customer_finance_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:customer_finance"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["report"] is None
    assert not selector_mock.called
    assert "Start date must be on or before end date." in content
