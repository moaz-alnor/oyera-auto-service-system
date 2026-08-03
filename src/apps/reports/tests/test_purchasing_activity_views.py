"""Tests for the Purchasing activity report interface."""

from datetime import (
    date,
    datetime,
    timedelta,
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
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.purchasing_activity import (
    PurchasingActivityReport,
    PurchasingActivitySummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create one employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"purchasing.report.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


@pytest.mark.django_db
def test_purchasing_report_requires_login(
    client,
) -> None:
    """Redirect anonymous users to login."""

    report_url = reverse("reports:purchasing_activity")

    response = client.get(report_url)

    assert response.status_code == 302
    assert response.headers["Location"] == (
        f"{reverse('accounts:login')}?next={report_url}"
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
def test_authorized_roles_open_purchasing_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved roles to view Purchasing reports."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:purchasing_activity"))

    assert response.status_code == 200
    assert "Purchasing activity report" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        RoleName.RECEPTIONIST,
        RoleName.SENIOR_TECHNICIAN,
        RoleName.TECHNICIAN,
    ),
)
def test_unauthorized_roles_cannot_open_purchasing_report(
    client,
    role: RoleName,
) -> None:
    """Deny Purchasing reporting without permission."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:purchasing_activity"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_purchasing_report_displays_summary_and_audit_rows(
    client,
    monkeypatch,
) -> None:
    """Display purchasing activity and liabilities."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    event_time = timezone.make_aware(datetime(2026, 7, 15, 10, 30))
    report_date = event_time.date()

    purchase_order = SimpleNamespace(
        pk=101,
        purchase_order_number="PO-000101",
        supplier_name_snapshot=("Report Parts Supplier"),
        currency="UGX",
        created_at=event_time,
        submitted_at=(event_time + timedelta(hours=1)),
        approved_at=(event_time + timedelta(hours=2)),
        cancelled_at=None,
        get_status_display=lambda: "Approved",
    )

    goods_receipt = SimpleNamespace(
        pk=102,
        goods_receipt_number="GRN-000102",
        purchase_order=purchase_order,
        purchase_order_number_snapshot=("PO-000101"),
        supplier_name_snapshot=("Report Parts Supplier"),
        supplier_delivery_reference=("DELIVERY-REPORT-102"),
        received_at=(event_time + timedelta(hours=3)),
        received_by=SimpleNamespace(username="purchasing.manager"),
    )

    supplier_invoice = SimpleNamespace(
        pk=103,
        supplier_invoice_number="SINV-000103",
        supplier_reference="SUP-REPORT-103",
        supplier_name_snapshot=("Report Parts Supplier"),
        purchase_order=purchase_order,
        purchase_order_number_snapshot=("PO-000101"),
        currency="UGX",
        invoice_date=report_date,
        due_date=report_date,
        total=Decimal("100000.00"),
        posted_at=(event_time + timedelta(hours=4)),
        voided_at=None,
        posted_payment_total=(Decimal("40000.00")),
        outstanding_amount=(Decimal("60000.00")),
        get_status_display=lambda: "Partially paid",
    )

    supplier_payment = SimpleNamespace(
        pk=104,
        payment_number="SPAY-000104",
        supplier_invoice=supplier_invoice,
        currency="UGX",
        amount=Decimal("40000.00"),
        paid_at=(event_time + timedelta(hours=5)),
        voided_at=None,
        external_reference=("BANK-REPORT-104"),
        recorded_by=SimpleNamespace(username="purchasing.cashier"),
        get_method_display=lambda: "Bank transfer",
        get_status_display=lambda: "Posted",
    )

    report = PurchasingActivityReport(
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

    selected_range: dict[
        str,
        ReportDateRange,
    ] = {}

    def fake_report(
        *,
        date_range: ReportDateRange,
        as_of_date: date,
    ) -> PurchasingActivityReport:
        selected_range["value"] = date_range
        selected_range["as_of_date"] = as_of_date

        return report

    monkeypatch.setattr(
        ("apps.reports.views.get_purchasing_activity_report"),
        fake_report,
    )

    response = client.get(
        reverse("reports:purchasing_activity"),
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

    assert "Purchase orders created" in content
    assert "Goods receipts posted" in content
    assert "Supplier payments during period" in content
    assert "Current outstanding liability" in content

    assert "PO-000101" in content
    assert "GRN-000102" in content
    assert "SINV-000103" in content
    assert "SPAY-000104" in content
    assert "Report Parts Supplier" in content
    assert "DELIVERY-REPORT-102" in content
    assert "BANK-REPORT-104" in content
    assert "60000.00" in content

    assert (
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:goods_receipt_detail",
            args=(goods_receipt.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(supplier_invoice.pk,),
        )
        in content
    )

    normalized_content = " ".join(content.split())

    assert "This section is a current liability snapshot" in normalized_content


@pytest.mark.django_db
def test_invalid_purchasing_dates_skip_report_query(
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

        raise AssertionError("Purchasing selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_purchasing_activity_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:purchasing_activity"),
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
