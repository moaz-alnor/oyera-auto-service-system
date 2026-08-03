"""Tests for Inventory activity CSV exports."""

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
from apps.inventory.selectors import InventoryBalance
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.inventory_activity import (
    build_inventory_activity_csv,
)
from apps.reports.selectors.inventory_activity import (
    InventoryActivityReport,
    InventoryActivitySummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create an employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"inventory.export.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


def _inventory_report(
    *,
    product_name: str = "Engine Oil Filter",
    location_name: str = "Main Parts Store",
    external_reference: str = "GRN-000071",
) -> InventoryActivityReport:
    """Return one Inventory activity report fixture."""

    inventory_item = SimpleNamespace(
        pk=71,
        reorder_level=Decimal("5.000"),
        product=SimpleNamespace(
            sku="FILTER-001",
            name=product_name,
        ),
        location=SimpleNamespace(
            code="MAIN-STORE",
            name=location_name,
        ),
    )

    movement = SimpleNamespace(
        pk=81,
        movement_number="MOV-000071",
        inventory_item=inventory_item,
        occurred_at=timezone.make_aware(datetime(2026, 7, 15, 10, 30)),
        signed_quantity=Decimal("4.000"),
        unit_cost=Decimal("25000.00"),
        currency="UGX",
        external_reference=external_reference,
        notes="Received for report.",
        created_by=SimpleNamespace(username="inventory.manager"),
        get_movement_type_display=lambda: "Stock receipt",
    )

    balance = InventoryBalance(
        inventory_item=inventory_item,
        on_hand_quantity=Decimal("5.000"),
        reserved_quantity=Decimal("1.000"),
        available_quantity=Decimal("4.000"),
    )

    return InventoryActivityReport(
        summary=InventoryActivitySummary(
            movement_count=1,
            items_moved_count=1,
            receipt_count=1,
            issue_count=0,
            return_count=0,
            positive_adjustment_count=0,
            negative_adjustment_count=0,
            low_stock_item_count=1,
        ),
        movements=(movement,),
        low_stock_balances=(balance,),
    )


@pytest.mark.django_db
def test_inventory_export_requires_login(
    client,
) -> None:
    """Redirect anonymous export requests to login."""

    export_url = reverse("reports:inventory_activity_export")

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
def test_authorized_roles_export_inventory_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved roles to download Inventory CSV."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:inventory_activity_export"))

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
def test_unauthorized_roles_cannot_export_inventory_report(
    client,
    role: RoleName,
) -> None:
    """Require Inventory-view and export permissions."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:inventory_activity_export"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_inventory_export_contains_report_data(
    client,
    monkeypatch,
) -> None:
    """Export movement and low-stock audit data."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    report = _inventory_report()

    selected_range: dict[
        str,
        ReportDateRange,
    ] = {}

    def fake_report(
        *,
        date_range: ReportDateRange,
    ) -> InventoryActivityReport:
        selected_range["value"] = date_range

        return report

    monkeypatch.setattr(
        ("apps.reports.views.get_inventory_activity_report"),
        fake_report,
    )

    response = client.get(
        reverse("reports:inventory_activity_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="inventory-activity-2026-07-01-to-2026-07-31.csv"'
    )

    assert selected_range["value"] == (
        ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    assert [
        "Stock movements",
        "1",
    ] in rows
    assert [
        "Current low-stock items",
        "1",
    ] in rows

    assert [
        "MOV-000071",
        "FILTER-001",
        "Engine Oil Filter",
        "MAIN-STORE",
        "Main Parts Store",
        "2026-07-15 10:30:00",
        "Stock receipt",
        "4.000",
        "25000.00",
        "UGX",
        "GRN-000071",
        "Received for report.",
        "inventory.manager",
    ] in rows

    assert [
        "FILTER-001",
        "Engine Oil Filter",
        "MAIN-STORE",
        "Main Parts Store",
        "5.000",
        "1.000",
        "4.000",
        "5.000",
    ] in rows


@pytest.mark.django_db
def test_invalid_inventory_export_dates_skip_query(
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

        raise AssertionError("Inventory selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_inventory_activity_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:inventory_activity_export"),
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        },
    )

    assert response.status_code == 400
    assert not selector_called
    assert "Invalid Inventory activity report filters." in response.content.decode()


def test_inventory_csv_protects_formula_cells() -> None:
    """Prevent user-controlled cells becoming formulas."""

    report = _inventory_report(
        product_name="=2+2",
        location_name="+STORE",
        external_reference="@COMMAND",
    )

    content = build_inventory_activity_csv(
        report=report,
        date_range=ReportDateRange(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        ),
    )

    rows = list(csv.reader(StringIO(content.lstrip("\ufeff"))))

    movement_row = next(row for row in rows if row and row[0] == "MOV-000071")

    low_stock_row = next(
        row for row in rows if row and row[0] == "FILTER-001" and len(row) == 8
    )

    assert movement_row[2] == "'=2+2"
    assert movement_row[4] == "'+STORE"
    assert movement_row[10] == "'@COMMAND"

    assert low_stock_row[1] == "'=2+2"
    assert low_stock_row[3] == "'+STORE"
