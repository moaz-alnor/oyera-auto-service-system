"""CSV serialization for workshop operations reports."""

import csv
from io import StringIO

from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.common import (
    format_local_datetime,
    safe_csv_text,
)
from apps.reports.selectors.workshop_operations import (
    WorkshopOperationsReport,
)


def workshop_operations_csv_filename(
    *,
    date_range: ReportDateRange,
) -> str:
    """Return the workshop report export filename."""

    return (
        "workshop-operations-"
        f"{date_range.start_date.isoformat()}"
        "-to-"
        f"{date_range.end_date.isoformat()}"
        ".csv"
    )


def build_workshop_operations_csv(
    *,
    report: WorkshopOperationsReport,
    date_range: ReportDateRange,
) -> str:
    """Serialize a workshop report as UTF-8 CSV."""

    output = StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    summary = report.summary

    writer.writerow(["Workshop operations report"])
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
            "Vehicles received",
            summary.vehicles_received_count,
        ]
    )
    writer.writerow(
        [
            "Urgent job cards",
            summary.urgent_job_count,
        ]
    )
    writer.writerow(
        [
            "Cancelled job cards",
            summary.cancelled_job_count,
        ]
    )
    writer.writerow(
        [
            "Work orders created",
            summary.work_orders_created_count,
        ]
    )
    writer.writerow(
        [
            "Work orders started",
            summary.work_orders_started_count,
        ]
    )
    writer.writerow(
        [
            "Work orders completed",
            summary.work_orders_completed_count,
        ]
    )
    writer.writerow(
        [
            "Vehicles released",
            summary.vehicles_released_count,
        ]
    )
    writer.writerow(
        [
            "Payment-override releases",
            summary.payment_override_release_count,
        ]
    )

    writer.writerow([])
    writer.writerow(["Vehicle intake"])
    writer.writerow(
        [
            "Job number",
            "Customer",
            "Vehicle",
            "Arrival",
            "Priority",
            "Status",
        ]
    )

    for job_card in report.job_cards:
        writer.writerow(
            [
                safe_csv_text(job_card.job_number),
                safe_csv_text(job_card.customer_name_snapshot),
                safe_csv_text(job_card.vehicle_registration_snapshot),
                format_local_datetime(job_card.arrival_at),
                safe_csv_text(job_card.get_priority_display()),
                safe_csv_text(job_card.get_status_display()),
            ]
        )

    writer.writerow([])
    writer.writerow(["Work-order activity"])
    writer.writerow(
        [
            "Work order",
            "Job number",
            "Vehicle",
            "Created",
            "Started",
            "Completed",
            "Status",
        ]
    )

    for work_order in report.work_orders:
        writer.writerow(
            [
                safe_csv_text(work_order.work_order_number),
                safe_csv_text(work_order.job_card.job_number),
                safe_csv_text(work_order.job_card.vehicle_registration_snapshot),
                format_local_datetime(work_order.created_at),
                format_local_datetime(work_order.started_at),
                format_local_datetime(work_order.completed_at),
                safe_csv_text(work_order.get_status_display()),
            ]
        )

    writer.writerow([])
    writer.writerow(["Vehicle releases"])
    writer.writerow(
        [
            "Release number",
            "Job number",
            "Vehicle",
            "Released",
            "Received by",
            "Invoice",
            "Currency",
            "Outstanding",
            "Payment override",
        ]
    )

    for release in report.releases:
        writer.writerow(
            [
                safe_csv_text(release.release_number),
                safe_csv_text(release.job_card.job_number),
                safe_csv_text(release.job_card.vehicle_registration_snapshot),
                format_local_datetime(release.released_at),
                safe_csv_text(release.received_by_name),
                safe_csv_text(release.invoice_number_snapshot),
                safe_csv_text(release.invoice_currency_snapshot),
                (f"{release.outstanding_amount_snapshot:.2f}"),
                ("Yes" if release.payment_override else "No"),
            ]
        )

    return "\ufeff" + output.getvalue()
