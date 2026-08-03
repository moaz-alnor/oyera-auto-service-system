"""Tests for Inventory activity report selectors."""

from datetime import (
    datetime,
    time,
    timedelta,
)
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory.constants import (
    StockMovementType,
)
from apps.inventory.services.adjustments import (
    AdjustStockCommand,
    adjust_stock,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.tests.conftest import (
    InventoryTestContext,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.inventory_activity import (
    InventoryActivitySummary,
    get_inventory_activity_report,
)


def _event_time(
    *,
    days_ago: int = 1,
    hour: int = 12,
) -> datetime:
    """Return a deterministic historical local time."""

    report_date = timezone.localdate() - timedelta(days=days_ago)

    return timezone.make_aware(
        datetime.combine(
            report_date,
            time(
                hour=hour,
            ),
        ),
        timezone.get_current_timezone(),
    )


@pytest.mark.django_db
def test_inventory_report_calculates_activity(
    inventory_context: InventoryTestContext,
) -> None:
    """Calculate movement and current-risk counts."""

    event_time = _event_time()
    report_date = event_time.date()

    receipt = receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("4.000"),
            unit_cost=Decimal("25000.00"),
            external_reference=("REPORT-RECEIPT-001"),
            occurred_at=event_time,
        ),
    )

    positive_adjustment = adjust_stock(
        actor=inventory_context.manager,
        command=AdjustStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            movement_type=(StockMovementType.ADJUSTMENT_IN),
            quantity=Decimal("2.000"),
            reason=("Inventory reporting adjustment."),
            occurred_at=(event_time + timedelta(hours=1)),
        ),
    )

    negative_adjustment = adjust_stock(
        actor=inventory_context.manager,
        command=AdjustStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            movement_type=(StockMovementType.ADJUSTMENT_OUT),
            quantity=Decimal("1.000"),
            reason=("Inventory reporting correction."),
            occurred_at=(event_time + timedelta(hours=2)),
        ),
    )

    report = get_inventory_activity_report(
        date_range=ReportDateRange(
            start_date=report_date,
            end_date=report_date,
        )
    )

    assert report.summary == (
        InventoryActivitySummary(
            movement_count=3,
            items_moved_count=1,
            receipt_count=1,
            issue_count=0,
            return_count=0,
            positive_adjustment_count=1,
            negative_adjustment_count=1,
            low_stock_item_count=1,
        )
    )

    assert report.movements == (
        negative_adjustment,
        positive_adjustment,
        receipt,
    )

    assert len(report.low_stock_balances) == 1

    balance = report.low_stock_balances[0]

    assert balance.inventory_item == inventory_context.inventory_item
    assert balance.on_hand_quantity == Decimal("5.000")
    assert balance.available_quantity == Decimal("5.000")
    assert balance.is_low_stock


@pytest.mark.django_db
def test_inventory_report_excludes_old_movements(
    inventory_context: InventoryTestContext,
) -> None:
    """Exclude ledger activity outside the period."""

    old_time = _event_time(days_ago=10)

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("4.000"),
            occurred_at=old_time,
        ),
    )

    report_date = timezone.localdate() - timedelta(days=1)

    report = get_inventory_activity_report(
        date_range=ReportDateRange(
            start_date=report_date,
            end_date=report_date,
        )
    )

    assert report.summary == (
        InventoryActivitySummary(
            movement_count=0,
            items_moved_count=0,
            receipt_count=0,
            issue_count=0,
            return_count=0,
            positive_adjustment_count=0,
            negative_adjustment_count=0,
            low_stock_item_count=1,
        )
    )

    assert report.movements == ()

    assert report.low_stock_balances[0].on_hand_quantity == Decimal("4.000")


@pytest.mark.django_db
def test_inventory_report_excludes_inactive_low_stock(
    inventory_context: InventoryTestContext,
) -> None:
    """Exclude inactive items from current low-stock risk."""

    inventory_context.inventory_item.is_active = False
    inventory_context.inventory_item.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    report_date = timezone.localdate() - timedelta(days=1)

    report = get_inventory_activity_report(
        date_range=ReportDateRange(
            start_date=report_date,
            end_date=report_date,
        )
    )

    assert report.summary.low_stock_item_count == 0
    assert report.low_stock_balances == ()


@pytest.mark.django_db
def test_inventory_report_uses_two_queries(
    inventory_context: InventoryTestContext,
    django_assert_num_queries,
) -> None:
    """Keep Inventory reporting query-bounded."""

    event_time = _event_time()

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("4.000"),
            occurred_at=event_time,
        ),
    )

    with django_assert_num_queries(2):
        report = get_inventory_activity_report(
            date_range=ReportDateRange(
                start_date=event_time.date(),
                end_date=event_time.date(),
            )
        )

        movement = report.movements[0]
        balance = report.low_stock_balances[0]

        assert movement.inventory_item.product.name == inventory_context.product.name
        assert movement.inventory_item.location.name == inventory_context.location.name
        assert movement.created_by.username == inventory_context.manager.username
        assert balance.inventory_item.product.sku == inventory_context.product.sku
        assert balance.inventory_item.location.code == inventory_context.location.code

    assert report.summary.movement_count == 1
