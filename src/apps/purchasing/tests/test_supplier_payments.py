"""Tests for supplier-payment application services."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
)
from apps.purchasing.models import SupplierInvoice
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    create_supplier_invoice,
    post_supplier_invoice,
)
from apps.purchasing.services.supplier_payments import (
    RecordSupplierPaymentCommand,
    VoidSupplierPaymentCommand,
    record_supplier_payment,
    void_supplier_payment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    create_posted_receipt,
)


def _create_supplier_invoice(
    *,
    context: PurchasingTestContext,
    posted: bool = True,
) -> SupplierInvoice:
    """Create one supplier invoice for payment tests."""

    receipt_context = create_posted_receipt(context=context)
    invoice_date = timezone.localdate()

    supplier_invoice = create_supplier_invoice(
        actor=context.manager,
        command=CreateSupplierInvoiceCommand(
            purchase_order_id=(receipt_context.purchase_order.pk),
            supplier_reference="SUP-PAYMENT-001",
            invoice_date=invoice_date,
            due_date=(invoice_date + timedelta(days=30)),
            lines=(
                SupplierInvoiceLineCommand(
                    goods_receipt_line_id=(receipt_context.goods_receipt_line.pk),
                    quantity_invoiced=Decimal("4.000"),
                    unit_cost=Decimal("25000.00"),
                ),
            ),
            notes="Supplier-payment service test.",
        ),
    )

    if not posted:
        return supplier_invoice

    return post_supplier_invoice(
        actor=context.manager,
        supplier_invoice_id=supplier_invoice.pk,
    )


@pytest.mark.django_db
def test_cashier_records_partial_supplier_payment(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Record a partial payment and update the invoice."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    payment = record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("40000.00"),
            method=(SupplierPaymentMethod.BANK_TRANSFER),
            external_reference="BANK-REF-001",
            notes="First supplier instalment.",
        ),
    )

    supplier_invoice.refresh_from_db()

    assert payment.payment_number == (f"SPAY-{supplier_invoice.pk:06d}-01")
    assert payment.amount == Decimal("40000.00")
    assert payment.currency == "UGX"
    assert payment.status == SupplierPaymentStatus.POSTED
    assert supplier_invoice.status == (SupplierInvoiceStatus.PARTIALLY_PAID)
    assert supplier_invoice.balance.paid_amount == (Decimal("40000.00"))
    assert supplier_invoice.balance.outstanding_amount == Decimal("60000.00")


@pytest.mark.django_db
def test_second_payment_completes_supplier_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Move the invoice to paid after full settlement."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("40000.00"),
            method=SupplierPaymentMethod.CASH,
        ),
    )

    payment = record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("60000.00"),
            method=(SupplierPaymentMethod.BANK_TRANSFER),
            external_reference="BANK-REF-002",
        ),
    )

    supplier_invoice.refresh_from_db()

    assert payment.payment_number == (f"SPAY-{supplier_invoice.pk:06d}-02")
    assert supplier_invoice.status == (SupplierInvoiceStatus.PAID)
    assert supplier_invoice.balance.paid_amount == (Decimal("100000.00"))
    assert supplier_invoice.balance.outstanding_amount == Decimal("0.00")
    assert supplier_invoice.balance.is_paid


@pytest.mark.django_db
def test_supplier_payment_cannot_exceed_balance(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject supplier overpayment."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    with pytest.raises(ValidationError) as exc_info:
        record_supplier_payment(
            actor=purchasing_context.cashier,
            supplier_invoice_id=(supplier_invoice.pk),
            command=RecordSupplierPaymentCommand(
                amount=Decimal("100000.01"),
                method=SupplierPaymentMethod.CASH,
            ),
        )

    assert "amount" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_payment_must_be_positive(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a zero supplier payment."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    with pytest.raises(ValidationError) as exc_info:
        record_supplier_payment(
            actor=purchasing_context.cashier,
            supplier_invoice_id=(supplier_invoice.pk),
            command=RecordSupplierPaymentCommand(
                amount=Decimal("0.00"),
                method=SupplierPaymentMethod.CASH,
            ),
        )

    assert "amount" in exc_info.value.message_dict


@pytest.mark.django_db
def test_technician_cannot_record_supplier_payment(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep supplier payments outside technician duties."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    with pytest.raises(PermissionDenied):
        record_supplier_payment(
            actor=purchasing_context.technician,
            supplier_invoice_id=(supplier_invoice.pk),
            command=RecordSupplierPaymentCommand(
                amount=Decimal("10000.00"),
                method=SupplierPaymentMethod.CASH,
            ),
        )


@pytest.mark.django_db
def test_draft_supplier_invoice_cannot_be_paid(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow payments only after invoice posting."""

    supplier_invoice = _create_supplier_invoice(
        context=purchasing_context,
        posted=False,
    )

    with pytest.raises(ValidationError) as exc_info:
        record_supplier_payment(
            actor=purchasing_context.cashier,
            supplier_invoice_id=(supplier_invoice.pk),
            command=RecordSupplierPaymentCommand(
                amount=Decimal("10000.00"),
                method=SupplierPaymentMethod.CASH,
            ),
        )

    assert "supplier_invoice" in exc_info.value.message_dict


@pytest.mark.django_db
def test_manager_voids_supplier_payment(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Void a payment and restore the invoice balance."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    payment = record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("40000.00"),
            method=(SupplierPaymentMethod.BANK_TRANSFER),
        ),
    )

    voided_payment = void_supplier_payment(
        actor=purchasing_context.manager,
        payment_id=payment.pk,
        command=VoidSupplierPaymentCommand(reason="Duplicate supplier payment."),
    )

    supplier_invoice.refresh_from_db()

    assert voided_payment.status == (SupplierPaymentStatus.VOIDED)
    assert voided_payment.voided_at is not None
    assert voided_payment.voided_by == purchasing_context.manager
    assert voided_payment.void_reason == ("Duplicate supplier payment.")
    assert supplier_invoice.status == (SupplierInvoiceStatus.POSTED)
    assert supplier_invoice.balance.paid_amount == (Decimal("0.00"))
    assert supplier_invoice.balance.outstanding_amount == Decimal("100000.00")


@pytest.mark.django_db
def test_cashier_cannot_void_supplier_payment(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep payment reversal under management control."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    payment = record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("10000.00"),
            method=SupplierPaymentMethod.CASH,
        ),
    )

    with pytest.raises(PermissionDenied):
        void_supplier_payment(
            actor=purchasing_context.cashier,
            payment_id=payment.pk,
            command=VoidSupplierPaymentCommand(reason="Cashier reversal attempt."),
        )


@pytest.mark.django_db
def test_supplier_payment_void_requires_reason(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require audit evidence for payment reversal."""

    supplier_invoice = _create_supplier_invoice(context=purchasing_context)

    payment = record_supplier_payment(
        actor=purchasing_context.cashier,
        supplier_invoice_id=supplier_invoice.pk,
        command=RecordSupplierPaymentCommand(
            amount=Decimal("10000.00"),
            method=SupplierPaymentMethod.CASH,
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        void_supplier_payment(
            actor=purchasing_context.manager,
            payment_id=payment.pk,
            command=VoidSupplierPaymentCommand(reason="   "),
        )

    assert "reason" in exc_info.value.message_dict
