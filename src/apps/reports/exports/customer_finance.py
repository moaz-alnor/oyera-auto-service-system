"""CSV serialization for customer finance reports."""

import csv
from io import StringIO

from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.common import (
    format_local_datetime,
    safe_csv_text,
)
from apps.reports.selectors.customer_finance import (
    CustomerFinanceReport,
)


def customer_finance_csv_filename(
    *,
    date_range: ReportDateRange,
) -> str:
    """Return the customer-finance export filename."""

    return (
        "customer-finance-"
        f"{date_range.start_date.isoformat()}"
        "-to-"
        f"{date_range.end_date.isoformat()}"
        ".csv"
    )


def build_customer_finance_csv(
    *,
    report: CustomerFinanceReport,
    date_range: ReportDateRange,
) -> str:
    """Serialize a customer finance report as UTF-8 CSV."""

    output = StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    summary = report.summary

    writer.writerow(["Customer finance report"])
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
    writer.writerow(["Currency", summary.currency])

    writer.writerow([])
    writer.writerow(["Summary", "Value"])

    writer.writerow(
        [
            "Issued invoices",
            summary.invoice_count,
        ]
    )
    writer.writerow(
        [
            "Invoice total",
            f"{summary.invoice_total:.2f}",
        ]
    )
    writer.writerow(
        [
            "Posted payments",
            (f"{summary.posted_payment_total:.2f}"),
        ]
    )
    writer.writerow(
        [
            "Outstanding balance",
            (f"{summary.outstanding_balance:.2f}"),
        ]
    )
    writer.writerow(
        [
            "Paid invoices",
            summary.paid_invoice_count,
        ]
    )
    writer.writerow(
        [
            "Partially paid invoices",
            (summary.partially_paid_invoice_count),
        ]
    )
    writer.writerow(
        [
            "Overdue invoices",
            summary.overdue_invoice_count,
        ]
    )
    writer.writerow(
        [
            "Voided invoices",
            summary.voided_invoice_count,
        ]
    )

    writer.writerow([])
    writer.writerow(
        [
            "Invoice number",
            "Customer",
            "Vehicle",
            "Issued at",
            "Due date",
            "Status",
            "Overdue",
            "Currency",
            "Total",
            "Paid",
            "Outstanding",
        ]
    )

    for row in report.invoices:
        invoice = row.invoice

        status_display = invoice.get_status_display()

        writer.writerow(
            [
                safe_csv_text(invoice.invoice_number),
                safe_csv_text(invoice.customer_name_snapshot),
                safe_csv_text(invoice.vehicle_registration_snapshot),
                format_local_datetime(invoice.issued_at),
                (invoice.due_date.isoformat() if invoice.due_date else ""),
                safe_csv_text(status_display),
                "Yes" if row.is_overdue else "No",
                invoice.currency,
                f"{invoice.total:.2f}",
                f"{row.paid_amount:.2f}",
                (f"{row.outstanding_amount:.2f}"),
            ]
        )

    return "\ufeff" + output.getvalue()
