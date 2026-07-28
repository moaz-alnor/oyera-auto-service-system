"""Tests for supplier invoice and payment models."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.purchasing.calculations import (
    calculate_line_total,
)
from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierPayment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    PostedReceiptContext,
    create_posted_receipt,
)


def _draft_supplier_invoice(
    *,
    context: PurchasingTestContext,
    receipt_context: PostedReceiptContext,
) -> SupplierInvoice:
    """Build one valid unsaved supplier invoice."""

    purchase_order = receipt_context.purchase_order
    invoice_date = timezone.localdate()

    return SupplierInvoice(
        supplier_invoice_number="SINV-TEST-001",
        supplier_reference=" supplier-ref-001 ",
        normalized_supplier_reference="",
        supplier=purchase_order.supplier,
        purchase_order=purchase_order,
        purchase_order_number_snapshot=(purchase_order.purchase_order_number),
        supplier_number_snapshot=(purchase_order.supplier_number_snapshot),
        supplier_name_snapshot=(purchase_order.supplier_name_snapshot),
        status=SupplierInvoiceStatus.DRAFT,
        currency=purchase_order.currency.lower(),
        invoice_date=invoice_date,
        due_date=invoice_date + timedelta(days=30),
        line_subtotal=Decimal("100000.00"),
        tax_amount=Decimal("0.00"),
        other_charges=Decimal("0.00"),
        total=Decimal("100000.00"),
        notes=" Supplier invoice test. ",
        created_by=context.manager,
        updated_by=context.manager,
    )


def _save_draft_supplier_invoice(
    *,
    context: PurchasingTestContext,
    receipt_context: PostedReceiptContext,
) -> SupplierInvoice:
    """Validate and save one draft supplier invoice."""

    supplier_invoice = _draft_supplier_invoice(
        context=context,
        receipt_context=receipt_context,
    )
    supplier_invoice.full_clean()
    supplier_invoice.save()

    return supplier_invoice


def _save_posted_supplier_invoice(
    *,
    context: PurchasingTestContext,
    receipt_context: PostedReceiptContext,
) -> SupplierInvoice:
    """Validate and save one posted supplier invoice."""

    supplier_invoice = _draft_supplier_invoice(
        context=context,
        receipt_context=receipt_context,
    )
    supplier_invoice.status = SupplierInvoiceStatus.POSTED
    supplier_invoice.posted_at = timezone.now()
    supplier_invoice.posted_by = context.manager
    supplier_invoice.full_clean()
    supplier_invoice.save()

    return supplier_invoice


def _supplier_invoice_line(
    *,
    context: PurchasingTestContext,
    receipt_context: PostedReceiptContext,
    supplier_invoice: SupplierInvoice,
    quantity: Decimal = Decimal("4.000"),
) -> SupplierInvoiceLine:
    """Build one line matched to the posted receipt."""

    unit_cost = Decimal("25000.00")

    return SupplierInvoiceLine(
        supplier_invoice=supplier_invoice,
        purchase_order_line=(receipt_context.purchase_order_line),
        goods_receipt_line=(receipt_context.goods_receipt_line),
        product_sku_snapshot=(receipt_context.product.sku),
        product_name_snapshot=(receipt_context.product.name),
        unit_snapshot=(receipt_context.purchase_order_line.unit_snapshot),
        quantity_invoiced=quantity,
        unit_cost=unit_cost,
        line_total=calculate_line_total(
            quantity=quantity,
            unit_cost=unit_cost,
        ),
        created_by=context.manager,
    )


@pytest.mark.django_db
def test_valid_draft_supplier_invoice_normalises_values(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Normalise a valid supplier invoice."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )

    supplier_invoice.full_clean()

    assert supplier_invoice.currency == "UGX"
    assert supplier_invoice.supplier_reference == ("supplier-ref-001")
    assert supplier_invoice.normalized_supplier_reference == "supplier-ref-001"
    assert supplier_invoice.notes == ("Supplier invoice test.")


@pytest.mark.django_db
def test_supplier_invoice_rejects_early_due_date(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a due date before the invoice date."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )
    supplier_invoice.due_date = supplier_invoice.invoice_date - timedelta(days=1)

    with pytest.raises(ValidationError) as exc_info:
        supplier_invoice.full_clean()

    assert "due_date" in exc_info.value.message_dict


@pytest.mark.django_db
def test_posted_supplier_invoice_requires_metadata(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require employee and timestamp when posting."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )
    supplier_invoice.status = SupplierInvoiceStatus.POSTED

    with pytest.raises(ValidationError) as exc_info:
        supplier_invoice.full_clean()

    assert "posted_at" in exc_info.value.message_dict


@pytest.mark.django_db
def test_voided_supplier_invoice_requires_metadata(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require a complete audit trail when voiding."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )
    supplier_invoice.status = SupplierInvoiceStatus.VOIDED
    supplier_invoice.posted_at = timezone.now()
    supplier_invoice.posted_by = purchasing_context.manager

    with pytest.raises(ValidationError) as exc_info:
        supplier_invoice.full_clean()

    assert "void_reason" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_invoice_line_matches_receipt(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Accept an invoice line matching received goods."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _save_draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )
    supplier_invoice_line = _supplier_invoice_line(
        context=purchasing_context,
        receipt_context=receipt_context,
        supplier_invoice=supplier_invoice,
    )

    supplier_invoice_line.full_clean()

    assert supplier_invoice_line.line_total == Decimal("100000.00")


@pytest.mark.django_db
def test_supplier_invoice_line_cannot_exceed_receipt(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject invoiced quantity above received quantity."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _save_draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )
    supplier_invoice_line = _supplier_invoice_line(
        context=purchasing_context,
        receipt_context=receipt_context,
        supplier_invoice=supplier_invoice,
        quantity=Decimal("5.000"),
    )

    with pytest.raises(ValidationError) as exc_info:
        supplier_invoice_line.full_clean()

    assert "quantity_invoiced" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_payment_currency_matches_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject payment in another currency."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _save_posted_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )

    payment = SupplierPayment(
        payment_number="SPAY-TEST-001",
        supplier_invoice=supplier_invoice,
        amount=Decimal("40000.00"),
        currency="USD",
        method=SupplierPaymentMethod.BANK_TRANSFER,
        status=SupplierPaymentStatus.POSTED,
        recorded_by=purchasing_context.cashier,
    )

    with pytest.raises(ValidationError) as exc_info:
        payment.full_clean()

    assert "currency" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_payment_rejects_draft_invoice(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow payments only against posted invoices."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _save_draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )

    payment = SupplierPayment(
        payment_number="SPAY-TEST-001",
        supplier_invoice=supplier_invoice,
        amount=Decimal("40000.00"),
        currency=supplier_invoice.currency,
        method=SupplierPaymentMethod.CASH,
        status=SupplierPaymentStatus.POSTED,
        recorded_by=purchasing_context.cashier,
    )

    with pytest.raises(ValidationError) as exc_info:
        payment.full_clean()

    assert "supplier_invoice" in exc_info.value.message_dict


@pytest.mark.django_db
def test_supplier_invoice_balance_ignores_voided_payments(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Calculate balance from active payments only."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _save_posted_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )

    posted_payment = SupplierPayment(
        payment_number="SPAY-TEST-001",
        supplier_invoice=supplier_invoice,
        amount=Decimal("40000.00"),
        currency=supplier_invoice.currency,
        method=SupplierPaymentMethod.BANK_TRANSFER,
        status=SupplierPaymentStatus.POSTED,
        recorded_by=purchasing_context.cashier,
    )
    posted_payment.full_clean()
    posted_payment.save()

    voided_payment = SupplierPayment(
        payment_number="SPAY-TEST-002",
        supplier_invoice=supplier_invoice,
        amount=Decimal("10000.00"),
        currency=supplier_invoice.currency,
        method=SupplierPaymentMethod.CASH,
        status=SupplierPaymentStatus.VOIDED,
        recorded_by=purchasing_context.cashier,
        voided_at=timezone.now(),
        voided_by=purchasing_context.manager,
        void_reason="Duplicate supplier payment.",
    )
    voided_payment.full_clean()
    voided_payment.save()

    balance = supplier_invoice.balance

    assert balance.paid_amount == Decimal("40000.00")
    assert balance.outstanding_amount == Decimal("60000.00")


@pytest.mark.django_db
def test_unsaved_supplier_invoice_has_no_balance(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require persistence before querying payments."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    supplier_invoice = _draft_supplier_invoice(
        context=purchasing_context,
        receipt_context=receipt_context,
    )

    with pytest.raises(
        ValueError,
        match="must be saved",
    ):
        _ = supplier_invoice.balance
