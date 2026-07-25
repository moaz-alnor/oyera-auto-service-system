"""Tests for billing interface forms."""

from datetime import timedelta
from typing import cast

import pytest
from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from apps.billing.forms import (
    InvoiceCreateForm,
    InvoiceIssueForm,
    InvoiceVoidForm,
    PaymentRecordForm,
    PaymentVoidForm,
)
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    create_invoice,
    issue_invoice,
)
from apps.billing.tests.conftest import BillingTestContext
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskStatus,
)
from apps.workshop.models import WorkOrder


def _work_order_queryset(
    form: InvoiceCreateForm,
) -> QuerySet[WorkOrder]:
    """Return the work-order field queryset."""

    field = form.fields["work_order"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )

    queryset = field.queryset

    assert queryset is not None

    return cast(
        QuerySet[WorkOrder],
        queryset,
    )


def _complete_work_order(
    *,
    context: BillingTestContext,
) -> None:
    """Complete the fixture work order."""

    now = timezone.now()
    task = context.work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for form tests."
    task.updated_by = context.manager
    task.full_clean()
    task.save()

    context.work_order.status = WorkOrderStatus.COMPLETED
    context.work_order.started_at = now
    context.work_order.completed_at = now
    context.work_order.updated_by = context.manager
    context.work_order.full_clean()
    context.work_order.save()

    context.work_order.refresh_from_db()


def _issued_invoice(
    *,
    context: BillingTestContext,
):
    """Create an issued invoice for form tests."""

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
def test_invoice_form_lists_completed_uninvoiced_orders(
    billing_context: BillingTestContext,
) -> None:
    """List only completed work orders without invoices."""

    form = InvoiceCreateForm()

    assert list(_work_order_queryset(form)) == []

    _complete_work_order(context=billing_context)

    form = InvoiceCreateForm()

    assert list(_work_order_queryset(form)) == [billing_context.work_order]

    create_invoice(
        actor=billing_context.manager,
        work_order_id=billing_context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    form = InvoiceCreateForm()

    assert list(_work_order_queryset(form)) == []


def test_invoice_issue_form_rejects_past_due_date() -> None:
    """Reject an issue date before today."""

    form = InvoiceIssueForm(
        data={
            "due_date": (timezone.localdate() - timedelta(days=1)),
        }
    )

    assert not form.is_valid()
    assert "due_date" in form.errors


def test_void_forms_normalize_reasons() -> None:
    """Normalize invoice and payment void reasons."""

    invoice_form = InvoiceVoidForm(
        data={
            "reason": " Incorrect invoice. ",
        }
    )
    payment_form = PaymentVoidForm(
        data={
            "reason": " Duplicate payment. ",
        }
    )

    assert invoice_form.is_valid()
    assert payment_form.is_valid()
    assert invoice_form.cleaned_data["reason"] == "Incorrect invoice."
    assert payment_form.cleaned_data["reason"] == "Duplicate payment."


@pytest.mark.django_db
def test_payment_form_uses_outstanding_balance(
    billing_context: BillingTestContext,
) -> None:
    """Reject payment above the invoice balance."""

    invoice = _issued_invoice(context=billing_context)

    valid_form = PaymentRecordForm(
        data={
            "amount": "30000.00",
            "payment_method": "CASH",
            "external_reference": " CASH-001 ",
            "notes": " First payment. ",
        },
        invoice=invoice,
    )

    assert valid_form.is_valid()
    assert valid_form.cleaned_data["external_reference"] == "CASH-001"
    assert valid_form.cleaned_data["notes"] == "First payment."

    excessive_form = PaymentRecordForm(
        data={
            "amount": "80000.01",
            "payment_method": "CASH",
        },
        invoice=invoice,
    )

    assert not excessive_form.is_valid()
    assert "amount" in excessive_form.errors


@pytest.mark.django_db
def test_payment_form_rejects_future_time(
    billing_context: BillingTestContext,
) -> None:
    """Reject a future payment timestamp."""

    invoice = _issued_invoice(context=billing_context)

    future_time = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

    form = PaymentRecordForm(
        data={
            "amount": "30000.00",
            "payment_method": "CARD",
            "paid_at": future_time,
        },
        invoice=invoice,
    )

    assert not form.is_valid()
    assert "paid_at" in form.errors
