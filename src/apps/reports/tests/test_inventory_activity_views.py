"""Tests for the Inventory activity report interface."""

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
from apps.inventory.selectors import InventoryBalance
from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.inventory_activity import (
    InventoryActivityReport,
    InventoryActivitySummary,
)


def _create_role_user(
    *,
    role: RoleName,
):
    """Create one employee with a synchronized role."""

    ensure_default_roles()

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=(f"inventory.report.{role.value.casefold()}").replace(" ", "."),
        password="Strong-Test-Password-2026",
    )

    user.groups.add(Group.objects.get(name=role.value))

    return user


@pytest.mark.django_db
def test_inventory_report_requires_login(
    client,
) -> None:
    """Redirect anonymous users to login."""

    report_url = reverse("reports:inventory_activity")

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
    ),
)
def test_authorized_roles_open_inventory_report(
    client,
    role: RoleName,
) -> None:
    """Allow approved roles to view Inventory reports."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:inventory_activity"))

    assert response.status_code == 200
    assert "Inventory activity report" in response.content.decode()


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
def test_unauthorized_roles_cannot_open_inventory_report(
    client,
    role: RoleName,
) -> None:
    """Deny Inventory reporting without permission."""

    employee = _create_role_user(role=role)
    client.force_login(employee)

    response = client.get(reverse("reports:inventory_activity"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_inventory_report_displays_summary_and_audit_rows(
    client,
    monkeypatch,
) -> None:
    """Display movement totals and current stock risks."""

    manager = _create_role_user(role=RoleName.MANAGER)
    client.force_login(manager)

    event_time = timezone.make_aware(datetime(2026, 7, 15, 10, 30))

    inventory_item = SimpleNamespace(
        pk=51,
        reorder_level=Decimal("5.000"),
        product=SimpleNamespace(
            sku="FILTER-001",
            name="Engine Oil Filter",
        ),
        location=SimpleNamespace(
            code="MAIN-STORE",
            name="Main Parts Store",
        ),
    )

    movement = SimpleNamespace(
        pk=61,
        movement_number="MOV-000061",
        inventory_item=inventory_item,
        occurred_at=event_time,
        signed_quantity=Decimal("4.000"),
        external_reference="GRN-000061",
        created_by=SimpleNamespace(username="inventory.manager"),
        get_movement_type_display=lambda: "Stock receipt",
    )

    balance = InventoryBalance(
        inventory_item=inventory_item,
        on_hand_quantity=Decimal("5.000"),
        reserved_quantity=Decimal("1.000"),
        available_quantity=Decimal("4.000"),
    )

    report = InventoryActivityReport(
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
        reverse("reports:inventory_activity"),
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

    assert "Stock movements" in content
    assert "Inventory items moved" in content
    assert "Workshop issues" in content
    assert "Current low-stock items" in content

    assert "MOV-000061" in content
    assert "FILTER-001" in content
    assert "Engine Oil Filter" in content
    assert "MAIN-STORE" in content
    assert "GRN-000061" in content

    assert (
        reverse(
            "inventory:detail",
            args=(inventory_item.pk,),
        )
        in content
    )

    normalized_content = " ".join(content.split())

    assert "This section shows current inventory balances." in normalized_content


@pytest.mark.django_db
def test_invalid_inventory_dates_skip_report_query(
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

        raise AssertionError("Inventory selector must not run.")

    monkeypatch.setattr(
        ("apps.reports.views.get_inventory_activity_report"),
        fail_if_called,
    )

    response = client.get(
        reverse("reports:inventory_activity"),
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
