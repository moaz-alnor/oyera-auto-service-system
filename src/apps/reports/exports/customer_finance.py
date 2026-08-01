"""CSV serialization for customer finance reports."""

import csv
from datetime import datetime
from io import StringIO

from django.utils import timezone

from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.customer_finance import (
    CustomerFinanceReport,
)

_DANGEROUS_CELL_PREFIXES = (
    "=",
    "+",
    "-",
    "@",
    "\t",
    "\r",
)


def _safe_csv_text(value: object) -> str:
    """Protect text cells from spreadsheet formulas."""

    text = str(value)

    if text.startswith(_DANGEROUS_CELL_PREFIXES):
        return f"'{text}"

    return text


def _format_datetime(
    value: datetime | None,
) -> str:
    """Return a stable local datetime for CSV output."""

    if value is None:
        return ""

    if timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d %H:%M:%S")


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
                _safe_csv_text(invoice.invoice_number),
                _safe_csv_text(invoice.customer_name_snapshot),
                _safe_csv_text(invoice.vehicle_registration_snapshot),
                _format_datetime(invoice.issued_at),
                (invoice.due_date.isoformat() if invoice.due_date else ""),
                _safe_csv_text(status_display),
                "Yes" if row.is_overdue else "No",
                invoice.currency,
                f"{invoice.total:.2f}",
                f"{row.paid_amount:.2f}",
                (f"{row.outstanding_amount:.2f}"),
            ]
        )

    return "\ufeff" + output.getvalue()
