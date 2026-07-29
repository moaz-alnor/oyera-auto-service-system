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
