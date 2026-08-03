"""CSV serialization for Inventory activity reports."""

import csv
from io import StringIO

from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.common import (
    format_local_datetime,
    safe_csv_text,
)
from apps.reports.selectors.inventory_activity import (
    InventoryActivityReport,
)


def _optional_safe_text(
    value: object | None,
) -> str:
    """Return safe text or an empty CSV cell."""

    if value in (None, ""):
        return ""

    return safe_csv_text(value)


def inventory_activity_csv_filename(
    *,
    date_range: ReportDateRange,
) -> str:
    """Return the Inventory report export filename."""

    return (
        "inventory-activity-"
        f"{date_range.start_date.isoformat()}"
        "-to-"
        f"{date_range.end_date.isoformat()}"
        ".csv"
    )


def build_inventory_activity_csv(
    *,
    report: InventoryActivityReport,
    date_range: ReportDateRange,
) -> str:
    """Serialize an Inventory activity report as CSV."""

    output = StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    summary = report.summary

    writer.writerow(["Inventory activity report"])
    writer.writerow(
        [
            "Report start",
            date_range.start_date.isoformat(),
        ]
    )
    writer.writerow(
        [
            "Report end",
            date_range.end_date.isoformat(),
        ]
    )

    writer.writerow([])
    writer.writerow(["Summary", "Value"])
    writer.writerow(
        [
            "Stock movements",
            summary.movement_count,
        ]
    )
    writer.writerow(
        [
            "Inventory items moved",
            summary.items_moved_count,
        ]
    )
    writer.writerow(
        [
            "Stock receipts",
            summary.receipt_count,
        ]
    )
    writer.writerow(
        [
            "Workshop issues",
            summary.issue_count,
        ]
    )
    writer.writerow(
        [
            "Workshop returns",
            summary.return_count,
        ]
    )
    writer.writerow(
        [
            "Positive adjustments",
            summary.positive_adjustment_count,
        ]
    )
    writer.writerow(
        [
            "Negative adjustments",
            summary.negative_adjustment_count,
        ]
    )
    writer.writerow(
        [
            "Current low-stock items",
            summary.low_stock_item_count,
        ]
    )

    writer.writerow([])
    writer.writerow(["Stock movements"])
    writer.writerow(
        [
            "Movement number",
            "SKU",
            "Product",
            "Location code",
            "Location",
            "Occurred",
            "Movement type",
            "Signed quantity",
            "Unit cost",
            "Currency",
            "Reference",
            "Notes",
            "Recorded by",
        ]
    )

    for movement in report.movements:
        inventory_item = movement.inventory_item

        writer.writerow(
            [
                safe_csv_text(movement.movement_number),
                safe_csv_text(inventory_item.product.sku),
                safe_csv_text(inventory_item.product.name),
                safe_csv_text(inventory_item.location.code),
                safe_csv_text(inventory_item.location.name),
                format_local_datetime(movement.occurred_at),
                safe_csv_text(movement.get_movement_type_display()),
                f"{movement.signed_quantity:.3f}",
                (f"{movement.unit_cost:.2f}" if movement.unit_cost is not None else ""),
                safe_csv_text(movement.currency),
                _optional_safe_text(movement.external_reference),
                _optional_safe_text(movement.notes),
                safe_csv_text(movement.created_by.username),
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "Current low-stock balances",
        ]
    )
    writer.writerow(
        [
            "Snapshot note",
            ("These are current balances, not historical balances for the period."),
        ]
    )
    writer.writerow(
        [
            "SKU",
            "Product",
            "Location code",
            "Location",
            "On hand",
            "Reserved",
            "Available",
            "Reorder level",
        ]
    )

    for balance in report.low_stock_balances:
        inventory_item = balance.inventory_item

        writer.writerow(
            [
                safe_csv_text(inventory_item.product.sku),
                safe_csv_text(inventory_item.product.name),
                safe_csv_text(inventory_item.location.code),
                safe_csv_text(inventory_item.location.name),
                f"{balance.on_hand_quantity:.3f}",
                f"{balance.reserved_quantity:.3f}",
                f"{balance.available_quantity:.3f}",
                (f"{inventory_item.reorder_level:.3f}"),
            ]
        )

    return "\ufeff" + output.getvalue()
