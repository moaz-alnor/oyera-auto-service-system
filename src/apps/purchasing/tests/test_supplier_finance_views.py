"""Tests for supplier-finance browser views."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    SupplierInvoice,
    SupplierPayment,
)
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    create_supplier_invoice,
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


def _create_draft_invoice(
    *,
    context: PurchasingTestContext,
) -> SupplierInvoice:
    """Create one draft invoice for view tests."""

    receipt_context = create_posted_receipt(context=context)
    today = timezone.localdate()

    return create_supplier_invoice(
        actor=context.manager,
        command=CreateSupplierInvoiceCommand(
            purchase_order_id=(receipt_context.purchase_order.pk),
            supplier_reference=("SUP-VIEW-DRAFT-001"),
            invoice_date=today,
            due_date=(today + timedelta(days=30)),
            lines=(
                SupplierInvoiceLineCommand(
                    goods_receipt_line_id=(receipt_context.goods_receipt_line.pk),
                    quantity_invoiced=Decimal("4.000"),
                    unit_cost=Decimal("25000.00"),
                ),
            ),
        ),
    )


def test_supplier_finance_urls_reverse() -> None:
    """Reverse every supplier-finance route."""

    assert (
        reverse("purchasing:supplier_invoice_list") == "/purchasing/supplier-invoices/"
    )

    assert (
        reverse("purchasing:supplier_invoice_create")
        == "/purchasing/supplier-invoices/new/"
    )

    assert (
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(1,),
        )
        == "/purchasing/supplier-invoices/1/"
    )

    assert reverse(
        "purchasing:supplier_invoice_post",
        args=(1,),
    ) == ("/purchasing/supplier-invoices/1/post/")

    assert reverse(
        "purchasing:supplier_invoice_void",
        args=(1,),
    ) == ("/purchasing/supplier-invoices/1/void/")

    assert reverse(
        "purchasing:supplier_payment_record",
        args=(1,),
    ) == ("/purchasing/supplier-invoices/1/payments/new/")

    assert reverse(
        "purchasing:supplier_payment_void",
        args=(1,),
    ) == ("/purchasing/supplier-payments/1/void/")


@pytest.mark.django_db
def test_anonymous_user_is_redirected(
    client: Client,
) -> None:
    """Require authentication for supplier finance."""

    response = client.get(reverse("purchasing:supplier_invoice_list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_manager_views_supplier_invoice_list(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow management to view supplier invoices."""

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:supplier_invoice_list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_manager_creates_supplier_invoice_from_browser(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Create a matched draft through the browser."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse("purchasing:supplier_invoice_create"),
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": ("SUP-BROWSER-001"),
            "invoice_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
            "notes": "Browser invoice test.",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "50",
            "lines-0-goods_receipt_line": (receipt_context.goods_receipt_line.pk),
            "lines-0-quantity_invoiced": ("4.000"),
            "lines-0-unit_cost": "25000.00",
        },
    )

    supplier_invoice = SupplierInvoice.objects.get(
        supplier_reference=("SUP-BROWSER-001")
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:supplier_invoice_detail",
        args=(supplier_invoice.pk,),
    )
    assert supplier_invoice.status == (SupplierInvoiceStatus.DRAFT)


@pytest.mark.django_db
def test_manager_posts_supplier_invoice_from_browser(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Post a matched draft through the browser."""

    supplier_invoice = _create_draft_invoice(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_invoice_post",
            args=(supplier_invoice.pk,),
        ),
        {
            "confirmation": "on",
        },
    )

    supplier_invoice.refresh_from_db()

    assert response.status_code == 302
    assert supplier_invoice.status == (SupplierInvoiceStatus.POSTED)


@pytest.mark.django_db
def test_cashier_records_supplier_payment_from_browser(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Record an accounts-payable payment."""

    context = create_supplier_finance_context(context=purchasing_context)
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.cashier)

    response = client.post(
        reverse(
            "purchasing:supplier_payment_record",
            args=(supplier_invoice.pk,),
        ),
        {
            "amount": "40000.00",
            "method": (SupplierPaymentMethod.BANK_TRANSFER),
            "external_reference": ("BANK-BROWSER-001"),
            "paid_at": "",
            "notes": "Browser payment test.",
        },
    )

    payment = SupplierPayment.objects.get(supplier_invoice=supplier_invoice)
    supplier_invoice.refresh_from_db()

    assert response.status_code == 302
    assert payment.status == (SupplierPaymentStatus.POSTED)
    assert supplier_invoice.status == (SupplierInvoiceStatus.PARTIALLY_PAID)


@pytest.mark.django_db
def test_cashier_cannot_void_supplier_payment(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep payment reversal under management."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment

    assert payment is not None

    client.force_login(purchasing_context.cashier)

    response = client.post(
        reverse(
            "purchasing:supplier_payment_void",
            args=(payment.pk,),
        ),
        {
            "reason": ("Cashier reversal attempt."),
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_voids_supplier_payment_from_browser(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Void a supplier payment through the browser."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment
    supplier_invoice = context.supplier_invoice

    assert payment is not None

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_payment_void",
            args=(payment.pk,),
        ),
        {
            "reason": ("Duplicate supplier payment."),
        },
    )

    payment.refresh_from_db()
    supplier_invoice.refresh_from_db()

    assert response.status_code == 302
    assert payment.status == (SupplierPaymentStatus.VOIDED)
    assert supplier_invoice.status == (SupplierInvoiceStatus.POSTED)


@pytest.mark.django_db
def test_manager_voids_unpaid_invoice_from_browser(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Void an unpaid posted supplier invoice."""

    context = create_supplier_finance_context(context=purchasing_context)
    supplier_invoice = context.supplier_invoice

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:supplier_invoice_void",
            args=(supplier_invoice.pk,),
        ),
        {
            "reason": ("Supplier cancelled invoice."),
        },
    )

    supplier_invoice.refresh_from_db()

    assert response.status_code == 302
    assert supplier_invoice.status == (SupplierInvoiceStatus.VOIDED)


@pytest.mark.django_db
def test_missing_supplier_invoice_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown invoice."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:supplier_invoice_detail",
            args=(999999,),
        )
    )

    assert response.status_code == 404
