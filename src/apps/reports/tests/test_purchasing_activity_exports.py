"""Tests for Purchasing activity CSV exports."""

import csv
from datetime import (
    date,
    datetime,
    timedelta,
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
from apps.reports.exports.purchasing_activity import (
    build_purchasing_activity_csv,
)
from apps.reports.selectors.purchasing_activity import (
    PurchasingActivityReport,
    PurchasingActivitySummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create an employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"purchasing.export.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


def _purchasing_report(
    *,
    supplier_name: str = ("Report Parts Supplier"),
    purchase_order_reference: str = ("SUP-PO-201"),
    delivery_reference: str = ("DELIVERY-REPORT-202"),
    invoice_reference: str = ("SUP-REPORT-203"),
    payment_reference: str = ("BANK-REPORT-204"),
) -> PurchasingActivityReport:
    """Return one Purchasing report fixture."""

    event_time = timezone.make_aware(datetime(2026, 7, 15, 10, 30))

    manager = SimpleNamespace(username="purchasing.manager")
    cashier = SimpleNamespace(username="purchasing.cashier")

    purchase_order = SimpleNamespace(
        pk=201,
        purchase_order_number="PO-000201",
        supplier_number_snapshot="SUP-201",
        supplier_name_snapshot=supplier_name,
        currency="UGX",
        supplier_reference=(purchase_order_reference),
        created_at=event_time,
        created_by=manager,
        submitted_at=(event_time + timedelta(hours=1)),
        submitted_by=manager,
        approved_at=(event_time + timedelta(hours=2)),
        approved_by=manager,
        cancelled_at=None,
        cancelled_by=None,
        cancellation_reason="",
        get_status_display=lambda: "Approved",
    )

    goods_receipt = SimpleNamespace(
        pk=202,
        goods_receipt_number="GRN-000202",
        purchase_order=purchase_order,
        purchase_order_number_snapshot=("PO-000201"),
        supplier_number_snapshot="SUP-201",
        supplier_name_snapshot=supplier_name,
        supplier_delivery_reference=(delivery_reference),
        received_at=(event_time + timedelta(hours=3)),
        received_by=manager,
        notes="Received in good condition.",
    )

    supplier_invoice = SimpleNamespace(
        pk=203,
        supplier_invoice_number="SINV-000203",
        supplier_reference=invoice_reference,
        supplier_number_snapshot="SUP-201",
        supplier_name_snapshot=supplier_name,
        purchase_order=purchase_order,
        purchase_order_number_snapshot=("PO-000201"),
        currency="UGX",
        invoice_date=date(2026, 7, 15),
        due_date=date(2026, 7, 20),
        total=Decimal("100000.00"),
        posted_at=(event_time + timedelta(hours=4)),
        posted_by=manager,
        voided_at=None,
        voided_by=None,
        void_reason="",
        notes="Matched to received goods.",
        posted_payment_total=(Decimal("40000.00")),
        outstanding_amount=(Decimal("60000.00")),
        get_status_display=lambda: "Partially paid",
    )

    supplier_payment = SimpleNamespace(
        pk=204,
        payment_number="SPAY-000204",
        supplier_invoice=supplier_invoice,
        currency="UGX",
        amount=Decimal("40000.00"),
        paid_at=(event_time + timedelta(hours=5)),
        external_reference=(payment_reference),
        recorded_by=cashier,
        voided_at=None,
        voided_by=None,
        void_reason="",
        notes="Paid by bank transfer.",
        get_method_display=lambda: "Bank transfer",
        get_status_display=lambda: "Posted",
    )

    return PurchasingActivityReport(
        summary=PurchasingActivitySummary(
            currency="UGX",
            purchase_orders_created_count=1,
            purchase_orders_submitted_count=1,
            purchase_orders_approved_count=1,
            purchase_orders_cancelled_count=0,
            goods_receipts_count=1,
            supplier_invoices_posted_count=1,
            supplier_invoices_voided_count=0,
            supplier_payments_posted_count=1,
            supplier_payments_voided_count=0,
            supplier_payment_total=(Decimal("40000.00")),
            current_open_invoice_count=1,
            current_outstanding_liability=(Decimal("60000.00")),
            current_overdue_invoice_count=1,
        ),
        purchase_orders=(purchase_order,),
        goods_receipts=(goods_receipt,),
        supplier_invoices=(supplier_invoice,),
        supplier_payments=(supplier_payment,),
        open_supplier_invoices=(supplier_invoice,),
    )


@pytest.mark.django_db
def test_purchasing_export_requires_login(
    client,
) -> None:
    """Redirect anonymous export requests to login."""

    export_url = reverse("reports:purchasing_activity_export")

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
        RoleName.CASHIER,
    ),
)
def test_authorized_roles_export_purchasing_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved roles to download CSV."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:purchasing_activity_export"))

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
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_export_purchasing_report(
    client,
    role: RoleName,
) -> None:
    """Require Purchasing-view and export permissions."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:purchasing_activity_export"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_purchasing_export_contains_report_data(
    client,
    monkeypatch,
) -> None:
    """Export activity and liability audit rows."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    report = _purchasing_report()

    selected_values: dict[str, object] = {}

    def fake_report(
        *,
        date_range: ReportDateRange,
        as_of_date: date,
    ) -> PurchasingActivityReport:
        selected_values["date_range"] = date_range
        selected_values["as_of_date"] = as_of_date

        return report

    monkeypatch.setattr(
        ("apps.reports.views.get_purchasing_activity_report"),
        fake_report,
    )

    response = client.get(
        reverse("reports:purchasing_activity_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="purchasing-activity-2026-07-01-to-2026-07-31.csv"'
    )

    assert selected_values["date_range"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    assert [
        "Purchase orders created",
        "1",
    ] in rows
    assert [
        "Supplier payment total",
        "40000.00",
    ] in rows
    assert [
        "Outstanding supplier liability",
        "60000.00",
    ] in rows

    assert [
        "PO-000201",
        "SUP-201",
        "Report Parts Supplier",
        "Approved",
        "UGX",
        "SUP-PO-201",
        "2026-07-15 10:30:00",
        "purchasing.manager",
        "2026-07-15 11:30:00",
        "purchasing.manager",
        "2026-07-15 12:30:00",
        "purchasing.manager",
        "",
        "",
        "",
    ] in rows

    assert [
        "GRN-000202",
        "PO-000201",
        "SUP-201",
        "Report Parts Supplier",
        "2026-07-15 13:30:00",
        "DELIVERY-REPORT-202",
        "purchasing.manager",
        "Received in good condition.",
    ] in rows

    assert [
        "SINV-000203",
        "SUP-REPORT-203",
        "SUP-201",
        "Report Parts Supplier",
        "PO-000201",
        "2026-07-15",
        "2026-07-20",
        "Partially paid",
        "UGX",
        "100000.00",
        "2026-07-15 14:30:00",
        "purchasing.manager",
        "",
        "",
        "",
        "Matched to received goods.",
    ] in rows

    assert [
        "SPAY-000204",
        "SINV-000203",
        "Report Parts Supplier",
        "2026-07-15 15:30:00",
        "40000.00",
        "UGX",
        "Bank transfer",
        "Posted",
        "BANK-REPORT-204",
        "purchasing.cashier",
        "",
        "",
        "",
        "Paid by bank transfer.",
    ] in rows

    assert [
        "SINV-000203",
        "Report Parts Supplier",
        "PO-000201",
        "2026-07-20",
        "Partially paid",
        "UGX",
        "100000.00",
        "40000.00",
        "60000.00",
        "Yes",
    ] in rows


@pytest.mark.django_db
def test_invalid_purchasing_export_dates_skip_query(
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

        raise AssertionError("Purchasing selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_purchasing_activity_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:purchasing_activity_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    assert response.status_code == 400
    assert not selector_called
    assert "Invalid Purchasing activity report filters." in response.content.decode()


def test_purchasing_csv_protects_formula_cells() -> None:
    """Prevent user-controlled cells becoming formulas."""

    report = _purchasing_report(
        supplier_name="=2+2",
        purchase_order_reference="+PO-COMMAND",
        delivery_reference="@DELIVERY-COMMAND",
        invoice_reference="-INVOICE-COMMAND",
        payment_reference="=PAYMENT-COMMAND",
    )

    content = build_purchasing_activity_csv(
        report=report,
        date_range=ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        ),
        as_of_date=date(2026, 7, 31),
    )

    rows = list(csv.reader(StringIO(content.lstrip("\ufeff"))))

    order_row = next(row for row in rows if row and row[0] == "PO-000201")
    receipt_row = next(row for row in rows if row and row[0] == "GRN-000202")
    invoice_row = next(
        row for row in rows if row and row[0] == "SINV-000203" and len(row) == 16
    )
    payment_row = next(row for row in rows if row and row[0] == "SPAY-000204")
    open_invoice_row = next(
        row for row in rows if row and row[0] == "SINV-000203" and len(row) == 10
    )

    assert order_row[2] == "'=2+2"
    assert order_row[5] == "'+PO-COMMAND"

    assert receipt_row[3] == "'=2+2"
    assert receipt_row[5] == "'@DELIVERY-COMMAND"

    assert invoice_row[1] == "'-INVOICE-COMMAND"
    assert invoice_row[3] == "'=2+2"

    assert payment_row[2] == "'=2+2"
    assert payment_row[8] == "'=PAYMENT-COMMAND"

    assert open_invoice_row[1] == "'=2+2"
