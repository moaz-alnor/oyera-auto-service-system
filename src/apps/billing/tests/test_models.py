"""Tests for billing database models."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
)
from apps.billing.models import (
    Invoice,
    InvoiceProductLine,
    InvoiceServiceLine,
    Payment,
)
from apps.billing.tests.conftest import BillingTestContext


def _draft_invoice(
    *,
    context: BillingTestContext,
) -> Invoice:
    """Build a valid unsaved draft invoice."""

    work_order = context.work_order
    job_card = context.job_card
    quotation = work_order.approved_quotation

    return Invoice(
        invoice_number="INV-TEST-001",
        work_order=work_order,
        status=InvoiceStatus.DRAFT,
        currency=quotation.currency,
        work_order_number_snapshot=(work_order.work_order_number),
        job_number_snapshot=job_card.job_number,
        quotation_number_snapshot=(quotation.quotation_number),
        customer_name_snapshot=(job_card.customer_name_snapshot),
        customer_phone_snapshot=(job_card.customer_phone_snapshot),
        customer_email_snapshot=(job_card.customer_email_snapshot),
        vehicle_registration_snapshot=(job_card.vehicle_registration_snapshot),
        vehicle_make_snapshot=(job_card.vehicle_make_snapshot),
        vehicle_model_snapshot=(job_card.vehicle_model_snapshot),
        vehicle_year_snapshot=(job_card.vehicle_year_snapshot),
        vehicle_color_snapshot=(job_card.vehicle_color_snapshot),
        service_subtotal=Decimal("80000.00"),
        product_subtotal=Decimal("0.00"),
        subtotal=Decimal("80000.00"),
        discount_percentage=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        taxable_amount=Decimal("80000.00"),
        tax_percentage=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total=Decimal("80000.00"),
        notes=" Billing test invoice. ",
        created_by=context.manager,
    )


@pytest.mark.django_db
def test_valid_draft_invoice_normalizes_values(
    billing_context: BillingTestContext,
) -> None:
    """Validate and normalize a draft invoice."""

    invoice = _draft_invoice(context=billing_context)

    invoice.currency = "ugx"
    invoice.vehicle_registration_snapshot = " ubb 101b "

    invoice.full_clean()

    assert invoice.currency == "UGX"
    assert invoice.vehicle_registration_snapshot == "UBB 101B"
    assert invoice.notes == "Billing test invoice."


@pytest.mark.django_db
def test_invoice_rejects_inconsistent_subtotal(
    billing_context: BillingTestContext,
) -> None:
    """Require invoice subtotal to match its components."""

    invoice = _draft_invoice(context=billing_context)
    invoice.subtotal = Decimal("70000.00")

    with pytest.raises(ValidationError) as exc_info:
        invoice.full_clean()

    assert "subtotal" in exc_info.value.message_dict


@pytest.mark.django_db
def test_issued_invoice_requires_issue_metadata(
    billing_context: BillingTestContext,
) -> None:
    """Require issue time and due date after draft state."""

    invoice = _draft_invoice(context=billing_context)
    invoice.status = InvoiceStatus.ISSUED

    with pytest.raises(ValidationError) as exc_info:
        invoice.full_clean()

    assert "issued_at" in exc_info.value.message_dict
    assert "due_date" in exc_info.value.message_dict


@pytest.mark.django_db
def test_payment_currency_must_match_invoice(
    billing_context: BillingTestContext,
) -> None:
    """Reject a payment in another currency."""

    invoice = _draft_invoice(context=billing_context)
    invoice.full_clean()
    invoice.save()

    payment = Payment(
        payment_number="PAY-TEST-001",
        invoice=invoice,
        amount=Decimal("20000.00"),
        currency="USD",
        payment_method=PaymentMethod.CASH,
        received_by=billing_context.cashier,
    )

    with pytest.raises(ValidationError) as exc_info:
        payment.full_clean()

    assert "currency" in exc_info.value.message_dict


def test_invoice_line_totals_are_calculated() -> None:
    """Calculate service and product line totals."""

    service_line = InvoiceServiceLine(
        quantity=Decimal("1.50"),
        unit_price=Decimal("80000.00"),
    )
    product_line = InvoiceProductLine(
        quantity=Decimal("2.500"),
        unit_price=Decimal("35000.00"),
    )

    assert service_line.line_total == Decimal("120000.00")
    assert product_line.line_total == Decimal("87500.00")
