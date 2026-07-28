"""Tests for supplier-invoice application services."""

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
from apps.purchasing.models import (
    SupplierPayment,
)
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    VoidSupplierInvoiceCommand,
    create_supplier_invoice,
    post_supplier_invoice,
    void_supplier_invoice,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    PostedReceiptContext,
    create_posted_receipt,
)


def _create_command(
    *,
    receipt_context: PostedReceiptContext,
    supplier_reference: str = "SUP-INV-001",
    quantity: Decimal = Decimal("4.000"),
    unit_cost: Decimal = Decimal("25000.00"),
) -> CreateSupplierInvoiceCommand:
    """Return a valid supplier-invoice command."""

    invoice_date = timezone.localdate()

    return CreateSupplierInvoiceCommand(
        purchase_order_id=(receipt_context.purchase_order.pk),
        supplier_reference=supplier_reference,
        invoice_date=invoice_date,
        due_date=invoice_date + timedelta(days=30),
        lines=(
            SupplierInvoiceLineCommand(
                goods_receipt_line_id=(receipt_context.goods_receipt_line.pk),
                quantity_invoiced=quantity,
                unit_cost=unit_cost,
            ),
        ),
        notes="Supplier invoice service test.",
    )


@pytest.mark.django_db
def test_manager_creates_matched_supplier_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Create a draft invoice from received goods."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    supplier_invoice = create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(receipt_context=receipt_context),
    )

    supplier_invoice_line = supplier_invoice.lines.get()

    assert supplier_invoice.supplier_invoice_number == (
        f"SINV-{supplier_invoice.pk:06d}"
    )
    assert supplier_invoice.status == SupplierInvoiceStatus.DRAFT
    assert supplier_invoice.total == Decimal("100000.00")
    assert supplier_invoice.purchase_order == receipt_context.purchase_order
    assert (
        supplier_invoice_line.goods_receipt_line == receipt_context.goods_receipt_line
    )
    assert supplier_invoice_line.quantity_invoiced == Decimal("4.000")
    assert supplier_invoice_line.unit_cost == Decimal("25000.00")


@pytest.mark.django_db
def test_technician_cannot_create_supplier_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep accounts payable outside technician duties."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    with pytest.raises(PermissionDenied):
        create_supplier_invoice(
            actor=purchasing_context.technician,
            command=_create_command(receipt_context=receipt_context),
        )


@pytest.mark.django_db
def test_duplicate_supplier_reference_is_rejected(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent duplicate supplier invoice references."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(
            receipt_context=receipt_context,
            supplier_reference="SUP-DUP-001",
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        create_supplier_invoice(
            actor=purchasing_context.manager,
            command=_create_command(
                receipt_context=receipt_context,
                supplier_reference=" sup-dup-001 ",
                quantity=Decimal("0.500"),
            ),
        )

    assert "supplier_reference" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_invoice_cost_must_match_receipt(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject an invoice with a changed supplier cost."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    with pytest.raises(ValidationError) as exc_info:
        create_supplier_invoice(
            actor=purchasing_context.manager,
            command=_create_command(
                receipt_context=receipt_context,
                unit_cost=Decimal("26000.00"),
            ),
        )

    assert "unit_cost" in exc_info.value.message_dict


@pytest.mark.django_db
def test_cumulative_invoices_cannot_exceed_receipt(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent invoicing received quantities twice."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(
            receipt_context=receipt_context,
            supplier_reference="SUP-QTY-001",
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        create_supplier_invoice(
            actor=purchasing_context.manager,
            command=_create_command(
                receipt_context=receipt_context,
                supplier_reference="SUP-QTY-002",
                quantity=Decimal("0.001"),
            ),
        )

    assert "quantity_invoiced" in exc_info.value.message_dict


@pytest.mark.django_db
def test_manager_posts_matched_supplier_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Post a correctly matched draft invoice."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(receipt_context=receipt_context),
    )

    posted_invoice = post_supplier_invoice(
        actor=purchasing_context.manager,
        supplier_invoice_id=supplier_invoice.pk,
    )

    assert posted_invoice.status == SupplierInvoiceStatus.POSTED
    assert posted_invoice.posted_at is not None
    assert posted_invoice.posted_by == purchasing_context.manager


@pytest.mark.django_db
def test_manager_voids_unpaid_supplier_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Void an unpaid posted supplier invoice."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(receipt_context=receipt_context),
    )
    supplier_invoice = post_supplier_invoice(
        actor=purchasing_context.manager,
        supplier_invoice_id=supplier_invoice.pk,
    )

    voided_invoice = void_supplier_invoice(
        actor=purchasing_context.manager,
        supplier_invoice_id=supplier_invoice.pk,
        command=VoidSupplierInvoiceCommand(reason="Supplier cancelled the invoice."),
    )

    assert voided_invoice.status == SupplierInvoiceStatus.VOIDED
    assert voided_invoice.voided_at is not None
    assert voided_invoice.voided_by == purchasing_context.manager
    assert voided_invoice.void_reason == ("Supplier cancelled the invoice.")


@pytest.mark.django_db
def test_supplier_invoice_with_payment_cannot_be_voided(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require payment reversal before invoice voiding."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = create_supplier_invoice(
        actor=purchasing_context.manager,
        command=_create_command(receipt_context=receipt_context),
    )
    supplier_invoice = post_supplier_invoice(
        actor=purchasing_context.manager,
        supplier_invoice_id=supplier_invoice.pk,
    )

    payment = SupplierPayment(
        payment_number="SPAY-LOCK-001",
        supplier_invoice=supplier_invoice,
        amount=Decimal("10000.00"),
        currency=supplier_invoice.currency,
        method=SupplierPaymentMethod.BANK_TRANSFER,
        status=SupplierPaymentStatus.POSTED,
        recorded_by=purchasing_context.cashier,
    )
    payment.full_clean()
    payment.save()

    with pytest.raises(ValidationError) as exc_info:
        void_supplier_invoice(
            actor=purchasing_context.manager,
            supplier_invoice_id=(supplier_invoice.pk),
            command=VoidSupplierInvoiceCommand(reason="Attempting invalid void."),
        )

    assert "supplier_invoice" in exc_info.value.message_dict
