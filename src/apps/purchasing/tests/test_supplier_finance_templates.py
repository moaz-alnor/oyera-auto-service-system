"""Tests for supplier-finance templates and navigation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierInvoiceStatus,
)
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    create_supplier_invoice,
)
from apps.purchasing.services.supplier_payments import (
    VoidSupplierPaymentCommand,
    void_supplier_payment,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    create_posted_receipt,
)
from apps.purchasing.tests.supplier_finance_factory import (
    create_supplier_finance_context,
)

pytestmark = pytest.mark.django_db


def test_manager_sees_purchasing_navigation(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display Purchasing navigation to management."""

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:supplier_invoice_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Supplier invoices" in content
    assert "Purchasing" in content
    assert 'href="/purchasing/supplier-invoices/"' in content
    assert 'href="/purchasing/supplier-invoices/new/"' in content


def test_supplier_invoice_list_displays_financial_summary(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display invoice identity and current balance."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference="SUP-LIST-001",
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:supplier_invoice_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier_invoice.supplier_invoice_number in content
    assert "SUP-LIST-001" in content
    assert supplier_invoice.supplier_name_snapshot in content
    assert supplier_invoice.purchase_order_number_snapshot in content
    assert "100000.00" in content
    assert "40000.00" in content
    assert "60000.00" in content


def test_supplier_invoice_list_applies_filters(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Apply search, lifecycle, and overdue filters."""

    today = timezone.localdate()

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-LIST-OVERDUE-001"),
        invoice_date=(today - timedelta(days=40)),
        due_date=(today - timedelta(days=10)),
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice
    purchase_order = context.receipt_context.purchase_order

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:supplier_invoice_list"),
        {
            "q": "SUP-LIST-OVERDUE-001",
            "status": (SupplierInvoiceStatus.PARTIALLY_PAID),
            "supplier": (supplier_invoice.supplier_id),
            "purchase_order": purchase_order.pk,
            "overdue": "1",
        },
    )

    assert response.status_code == 200
    assert list(response.context["supplier_invoices"]) == [supplier_invoice]
    assert response.context["selected_status"] == SupplierInvoiceStatus.PARTIALLY_PAID
    assert response.context["selected_supplier_id"] == supplier_invoice.supplier_id
    assert response.context["selected_purchase_order_id"] == purchase_order.pk
    assert response.context["overdue_only"] is True

    content = response.content.decode()

    assert "SUP-LIST-OVERDUE-001" in content
    assert "Partially paid" in content
    assert "checked" in content


def test_technician_cannot_view_supplier_invoices(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject employees without Purchasing access."""

    client.force_login(purchasing_context.technician)

    response = client.get(reverse("purchasing:supplier_invoice_list"))

    assert response.status_code == 403


def test_supplier_invoice_create_prompts_for_purchase_order(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require an order before displaying receipt lines."""

    create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:supplier_invoice_create"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Choose a received purchase order" in content
    assert "Load received lines" in content
    assert 'name="purchase_order"' in content
    assert "Create draft supplier invoice" not in content


def test_supplier_invoice_create_displays_received_lines(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display available receipt lines and matching data."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:supplier_invoice_create"),
        {"purchase_order": (receipt_context.purchase_order.pk)},
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["selected_purchase_order"] == receipt_context.purchase_order
    assert receipt_context.purchase_order.purchase_order_number in content
    assert receipt_context.goods_receipt.goods_receipt_number in content
    assert receipt_context.product.sku in content
    assert receipt_context.product.name in content
    assert "available 4.000" in content
    assert "cost UGX 25000.00" in content
    assert 'name="lines-TOTAL_FORMS"' in content
    assert "Add another line" in content
    assert "Three-way match" in content


def test_supplier_invoice_create_displays_quantity_error(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display received-quantity validation errors."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:supplier_invoice_create"),
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": ("SUP-TEMPLATE-QTY-001"),
            "invoice_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
            "notes": "",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "50",
            "lines-0-goods_receipt_line": (receipt_context.goods_receipt_line.pk),
            "lines-0-quantity_invoiced": ("4.001"),
            "lines-0-unit_cost": "25000.00",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Invoiced quantity cannot exceed the remaining received quantity." in content


def test_supplier_invoice_create_displays_duplicate_line_error(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display duplicate receipt-line formset errors."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()
    receipt_line_id = receipt_context.goods_receipt_line.pk

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:supplier_invoice_create"),
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": ("SUP-TEMPLATE-DUP-001"),
            "invoice_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
            "notes": "",
            "lines-TOTAL_FORMS": "2",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "50",
            "lines-0-goods_receipt_line": (receipt_line_id),
            "lines-0-quantity_invoiced": ("2.000"),
            "lines-0-unit_cost": "25000.00",
            "lines-1-goods_receipt_line": (receipt_line_id),
            "lines-1-quantity_invoiced": ("2.000"),
            "lines-1-unit_cost": "25000.00",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "A goods-receipt line cannot appear more than once." in content


def _create_draft_supplier_invoice(
    *,
    context: PurchasingTestContext,
):
    """Create one matched draft for template tests."""

    receipt_context = create_posted_receipt(context=context)
    today = timezone.localdate()

    supplier_invoice = create_supplier_invoice(
        actor=context.manager,
        command=CreateSupplierInvoiceCommand(
            purchase_order_id=(receipt_context.purchase_order.pk),
            supplier_reference=("SUP-DETAIL-DRAFT-001"),
            invoice_date=today,
            due_date=(today + timedelta(days=30)),
            lines=(
                SupplierInvoiceLineCommand(
                    goods_receipt_line_id=(receipt_context.goods_receipt_line.pk),
                    quantity_invoiced=Decimal("4.000"),
                    unit_cost=Decimal("25000.00"),
                ),
            ),
            notes="Supplier detail template test.",
        ),
    )

    return supplier_invoice, receipt_context


def test_draft_supplier_invoice_detail_displays_match_audit(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display draft identity and three-way-match data."""

    (
        supplier_invoice,
        receipt_context,
    ) = _create_draft_supplier_invoice(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier_invoice.supplier_invoice_number in content
    assert "SUP-DETAIL-DRAFT-001" in content
    assert supplier_invoice.purchase_order_number_snapshot in content
    assert receipt_context.goods_receipt.goods_receipt_number in content
    assert receipt_context.product.sku in content
    assert receipt_context.product.name in content
    assert "4.000" in content
    assert "25000.00" in content
    assert "100000.00" in content
    assert "Post supplier invoice" in content
    assert "Record supplier payment" not in content
    assert "Void supplier invoice" not in content


def test_partially_paid_invoice_detail_displays_balance_and_payment(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display totals and active supplier payment history."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-DETAIL-PAID-001"),
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice
    payment = context.supplier_payment

    assert payment is not None

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Partially paid" in content
    assert "100000.00" in content
    assert "40000.00" in content
    assert "60000.00" in content
    assert payment.payment_number in content
    assert "BANK-SELECTOR-001" in content
    assert "Bank transfer" in content
    assert "Record supplier payment" in content
    assert "Void supplier payment" in content


def test_supplier_invoice_detail_displays_overdue_warning(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display an overdue outstanding-balance warning."""

    today = timezone.localdate()

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-DETAIL-OVERDUE-001"),
        invoice_date=(today - timedelta(days=40)),
        due_date=(today - timedelta(days=10)),
        payment_amount=Decimal("40000.00"),
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(context.supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "This supplier invoice is overdue" in content
    assert "60000.00" in content


def test_supplier_invoice_detail_preserves_voided_payment_audit(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display voided payment evidence and restored balance."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-DETAIL-VOID-PAYMENT-001"),
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment

    assert payment is not None

    void_supplier_payment(
        actor=purchasing_context.manager,
        payment_id=payment.pk,
        command=VoidSupplierPaymentCommand(reason="Duplicate supplier payment."),
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(context.supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert payment.payment_number in content
    assert "Voided" in content
    assert "Duplicate supplier payment." in content
    assert "100000.00" in content
    assert "Void supplier payment" not in content


def test_cashier_sees_payment_action_without_management_actions(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Show Cashier payment access without void or post access."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-DETAIL-CASHIER-001"),
    )

    client.force_login(purchasing_context.cashier)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(context.supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Record supplier payment" in content
    assert "Post supplier invoice" not in content
    assert "Void supplier invoice" not in content
    assert "Void supplier payment" not in content


def test_supplier_invoice_post_template_requires_confirmation(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display posting evidence and require confirmation."""

    (
        supplier_invoice,
        _receipt_context,
    ) = _create_draft_supplier_invoice(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_post",
            args=(supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier_invoice.supplier_invoice_number in content
    assert supplier_invoice.purchase_order_number_snapshot in content
    assert "100000.00" in content
    assert "Posting confirmation" in content
    assert 'name="confirmation"' in content
    assert "Post supplier invoice" in content

    invalid_response = client.post(
        reverse(
            "purchasing:supplier_invoice_post",
            args=(supplier_invoice.pk,),
        ),
        {},
    )

    invalid_content = invalid_response.content.decode()

    supplier_invoice.refresh_from_db()

    assert invalid_response.status_code == 200
    assert "This field is required." in invalid_content
    assert supplier_invoice.status == (SupplierInvoiceStatus.DRAFT)


def test_supplier_invoice_void_template_displays_warning(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display invoice identity and irreversible warning."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-ACTION-VOID-001"),
    )
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_void",
            args=(supplier_invoice.pk,),
        )
    )

    content = response.content.decode()
    normalised_content = " ".join(content.split())

    assert response.status_code == 200
    assert supplier_invoice.supplier_invoice_number in content
    assert "SUP-ACTION-VOID-001" in content
    assert "Voiding this supplier invoice cannot be undone." in normalised_content
    assert "100000.00" in content
    assert 'name="reason"' in content
    assert "Void supplier invoice" in content


def test_supplier_invoice_void_template_requires_reason(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display a required-reason validation error."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-ACTION-VOID-REQUIRED-001"),
    )
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_invoice_void",
            args=(supplier_invoice.pk,),
        ),
        {
            "reason": "",
        },
    )

    supplier_invoice.refresh_from_db()

    content = response.content.decode()

    assert response.status_code == 200
    assert "This field is required." in content
    assert supplier_invoice.status == (SupplierInvoiceStatus.POSTED)


def test_supplier_payment_template_displays_balance(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display invoice balance and payment controls."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-ACTION-PAYMENT-001"),
    )
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.cashier)

    response = client.get(
        reverse(
            "purchasing:supplier_payment_record",
            args=(supplier_invoice.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert supplier_invoice.supplier_invoice_number in content
    assert "SUP-ACTION-PAYMENT-001" in content
    assert "100000.00" in content
    assert "Outstanding balance" in content
    assert 'name="amount"' in content
    assert 'max="100000.00"' in content
    assert 'name="method"' in content
    assert 'name="external_reference"' in content
    assert 'name="paid_at"' in content
    assert "Record supplier payment" in content


def test_supplier_payment_template_displays_overpayment_error(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display payment balance validation errors."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-ACTION-OVERPAY-001"),
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.cashier)

    response = client.post(
        reverse(
            "purchasing:supplier_payment_record",
            args=(supplier_invoice.pk,),
        ),
        {
            "amount": "60000.01",
            "method": "BANK_TRANSFER",
            "external_reference": ("BANK-OVERPAY-001"),
            "paid_at": "",
            "notes": "",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Supplier payment cannot exceed the outstanding invoice balance." in content
    assert "60000.00" in content


def test_supplier_payment_void_template_displays_audit_details(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display payment identity and void consequences."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        supplier_reference=("SUP-ACTION-VOID-PAYMENT-001"),
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment

    assert payment is not None

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_payment_void",
            args=(payment.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert payment.payment_number in content
    assert "40000.00" in content
    assert "Bank transfer" in content
    assert "BANK-SELECTOR-001" in content
    assert "no longer count" in content
    assert 'name="reason"' in content
    assert "Void supplier payment" in content


def test_cashier_cannot_open_supplier_payment_void_template(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Restrict supplier-payment reversal to management."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment

    assert payment is not None

    client.force_login(purchasing_context.cashier)

    response = client.get(
        reverse(
            "purchasing:supplier_payment_void",
            args=(payment.pk,),
        )
    )

    assert response.status_code == 403
