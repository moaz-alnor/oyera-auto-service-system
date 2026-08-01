"""Tests for customer finance CSV exports."""

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
from apps.billing.constants import InvoiceStatus
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.customer_finance import (
    build_customer_finance_csv,
)
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
        username=(f"customer.export.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


def _customer_finance_report(
    *,
    customer_name: str = "Export Customer",
    vehicle_registration: str = "UBX-818A",
) -> CustomerFinanceReport:
    """Return one customer-finance report fixture."""

    invoice = SimpleNamespace(
        pk=18,
        invoice_number="INV-000018",
        customer_name_snapshot=customer_name,
        vehicle_registration_snapshot=(vehicle_registration),
        issued_at=timezone.make_aware(datetime(2026, 7, 15, 10, 30)),
        due_date=date(2026, 7, 20),
        status=InvoiceStatus.PARTIALLY_PAID,
        currency="UGX",
        total=Decimal("80000.00"),
        get_status_display=lambda: "Partially paid",
    )

    return CustomerFinanceReport(
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


@pytest.mark.django_db
def test_customer_finance_export_requires_login(
    client,
) -> None:
    """Redirect anonymous export requests to login."""

    export_url = reverse("reports:customer_finance_export")

    response = client.get(export_url)

    assert response.status_code == 302
    assert response.headers["Location"] == (
        f"{reverse('accounts:login')}?next={export_url}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.MANAGER,
        RoleName.CASHIER,
    ),
)
def test_authorized_roles_export_customer_finance(
    client,
    role: RoleName,
) -> None:
    """Allow report-export roles to download CSV."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:customer_finance_export"))

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "attachment;" in response.headers["Content-Disposition"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.RECEPTIONIST,
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_export_customer_finance(
    client,
    role: RoleName,
) -> None:
    """Deny CSV export without export permission."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:customer_finance_export"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_finance_export_contains_report_data(
    client,
    monkeypatch,
) -> None:
    """Export summary values and invoice audit rows."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    report = _customer_finance_report()

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
        reverse("reports:customer_finance_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="customer-finance-2026-07-01-to-2026-07-31.csv"'
    )

    assert selected_range["value"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    decoded = response.content.decode("utf-8-sig")
    rows = list(csv.reader(StringIO(decoded)))

    assert [
        "Report start",
        "2026-07-01",
    ] in rows
    assert [
        "Invoice total",
        "80000.00",
    ] in rows
    assert [
        "Posted payments",
        "30000.00",
    ] in rows
    assert [
        "Outstanding balance",
        "50000.00",
    ] in rows

    assert [
        "INV-000018",
        "Export Customer",
        "UBX-818A",
        "2026-07-15 10:30:00",
        "2026-07-20",
        "Partially paid",
        "Yes",
        "UGX",
        "80000.00",
        "30000.00",
        "50000.00",
    ] in rows


@pytest.mark.django_db
def test_invalid_export_dates_skip_report_query(
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

        raise AssertionError("Report selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_customer_finance_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:customer_finance_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    assert response.status_code == 400
    assert not selector_called
    assert "Invalid customer finance report filters." in response.content.decode()


def test_customer_finance_csv_protects_formula_cells() -> None:
    """Prevent user-controlled cells becoming formulas."""

    report = _customer_finance_report(
        customer_name="=2+2",
        vehicle_registration="+COMMAND",
    )

    content = build_customer_finance_csv(
        report=report,
        date_range=ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        ),
    )

    rows = list(csv.reader(StringIO(content.lstrip("\ufeff"))))

    invoice_row = next(row for row in rows if row and row[0] == "INV-000018")

    assert invoice_row[1] == "'=2+2"
    assert invoice_row[2] == "'+COMMAND"
