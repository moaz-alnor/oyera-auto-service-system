"""CSV serialization for Purchasing activity reports."""

import csv
from datetime import date
from io import StringIO

from apps.reports.date_ranges import ReportDateRange
from apps.reports.exports.common import (
    format_local_datetime,
    safe_csv_text,
)
from apps.reports.selectors.purchasing_activity import (
    PurchasingActivityReport,
)


def _optional_safe_text(
    value: object | None,
) -> str:
    """Return safe text or an empty CSV cell."""

    if value in (None, ""):
        return ""

    return safe_csv_text(value)


def _optional_datetime(
    value,
) -> str:
    """Format an optional local timestamp."""

    if value is None:
        return ""

    return format_local_datetime(value)


def _optional_username(
    employee,
) -> str:
    """Return an optional employee username."""

    if employee is None:
        return ""

    return safe_csv_text(employee.username)


def purchasing_activity_csv_filename(
    *,
    date_range: ReportDateRange,
) -> str:
    """Return the Purchasing export filename."""

    return (
        "purchasing-activity-"
        f"{date_range.start_date.isoformat()}"
        "-to-"
        f"{date_range.end_date.isoformat()}"
        ".csv"
    )


def build_purchasing_activity_csv(
    *,
    report: PurchasingActivityReport,
    date_range: ReportDateRange,
    as_of_date: date,
) -> str:
    """Serialize Purchasing activity as CSV."""

    output = StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    summary = report.summary

    writer.writerow(["Purchasing activity report"])
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
    writer.writerow(
        [
            "Liability snapshot date",
            as_of_date.isoformat(),
        ]
    )
    writer.writerow(
        [
            "Currency",
            summary.currency,
        ]
    )

    writer.writerow([])
    writer.writerow(["Period activity", "Value"])
    writer.writerow(
        [
            "Purchase orders created",
            summary.purchase_orders_created_count,
        ]
    )
    writer.writerow(
        [
            "Purchase orders submitted",
            summary.purchase_orders_submitted_count,
        ]
    )
    writer.writerow(
        [
            "Purchase orders approved",
            summary.purchase_orders_approved_count,
        ]
    )
    writer.writerow(
        [
            "Purchase orders cancelled",
            summary.purchase_orders_cancelled_count,
        ]
    )
    writer.writerow(
        [
            "Goods receipts posted",
            summary.goods_receipts_count,
        ]
    )
    writer.writerow(
        [
            "Supplier invoices posted",
            summary.supplier_invoices_posted_count,
        ]
    )
    writer.writerow(
        [
            "Supplier invoices voided",
            summary.supplier_invoices_voided_count,
        ]
    )
    writer.writerow(
        [
            "Supplier payments posted",
            summary.supplier_payments_posted_count,
        ]
    )
    writer.writerow(
        [
            "Supplier payments voided",
            summary.supplier_payments_voided_count,
        ]
    )
    writer.writerow(
        [
            "Supplier payment total",
            f"{summary.supplier_payment_total:.2f}",
        ]
    )

    writer.writerow([])
    writer.writerow(["Current liability", "Value"])
    writer.writerow(
        [
            "Open supplier invoices",
            summary.current_open_invoice_count,
        ]
    )
    writer.writerow(
        [
            "Outstanding supplier liability",
            (f"{summary.current_outstanding_liability:.2f}"),
        ]
    )
    writer.writerow(
        [
            "Overdue supplier invoices",
            summary.current_overdue_invoice_count,
        ]
    )

    writer.writerow([])
    writer.writerow(["Purchase orders"])
    writer.writerow(
        [
            "Purchase order",
            "Supplier number",
            "Supplier",
            "Status",
            "Currency",
            "Supplier reference",
            "Created",
            "Created by",
            "Submitted",
            "Submitted by",
            "Approved",
            "Approved by",
            "Cancelled",
            "Cancelled by",
            "Cancellation reason",
        ]
    )

    for purchase_order in report.purchase_orders:
        writer.writerow(
            [
                safe_csv_text(purchase_order.purchase_order_number),
                safe_csv_text(purchase_order.supplier_number_snapshot),
                safe_csv_text(purchase_order.supplier_name_snapshot),
                safe_csv_text(purchase_order.get_status_display()),
                safe_csv_text(purchase_order.currency),
                _optional_safe_text(purchase_order.supplier_reference),
                format_local_datetime(purchase_order.created_at),
                _optional_username(purchase_order.created_by),
                _optional_datetime(purchase_order.submitted_at),
                _optional_username(purchase_order.submitted_by),
                _optional_datetime(purchase_order.approved_at),
                _optional_username(purchase_order.approved_by),
                _optional_datetime(purchase_order.cancelled_at),
                _optional_username(purchase_order.cancelled_by),
                _optional_safe_text(purchase_order.cancellation_reason),
            ]
        )

    writer.writerow([])
    writer.writerow(["Goods receipts"])
    writer.writerow(
        [
            "Goods receipt",
            "Purchase order",
            "Supplier number",
            "Supplier",
            "Received",
            "Delivery reference",
            "Received by",
            "Notes",
        ]
    )

    for goods_receipt in report.goods_receipts:
        writer.writerow(
            [
                safe_csv_text(goods_receipt.goods_receipt_number),
                safe_csv_text(goods_receipt.purchase_order_number_snapshot),
                safe_csv_text(goods_receipt.supplier_number_snapshot),
                safe_csv_text(goods_receipt.supplier_name_snapshot),
                format_local_datetime(goods_receipt.received_at),
                _optional_safe_text(goods_receipt.supplier_delivery_reference),
                safe_csv_text(goods_receipt.received_by.username),
                _optional_safe_text(goods_receipt.notes),
            ]
        )

    writer.writerow([])
    writer.writerow(["Supplier invoices"])
    writer.writerow(
        [
            "Supplier invoice",
            "Supplier reference",
            "Supplier number",
            "Supplier",
            "Purchase order",
            "Invoice date",
            "Due date",
            "Status",
            "Currency",
            "Total",
            "Posted",
            "Posted by",
            "Voided",
            "Voided by",
            "Void reason",
            "Notes",
        ]
    )

    for supplier_invoice in report.supplier_invoices:
        writer.writerow(
            [
                safe_csv_text(supplier_invoice.supplier_invoice_number),
                safe_csv_text(supplier_invoice.supplier_reference),
                safe_csv_text(supplier_invoice.supplier_number_snapshot),
                safe_csv_text(supplier_invoice.supplier_name_snapshot),
                safe_csv_text(supplier_invoice.purchase_order_number_snapshot),
                supplier_invoice.invoice_date.isoformat(),
                supplier_invoice.due_date.isoformat(),
                safe_csv_text(supplier_invoice.get_status_display()),
                safe_csv_text(supplier_invoice.currency),
                f"{supplier_invoice.total:.2f}",
                _optional_datetime(supplier_invoice.posted_at),
                _optional_username(supplier_invoice.posted_by),
                _optional_datetime(supplier_invoice.voided_at),
                _optional_username(supplier_invoice.voided_by),
                _optional_safe_text(supplier_invoice.void_reason),
                _optional_safe_text(supplier_invoice.notes),
            ]
        )

    writer.writerow([])
    writer.writerow(["Supplier payments"])
    writer.writerow(
        [
            "Payment",
            "Supplier invoice",
            "Supplier",
            "Paid",
            "Amount",
            "Currency",
            "Method",
            "Status",
            "External reference",
            "Recorded by",
            "Voided",
            "Voided by",
            "Void reason",
            "Notes",
        ]
    )

    for payment in report.supplier_payments:
        writer.writerow(
            [
                safe_csv_text(payment.payment_number),
                safe_csv_text(payment.supplier_invoice.supplier_invoice_number),
                safe_csv_text(payment.supplier_invoice.supplier_name_snapshot),
                format_local_datetime(payment.paid_at),
                f"{payment.amount:.2f}",
                safe_csv_text(payment.currency),
                safe_csv_text(payment.get_method_display()),
                safe_csv_text(payment.get_status_display()),
                _optional_safe_text(payment.external_reference),
                safe_csv_text(payment.recorded_by.username),
                _optional_datetime(payment.voided_at),
                _optional_username(payment.voided_by),
                _optional_safe_text(payment.void_reason),
                _optional_safe_text(payment.notes),
            ]
        )

    writer.writerow([])
    writer.writerow(["Current open supplier invoices"])
    writer.writerow(
        [
            "Snapshot note",
            ("These are current liabilities, not historical balances for the period."),
        ]
    )
    writer.writerow(
        [
            "Supplier invoice",
            "Supplier",
            "Purchase order",
            "Due date",
            "Status",
            "Currency",
            "Total",
            "Paid",
            "Outstanding",
            "Overdue",
        ]
    )

    for supplier_invoice in report.open_supplier_invoices:
        writer.writerow(
            [
                safe_csv_text(supplier_invoice.supplier_invoice_number),
                safe_csv_text(supplier_invoice.supplier_name_snapshot),
                safe_csv_text(supplier_invoice.purchase_order_number_snapshot),
                supplier_invoice.due_date.isoformat(),
                safe_csv_text(supplier_invoice.get_status_display()),
                safe_csv_text(supplier_invoice.currency),
                f"{supplier_invoice.total:.2f}",
                (f"{supplier_invoice.posted_payment_total:.2f}"),
                (f"{supplier_invoice.outstanding_amount:.2f}"),
                (
                    "Yes"
                    if (
                        supplier_invoice.due_date < as_of_date
                        and supplier_invoice.outstanding_amount > 0
                    )
                    else "No"
                ),
            ]
        )

    return "\ufeff" + output.getvalue()
