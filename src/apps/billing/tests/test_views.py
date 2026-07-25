"""Tests for billing browser workflows."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
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

pytestmark = pytest.mark.django_db


def _complete_work_order(
    *,
    context: BillingTestContext,
) -> None:
    """Complete the fixture workshop work order."""

    now = timezone.now()
    task = context.work_order.tasks.get()

    task.status = WorkTaskStatus.COMPLETED
    task.actual_started_at = now
    task.actual_completed_at = now
    task.completion_notes = "Completed for billing browser tests."
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


def _create_draft_invoice(
    *,
    context: BillingTestContext,
) -> Invoice:
    """Create a draft invoice from completed work."""

    _complete_work_order(context=context)

    return create_invoice(
        actor=context.manager,
        work_order_id=context.work_order.pk,
        command=CreateInvoiceCommand(),
    )


def _create_issued_invoice(
    *,
    context: BillingTestContext,
) -> Invoice:
    """Create and issue an invoice."""

    invoice = _create_draft_invoice(context=context)

    return issue_invoice(
        actor=context.cashier,
        invoice_id=invoice.pk,
        command=IssueInvoiceCommand(
            due_date=(timezone.localdate() + timedelta(days=14))
        ),
    )


def test_anonymous_user_is_redirected_from_billing(
    client: Client,
) -> None:
    """Require authentication before viewing billing."""

    response = client.get(reverse("billing:list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


def test_cashier_can_view_billing_and_sidebar_link(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Display billing navigation to permitted employees."""

    client.force_login(billing_context.cashier)

    response = client.get(reverse("billing:list"))

    assert response.status_code == 200
    assert response.context["invoices"].count() == 0
    assert 'href="/billing/"' in response.content.decode()
    assert "Billing" in response.content.decode()


def test_manager_creates_invoice_from_browser(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Create a draft invoice through the browser form."""

    _complete_work_order(context=billing_context)
    client.force_login(billing_context.manager)

    response = client.post(
        reverse("billing:create"),
        {
            "work_order": billing_context.work_order.pk,
            "notes": " Browser-created invoice. ",
        },
    )

    invoice = Invoice.objects.get(work_order=billing_context.work_order)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "billing:detail",
        args=(invoice.pk,),
    )
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.notes == "Browser-created invoice."


def test_invoice_detail_displays_frozen_information(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Display invoice identity, customer, and total."""

    invoice = _create_draft_invoice(context=billing_context)
    client.force_login(billing_context.manager)

    response = client.get(
        reverse(
            "billing:detail",
            args=(invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert invoice.invoice_number in content
    assert "Billing Test Customer" in content
    assert "UBB 101B" in content
    assert "80000.00" in content


def test_cashier_issues_invoice_from_browser(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Issue a draft invoice through the browser."""

    invoice = _create_draft_invoice(context=billing_context)
    client.force_login(billing_context.cashier)

    due_date = timezone.localdate() + timedelta(days=14)

    response = client.post(
        reverse(
            "billing:issue",
            args=(invoice.pk,),
        ),
        {
            "due_date": due_date.isoformat(),
        },
    )

    invoice.refresh_from_db()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "billing:detail",
        args=(invoice.pk,),
    )
    assert invoice.status == InvoiceStatus.ISSUED
    assert invoice.due_date == due_date


def test_cashier_records_payment_from_browser(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Record a partial payment through the browser."""

    invoice = _create_issued_invoice(context=billing_context)
    client.force_login(billing_context.cashier)

    response = client.post(
        reverse(
            "billing:payment_create",
            args=(invoice.pk,),
        ),
        {
            "amount": "30000.00",
            "payment_method": PaymentMethod.CASH,
            "external_reference": "CASH-001",
            "notes": "Customer deposit.",
        },
    )

    invoice.refresh_from_db()
    payment = Payment.objects.get(invoice=invoice)

    assert response.status_code == 302
    assert payment.status == PaymentStatus.POSTED
    assert payment.amount == Decimal("30000.00")
    assert payment.external_reference == "CASH-001"
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID


def test_cashier_cannot_open_invoice_void_page(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Prevent cashiers from voiding invoices."""

    invoice = _create_issued_invoice(context=billing_context)
    client.force_login(billing_context.cashier)

    response = client.get(
        reverse(
            "billing:void",
            args=(invoice.pk,),
        )
    )

    assert response.status_code == 403


def test_manager_voids_invoice_from_browser(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Void an unpaid issued invoice through the browser."""

    invoice = _create_issued_invoice(context=billing_context)
    client.force_login(billing_context.manager)

    response = client.post(
        reverse(
            "billing:void",
            args=(invoice.pk,),
        ),
        {
            "reason": " Incorrect customer invoice. ",
        },
    )

    invoice.refresh_from_db()

    assert response.status_code == 302
    assert invoice.status == InvoiceStatus.VOIDED
    assert invoice.voided_by == billing_context.manager
    assert invoice.void_reason == "Incorrect customer invoice."


def test_manager_voids_payment_from_browser(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Void a posted payment and restore the balance."""

    invoice = _create_issued_invoice(context=billing_context)

    payment = record_payment(
        actor=billing_context.cashier,
        invoice_id=invoice.pk,
        command=RecordPaymentCommand(
            amount=Decimal("30000.00"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    client.force_login(billing_context.manager)

    response = client.post(
        reverse(
            "billing:payment_void",
            args=(payment.pk,),
        ),
        {
            "reason": " Duplicate receipt entry. ",
        },
    )

    payment.refresh_from_db()
    invoice.refresh_from_db()

    assert response.status_code == 302
    assert payment.status == PaymentStatus.VOIDED
    assert payment.void_reason == "Duplicate receipt entry."
    assert invoice.status == InvoiceStatus.ISSUED


def test_completed_work_order_links_to_invoice_workflow(
    client: Client,
    billing_context: BillingTestContext,
) -> None:
    """Switch the workshop shortcut after invoicing."""

    _complete_work_order(context=billing_context)
    client.force_login(billing_context.manager)

    work_order_url = reverse(
        "workshop:detail",
        args=(billing_context.work_order.pk,),
    )
    create_url = (
        f"{reverse('billing:create')}?work_order={billing_context.work_order.pk}"
    )

    response = client.get(work_order_url)
    content = response.content.decode()

    assert response.status_code == 200
    assert create_url in content
    assert "Create invoice" in content

    invoice = create_invoice(
        actor=billing_context.manager,
        work_order_id=billing_context.work_order.pk,
        command=CreateInvoiceCommand(),
    )

    response = client.get(work_order_url)
    content = response.content.decode()

    assert response.status_code == 200
    assert (
        reverse(
            "billing:detail",
            args=(invoice.pk,),
        )
        in content
    )
    assert "View invoice" in content
    assert "Create invoice" not in content
