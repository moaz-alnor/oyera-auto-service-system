"""Read-only selectors for inventory activity reports."""

from dataclasses import dataclass
from datetime import (
    datetime,
    time,
    timedelta,
)

from django.utils import timezone

from apps.inventory.constants import (
    StockMovementType,
)
from apps.inventory.models import StockMovement
from apps.inventory.selectors import (
    InventoryBalance,
    get_low_stock_items,
)
from apps.reports.date_ranges import ReportDateRange


@dataclass(frozen=True, slots=True)
class InventoryActivitySummary:
    """Contain Inventory activity totals."""

    movement_count: int
    items_moved_count: int
    receipt_count: int
    issue_count: int
    return_count: int
    positive_adjustment_count: int
    negative_adjustment_count: int
    low_stock_item_count: int


@dataclass(frozen=True, slots=True)
class InventoryActivityReport:
    """Contain movement activity and current risks."""

    summary: InventoryActivitySummary
    movements: tuple[StockMovement, ...]
    low_stock_balances: tuple[
        InventoryBalance,
        ...,
    ]


def _local_date_bounds(
    *,
    date_range: ReportDateRange,
) -> tuple[datetime, datetime]:
    """Return inclusive-start and exclusive-end times."""

    current_timezone = timezone.get_current_timezone()

    start_at = timezone.make_aware(
        datetime.combine(
            date_range.start_date,
            time.min,
        ),
        current_timezone,
    )

    end_at = timezone.make_aware(
        datetime.combine(
            (date_range.end_date + timedelta(days=1)),
            time.min,
        ),
        current_timezone,
    )

    return start_at, end_at


def _movement_type_count(
    *,
    movements: tuple[StockMovement, ...],
    movement_type: StockMovementType,
) -> int:
    """Count movements of one ledger type."""

    return sum(movement.movement_type == movement_type for movement in movements)


def get_inventory_activity_report(
    *,
    date_range: ReportDateRange,
) -> InventoryActivityReport:
    """Return Inventory activity and current stock risks."""

    start_at, end_at = _local_date_bounds(date_range=date_range)

    movements = tuple(
        StockMovement.objects.filter(
            occurred_at__gte=start_at,
            occurred_at__lt=end_at,
        )
        .select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__product__category",
            "inventory_item__location",
            "reservation",
            "source_movement",
            "created_by",
        )
        .order_by(
            "-occurred_at",
            "-pk",
        )
    )

    low_stock_balances = tuple(get_low_stock_items())

    summary = InventoryActivitySummary(
        movement_count=len(movements),
        items_moved_count=len({movement.inventory_item_id for movement in movements}),
        receipt_count=_movement_type_count(
            movements=movements,
            movement_type=(StockMovementType.RECEIPT),
        ),
        issue_count=_movement_type_count(
            movements=movements,
            movement_type=(StockMovementType.ISSUE),
        ),
        return_count=_movement_type_count(
            movements=movements,
            movement_type=(StockMovementType.RETURN),
        ),
        positive_adjustment_count=(
            _movement_type_count(
                movements=movements,
                movement_type=(StockMovementType.ADJUSTMENT_IN),
            )
        ),
        negative_adjustment_count=(
            _movement_type_count(
                movements=movements,
                movement_type=(StockMovementType.ADJUSTMENT_OUT),
            )
        ),
        low_stock_item_count=len(low_stock_balances),
    )

    return InventoryActivityReport(
        summary=summary,
        movements=movements,
        low_stock_balances=(low_stock_balances),
    )
