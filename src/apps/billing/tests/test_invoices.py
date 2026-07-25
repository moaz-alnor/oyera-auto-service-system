"""Tests for invoice creation and issue workflows."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
)
from apps.billing.models import Invoice
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    VoidInvoiceCommand,
    create_invoice,
    issue_invoice,
    void_invoice,
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


def _complete_work_order(
    *,
    context: BillingTestContext,
) -> None:
    """Move the fixture work order to completed state."""

    now = timezone.now()
    work_order = context.work_order
    task = work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for billing test."
    task.updated_by = context.manager
    task.full_clean()
    task.save()

    work_order.status = WorkOrderStatus.COMPLETED
    work_order.started_at = now
    work_order.completed_at = now
    work_order.updated_by = context.manager
    work_order.full_clean()
    work_order.save()

    context.work_order.refresh_from_db()


def _create_issued_invoice(
    *,
    context: BillingTestContext,
):
    """Create and issue an invoice for voiding tests."""

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
def test_incomplete_work_order_cannot_be_invoiced(
    billing_context: BillingTestContext,
) -> None:
    """Reject invoicing before workshop completion."""

    with pytest.raises(ValidationError) as exc_info:
        create_invoice(
            actor=billing_context.manager,
            work_order_id=billing_context.work_order.pk,
            command=CreateInvoiceCommand(),
        )

    assert "work_order" in exc_info.value.message_dict
    assert not Invoice.objects.exists()


@pytest.mark.django_db
def test_completed_work_order_creates_draft_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Create frozen invoice and service snapshots."""

    _complete_work_order(context=billing_context)

    invoice = create_invoice(
        actor=billing_context.manager,
        work_order_id=billing_context.work_order.pk,
        command=CreateInvoiceCommand(notes=" Final customer invoice. "),
    )

    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.invoice_number == "INV-000001"
    assert invoice.currency == "UGX"
    assert invoice.service_subtotal == Decimal("80000.00")
    assert invoice.product_subtotal == Decimal("0.00")
    assert invoice.total == Decimal("80000.00")
    assert invoice.notes == "Final customer invoice."

    service_line = invoice.service_lines.get()

    assert service_line.service_code_snapshot == "BILL-OIL-SERVICE"
    assert service_line.quantity == Decimal("1.00")
    assert service_line.unit_price == Decimal("80000.00")
    assert service_line.line_total == Decimal("80000.00")


@pytest.mark.django_db
def test_work_order_cannot_receive_second_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Prevent duplicate invoices for one work order."""

    _complete_work_order(context=billing_context)

    create_invoice(
        actor=billing_context.manager,
        work_order_id=billing_context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    with pytest.raises(ValidationError) as exc_info:
        create_invoice(
            actor=billing_context.manager,
            work_order_id=billing_context.work_order.pk,
            command=CreateInvoiceCommand(),
        )

    assert "work_order" in exc_info.value.message_dict
    assert Invoice.objects.count() == 1


@pytest.mark.django_db
def test_cashier_issues_draft_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Allow a cashier to issue a prepared invoice."""

    _complete_work_order(context=billing_context)

    invoice = create_invoice(
        actor=billing_context.cashier,
        work_order_id=billing_context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    due_date = timezone.localdate() + timedelta(days=14)

    issued_invoice = issue_invoice(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(due_date=due_date),
    )

    assert issued_invoice.status == InvoiceStatus.ISSUED
    assert issued_invoice.issued_at is not None
    assert issued_invoice.due_date == due_date


@pytest.mark.django_db
def test_cashier_cannot_void_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Keep invoice-void authority away from cashiers."""

    invoice = _create_issued_invoice(context=billing_context)

    with pytest.raises(PermissionDenied):
        void_invoice(
            actor=billing_context.cashier,
            invoice_id=invoice.pk,
            command=VoidInvoiceCommand(reason="Incorrect invoice."),
        )


@pytest.mark.django_db
def test_manager_voids_unpaid_issued_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Preserve and void an unpaid issued invoice."""

    invoice = _create_issued_invoice(context=billing_context)

    voided_invoice = void_invoice(
        actor=billing_context.manager,
        invoice_id=invoice.pk,
        command=VoidInvoiceCommand(reason=" Customer job was cancelled. "),
    )

    assert voided_invoice.status == InvoiceStatus.VOIDED
    assert voided_invoice.voided_at is not None
    assert voided_invoice.voided_by == billing_context.manager
    assert voided_invoice.void_reason == "Customer job was cancelled."


@pytest.mark.django_db
def test_invoice_with_posted_payment_cannot_be_voided(
    billing_context: BillingTestContext,
) -> None:
    """Require payment voiding before invoice voiding."""

    invoice = _create_issued_invoice(context=billing_context)

    record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        void_invoice(
            actor=billing_context.manager,
            invoice_id=invoice.pk,
            command=VoidInvoiceCommand(reason="Incorrect invoice."),
        )

    assert "invoice" in exc_info.value.message_dict

    invoice.refresh_from_db()

    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
