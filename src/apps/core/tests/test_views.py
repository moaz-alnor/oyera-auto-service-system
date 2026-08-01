"""Tests for shared application views."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import (
    ensure_default_roles,
)


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
    employee = user_model.objects.create_superuser(
        username="dashboard.employee",
        email="dashboard@example.com",
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


@pytest.mark.django_db
def test_dashboard_displays_actionable_links(
    client,
    monkeypatch,
) -> None:
    """Display direct links for records needing action."""

    from datetime import date, datetime
    from decimal import Decimal
    from types import SimpleNamespace

    from apps.core.selectors import (
        OperationalDashboardAlerts,
        OperationalDashboardMetrics,
    )

    user_model = get_user_model()
    employee = user_model.objects.create_superuser(
        username="dashboard.manager",
        email="manager@example.com",
        password="Strong-Test-Password-2026",
    )
    client.force_login(employee)

    metrics = OperationalDashboardMetrics(
        vehicles_received_today=0,
        open_job_cards=0,
        active_work_orders=0,
        vehicles_ready_for_release=1,
        invoices_awaiting_payment=0,
        low_stock_items=1,
        purchase_orders_awaiting_approval=1,
        supplier_invoices_awaiting_payment=1,
    )

    job = SimpleNamespace(
        pk=11,
        job_number="JOB-000011",
        vehicle_registration_snapshot="UBX-111A",
        customer_name_snapshot="Dashboard Customer",
    )

    inventory_item = SimpleNamespace(
        pk=22,
        product=SimpleNamespace(
            sku="FLT-001",
            name="Oil Filter",
        ),
        location=SimpleNamespace(
            name="Main Parts Store",
        ),
        reorder_level=Decimal("5.000"),
    )

    balance = SimpleNamespace(
        inventory_item=inventory_item,
        available_quantity=Decimal("2.000"),
    )

    purchase_order = SimpleNamespace(
        pk=33,
        purchase_order_number="PO-000033",
        supplier_name_snapshot="Dashboard Supplier",
        submitted_at=datetime(
            2026,
            8,
            1,
            10,
            0,
        ),
    )

    supplier_invoice = SimpleNamespace(
        pk=44,
        supplier_invoice_number="SINV-000044",
        supplier_name_snapshot="Dashboard Supplier",
        due_date=date(2026, 8, 5),
        currency="UGX",
        total=Decimal("250000.00"),
    )

    alerts = OperationalDashboardAlerts(
        release_ready_jobs=(job,),
        low_stock_balances=(balance,),
        submitted_purchase_orders=(purchase_order,),
        unpaid_supplier_invoices=(supplier_invoice,),
    )

    monkeypatch.setattr(
        ("apps.core.views.get_operational_dashboard_metrics"),
        lambda: metrics,
    )
    monkeypatch.setattr(
        ("apps.core.views.get_operational_dashboard_alerts"),
        lambda: alerts,
    )

    response = client.get(reverse("core:dashboard"))

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["alerts"] == alerts

    assert (
        reverse(
            "jobs:detail",
            args=(job.pk,),
        )
        in content
    )
    assert (
        reverse(
            "jobs:release_create",
            args=(job.pk,),
        )
        in content
    )
    assert (
        reverse(
            "inventory:detail",
            args=(inventory_item.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "role",
        "shows_customer_finance",
        "shows_supplier_finance",
    ),
    (
        (RoleName.MANAGER, True, True),
        (RoleName.CASHIER, True, True),
        (RoleName.RECEPTIONIST, False, False),
        (RoleName.TECHNICIAN, False, False),
    ),
)
def test_dashboard_finance_visibility_follows_role(
    client,
    monkeypatch,
    role: RoleName,
    shows_customer_finance: bool,
    shows_supplier_finance: bool,
) -> None:
    """Show financial information only to authorized roles."""

    from decimal import Decimal

    from apps.core.selectors import (
        FinancialDashboardMetrics,
        OperationalDashboardAlerts,
        OperationalDashboardMetrics,
    )

    ensure_default_roles()

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username=(f"dashboard.{role.value.casefold()}".replace(" ", ".")),
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))
    client.force_login(employee)

    operational_metrics = OperationalDashboardMetrics(
        vehicles_received_today=0,
        open_job_cards=0,
        active_work_orders=0,
        vehicles_ready_for_release=0,
        invoices_awaiting_payment=0,
        low_stock_items=0,
        purchase_orders_awaiting_approval=0,
        supplier_invoices_awaiting_payment=0,
    )

    alerts = OperationalDashboardAlerts(
        release_ready_jobs=(),
        low_stock_balances=(),
        submitted_purchase_orders=(),
        unpaid_supplier_invoices=(),
    )

    financial_metrics = FinancialDashboardMetrics(
        currency="UGX",
        customer_outstanding_balance=(Decimal("125000.00")),
        supplier_outstanding_liability=(Decimal("75000.00")),
        overdue_customer_invoices=2,
        overdue_supplier_invoices=1,
    )

    financial_arguments: dict[str, bool] = {}

    def fake_financial_metrics(
        *,
        include_customer_finance: bool,
        include_supplier_finance: bool,
        currency: str = "UGX",
    ) -> FinancialDashboardMetrics:
        financial_arguments.update(
            {
                "include_customer_finance": (include_customer_finance),
                "include_supplier_finance": (include_supplier_finance),
            }
        )

        assert currency == "UGX"

        return financial_metrics

    monkeypatch.setattr(
        ("apps.core.views.get_operational_dashboard_metrics"),
        lambda: operational_metrics,
    )
    monkeypatch.setattr(
        ("apps.core.views.get_operational_dashboard_alerts"),
        lambda: alerts,
    )
    monkeypatch.setattr(
        ("apps.core.views.get_financial_dashboard_metrics"),
        fake_financial_metrics,
    )

    response = client.get(reverse("core:dashboard"))

    content = response.content.decode()

    assert response.status_code == 200

    assert financial_arguments == {
        "include_customer_finance": (shows_customer_finance),
        "include_supplier_finance": (shows_supplier_finance),
    }

    customer_labels = (
        "Outstanding customer balance",
        "Overdue customer invoices",
    )
    supplier_labels = (
        "Outstanding supplier liability",
        "Overdue supplier invoices",
    )

    for label in customer_labels:
        assert (label in content) is (shows_customer_finance)

    for label in supplier_labels:
        assert (label in content) is (shows_supplier_finance)
