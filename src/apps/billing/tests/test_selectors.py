"""Tests for read-only billing selectors."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
)
from apps.billing.selectors import (
    get_invoice_balance,
    get_invoice_detail,
    invoice_is_overdue,
    invoice_list_queryset,
    payment_list_queryset,
)
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
from apps.billing.tests.conftest import BillingTestContext
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskStatus,
)


def _create_issued_invoice(
    *,
    context: BillingTestContext,
):
    """Create a completed, issued invoice."""

    now = timezone.now()
    task = context.work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for selector tests."
    task.updated_by = context.manager
    task.full_clean()
    task.save()

    context.work_order.status = WorkOrderStatus.COMPLETED
    context.work_order.started_at = now
    context.work_order.completed_at = now
    context.work_order.updated_by = context.manager
    context.work_order.full_clean()
    context.work_order.save()

    invoice = create_invoice(
        actor=context.manager,
        work_order_id=context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    return issue_invoice(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(due_date=timezone.localdate()),
    )


@pytest.mark.django_db
def test_invoice_list_returns_created_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Return created invoices from the list selector."""

    invoice = _create_issued_invoice(context=billing_context)

    invoices = list(invoice_list_queryset())

    assert [item.pk for item in invoices] == [invoice.pk]
    assert invoices[0].work_order.pk == (billing_context.work_order.pk)


@pytest.mark.django_db
def test_invoice_detail_includes_lines_and_payments(
    billing_context: BillingTestContext,
) -> None:
    """Return invoice lines and payment history."""

    invoice = _create_issued_invoice(context=billing_context)

    payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    detailed_invoice = get_invoice_detail(invoice_id=invoice.pk)
    payments = list(payment_list_queryset(invoice_id=invoice.pk))

    assert detailed_invoice.service_lines.count() == 1
    assert detailed_invoice.product_lines.count() == 0
    assert detailed_invoice.payments.count() == 1
    assert payments == [payment]


@pytest.mark.django_db
def test_overdue_requires_an_outstanding_balance(
    billing_context: BillingTestContext,
) -> None:
    """Treat only unpaid past-due invoices as overdue."""

    invoice = _create_issued_invoice(context=billing_context)

    tomorrow = timezone.localdate() + timedelta(days=1)

    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice_is_overdue(
        invoice=invoice,
        on_date=tomorrow,
    )

    record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("80000.00"),
            payment_method=PaymentMethod.CARD,
        ),
    )

    invoice.refresh_from_db()
    balance = get_invoice_balance(invoice_id=invoice.pk)

    assert invoice.status == InvoiceStatus.PAID
    assert balance.outstanding_amount == Decimal("0.00")
    assert not invoice_is_overdue(
        invoice=invoice,
        on_date=tomorrow,
    )
