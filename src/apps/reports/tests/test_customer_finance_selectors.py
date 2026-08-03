"""Tests for customer finance report selectors."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
)
from apps.billing.models import Invoice
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    create_invoice,
    issue_invoice,
)
from apps.billing.services.payments import (
    RecordPaymentCommand,
    record_payment,
)
from apps.billing.tests.conftest import (
    BillingTestContext,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.selectors.customer_finance import (
    CustomerFinanceSummary,
    get_customer_finance_report,
)
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskStatus,
)


def _complete_work_order(
    *,
    context: BillingTestContext,
) -> None:
    """Complete the billing fixture work order."""

    now = timezone.now()
    work_order = context.work_order
    task = work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for reporting tests."
    task.updated_by = context.manager
    task.full_clean()
    task.save()

    work_order.status = WorkOrderStatus.COMPLETED
    work_order.started_at = now
    work_order.completed_at = now
    work_order.updated_by = context.manager
    work_order.full_clean()
    work_order.save()


def _create_issued_invoice(
    *,
    context: BillingTestContext,
):
    """Create one issued customer invoice."""

    _complete_work_order(context=context)

    invoice = create_invoice(
        actor=context.manager,
        work_order_id=context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    return issue_invoice(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(
            due_date=(timezone.localdate() + timedelta(days=14))
        ),
    )


@pytest.mark.django_db
def test_customer_finance_report_calculates_totals(
    billing_context: BillingTestContext,
) -> None:
    """Calculate invoice, payment and balance totals."""

    invoice = _create_issued_invoice(context=billing_context)

    record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    today = timezone.localdate()

    report = get_customer_finance_report(
        date_range=ReportDateRange(
            start_date=today,
            end_date=today,
        )
    )

    assert report.summary == (
        CustomerFinanceSummary(
            currency="UGX",
            invoice_count=1,
            invoice_total=Decimal("80000.00"),
            posted_payment_total=(Decimal("30000.00")),
            outstanding_balance=(Decimal("50000.00")),
            paid_invoice_count=0,
            partially_paid_invoice_count=1,
            overdue_invoice_count=0,
            voided_invoice_count=0,
        )
    )

    assert len(report.invoices) == 1

    row = report.invoices[0]

    assert row.invoice.pk == invoice.pk
    assert row.paid_amount == Decimal("30000.00")
    assert row.outstanding_amount == (Decimal("50000.00"))
    assert not row.is_overdue


@pytest.mark.django_db
def test_customer_finance_report_marks_overdue_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Identify an open invoice past its due date."""

    invoice = _create_issued_invoice(context=billing_context)

    report_date = timezone.localdate()

    Invoice.objects.filter(pk=invoice.pk).update(
        issued_at=(timezone.now() - timedelta(days=5)),
        due_date=(report_date - timedelta(days=1)),
        status=InvoiceStatus.ISSUED,
    )

    report = get_customer_finance_report(
        date_range=ReportDateRange(
            start_date=(report_date - timedelta(days=7)),
            end_date=report_date,
        ),
        as_of_date=report_date,
    )

    assert report.summary.overdue_invoice_count == 1
    assert report.invoices[0].is_overdue


@pytest.mark.django_db
def test_customer_finance_report_uses_two_queries(
    billing_context: BillingTestContext,
    django_assert_num_queries,
) -> None:
    """Keep customer finance reporting query-bounded."""

    _create_issued_invoice(context=billing_context)

    today = timezone.localdate()

    with django_assert_num_queries(2):
        report = get_customer_finance_report(
            date_range=ReportDateRange(
                start_date=today,
                end_date=today,
            )
        )

    assert report.summary.invoice_count == 1


def test_customer_finance_report_rejects_currency() -> None:
    """Reject an invalid report currency code."""

    today = timezone.localdate()

    with pytest.raises(
        ValueError,
        match="three-letter code",
    ):
        get_customer_finance_report(
            date_range=ReportDateRange(
                start_date=today,
                end_date=today,
            ),
            currency="UGXA",
        )
