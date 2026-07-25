"""Tests for payment recording and voiding workflows."""

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
    PaymentStatus,
)
from apps.billing.selectors import get_invoice_balance
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    create_invoice,
    issue_invoice,
)
from apps.billing.services.payments import (
    RecordPaymentCommand,
    VoidPaymentCommand,
    record_payment,
    void_payment,
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
    """Complete the billing fixture work order."""

    now = timezone.now()
    work_order = context.work_order
    task = work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for payment tests."
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


def _create_draft_invoice(
    *,
    context: BillingTestContext,
):
    """Create a draft invoice for payment tests."""

    _complete_work_order(context=context)

    return create_invoice(
        actor=context.manager,
        work_order_id=context.work_order.pk,
        command=CreateInvoiceCommand(),
    )


def _create_issued_invoice(
    *,
    context: BillingTestContext,
):
    """Create and issue an invoice for payment tests."""

    invoice = _create_draft_invoice(context=context)

    return issue_invoice(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(
            due_date=(timezone.localdate() + timedelta(days=14))
        ),
    )


@pytest.mark.django_db
def test_draft_invoice_rejects_payment(
    billing_context: BillingTestContext,
) -> None:
    """Require invoice issue before accepting payment."""

    invoice = _create_draft_invoice(context=billing_context)

    with pytest.raises(ValidationError) as exc_info:
        record_payment(
            actor=billing_context.cashier,
            invoice_id=invoice.pk,
            command=RecordPaymentCommand(
                amount=Decimal("20000.00"),
                payment_method=PaymentMethod.CASH,
            ),
        )

    assert "invoice" in exc_info.value.message_dict
    assert not invoice.payments.exists()


@pytest.mark.django_db
def test_cashier_records_partial_payment(
    billing_context: BillingTestContext,
) -> None:
    """Change an issued invoice to partially paid."""

    invoice = _create_issued_invoice(context=billing_context)

    payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
            notes=" First customer instalment. ",
        ),
    )

    invoice.refresh_from_db()
    balance = get_invoice_balance(invoice_id=invoice.pk)

    assert payment.payment_number == "PAY-000001-01"
    assert payment.status == PaymentStatus.POSTED
    assert payment.notes == "First customer instalment."
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert balance.paid_amount == Decimal("30000.00")
    assert balance.outstanding_amount == Decimal("50000.00")
    assert not balance.is_paid


@pytest.mark.django_db
def test_final_payment_marks_invoice_paid(
    billing_context: BillingTestContext,
) -> None:
    """Mark the invoice paid when its balance reaches zero."""

    invoice = _create_issued_invoice(context=billing_context)

    record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.MOBILE_MONEY,
        ),
    )

    final_payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("50000.00"),
            payment_method=PaymentMethod.CARD,
        ),
    )

    invoice.refresh_from_db()
    balance = get_invoice_balance(invoice_id=invoice.pk)

    assert final_payment.payment_number == "PAY-000001-02"
    assert invoice.status == InvoiceStatus.PAID
    assert balance.paid_amount == Decimal("80000.00")
    assert balance.outstanding_amount == Decimal("0.00")
    assert balance.is_paid


@pytest.mark.django_db
def test_payment_cannot_exceed_outstanding_balance(
    billing_context: BillingTestContext,
) -> None:
    """Reject customer overpayments."""

    invoice = _create_issued_invoice(context=billing_context)

    with pytest.raises(ValidationError) as exc_info:
        record_payment(
            actor=billing_context.cashier,
            invoice_id=invoice.pk,
            command=RecordPaymentCommand(
                amount=Decimal("80000.01"),
                payment_method=PaymentMethod.CASH,
            ),
        )

    assert "amount" in exc_info.value.message_dict
    assert not invoice.payments.exists()


@pytest.mark.django_db
def test_cashier_cannot_void_payment(
    billing_context: BillingTestContext,
) -> None:
    """Keep payment void authority away from cashiers."""

    invoice = _create_issued_invoice(context=billing_context)

    payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    with pytest.raises(PermissionDenied):
        void_payment(
            actor=billing_context.cashier,
            payment_id=payment.pk,
            command=VoidPaymentCommand(reason="Incorrect payment."),
        )


@pytest.mark.django_db
def test_manager_voids_payment_and_restores_balance(
    billing_context: BillingTestContext,
) -> None:
    """Void a payment and recalculate invoice status."""

    invoice = _create_issued_invoice(context=billing_context)

    payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.BANK_TRANSFER,
        ),
    )

    voided_payment = void_payment(
        actor=billing_context.manager,
        payment_id=payment.pk,
        command=VoidPaymentCommand(reason=" Duplicate bank entry. "),
    )

    invoice.refresh_from_db()
    balance = get_invoice_balance(invoice_id=invoice.pk)

    assert voided_payment.status == PaymentStatus.VOIDED
    assert voided_payment.voided_at is not None
    assert voided_payment.voided_by == billing_context.manager
    assert voided_payment.void_reason == "Duplicate bank entry."
    assert invoice.status == InvoiceStatus.ISSUED
    assert balance.paid_amount == Decimal("0.00")
    assert balance.outstanding_amount == Decimal("80000.00")
