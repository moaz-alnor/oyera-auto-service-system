"""Tests for supplier-finance selectors."""

from datetime import timedelta
from decimal import Decimal
from typing import Protocol, cast

import pytest
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
    SupplierPaymentStatus,
)
from apps.purchasing.selectors import (
    get_supplier_invoice_by_id,
    get_supplier_invoices_for_purchase_order,
    get_supplier_invoices_for_supplier,
    get_supplier_payment_by_id,
    search_supplier_invoices,
    search_supplier_payments,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.supplier_finance_factory import (
    create_supplier_finance_context,
)


class _SupplierInvoiceWithBalance(Protocol):
    """Describe supplier-invoice balance annotations."""

    paid_amount: Decimal
    outstanding_amount: Decimal


@pytest.mark.django_db
def test_search_supplier_invoices_by_audit_identity(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find invoices through financial audit data."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice
    receipt_context = context.receipt_context

    assert context.supplier_payment is not None

    search_values = (
        supplier_invoice.supplier_invoice_number,
        supplier_invoice.supplier_reference,
        supplier_invoice.supplier_name_snapshot,
        supplier_invoice.purchase_order_number_snapshot,
        receipt_context.product.sku,
        receipt_context.goods_receipt.goods_receipt_number,
        context.supplier_payment.payment_number,
        "BANK-SELECTOR-001",
    )

    for search_value in search_values:
        assert list(search_supplier_invoices(query=search_value)) == [supplier_invoice]


@pytest.mark.django_db
def test_filter_supplier_invoices(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Filter invoices by lifecycle and business parent."""

    today = timezone.localdate()

    context = create_supplier_finance_context(
        context=purchasing_context,
        invoice_date=today - timedelta(days=40),
        due_date=today - timedelta(days=10),
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice
    purchase_order = context.receipt_context.purchase_order

    assert supplier_invoice.status == (SupplierInvoiceStatus.PARTIALLY_PAID)

    assert list(
        search_supplier_invoices(status=SupplierInvoiceStatus.PARTIALLY_PAID)
    ) == [supplier_invoice]

    assert list(search_supplier_invoices(supplier_id=supplier_invoice.supplier_id)) == [
        supplier_invoice
    ]

    assert list(search_supplier_invoices(purchase_order_id=purchase_order.pk)) == [
        supplier_invoice
    ]

    assert list(search_supplier_invoices(overdue_only=True)) == [supplier_invoice]

    assert list(
        get_supplier_invoices_for_supplier(supplier_id=supplier_invoice.supplier_id)
    ) == [supplier_invoice]

    assert list(
        get_supplier_invoices_for_purchase_order(purchase_order_id=purchase_order.pk)
    ) == [supplier_invoice]


@pytest.mark.django_db
def test_supplier_invoice_queryset_calculates_balance(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Annotate paid and outstanding invoice amounts."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )

    selected = get_supplier_invoice_by_id(
        supplier_invoice_id=(context.supplier_invoice.pk)
    )
    annotated_invoice = cast(
        _SupplierInvoiceWithBalance,
        selected,
    )

    assert annotated_invoice.paid_amount == Decimal("40000.00")
    assert annotated_invoice.outstanding_amount == Decimal("60000.00")


@pytest.mark.django_db
def test_supplier_invoice_detail_is_query_optimised(
    purchasing_context: PurchasingTestContext,
    django_assert_num_queries,
) -> None:
    """Load one invoice and its audit collections efficiently."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )

    with django_assert_num_queries(3):
        selected = get_supplier_invoice_by_id(
            supplier_invoice_id=(context.supplier_invoice.pk)
        )
        lines = list(selected.lines.all())
        payments = list(selected.payments.all())

        assert selected.supplier.name
        assert selected.purchase_order.purchase_order_number
        assert lines[0].purchase_order_line.product.name
        assert lines[0].goods_receipt_line.goods_receipt.goods_receipt_number
        assert payments[0].recorded_by.username

    assert len(lines) == 1
    assert len(payments) == 1


@pytest.mark.django_db
def test_search_and_load_supplier_payments(
    purchasing_context: PurchasingTestContext,
    django_assert_num_queries,
) -> None:
    """Search and load supplier payments efficiently."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    payment = context.supplier_payment
    supplier_invoice = context.supplier_invoice

    assert payment is not None

    assert list(search_supplier_payments(query=payment.payment_number)) == [payment]

    assert list(search_supplier_payments(query="BANK-SELECTOR-001")) == [payment]

    assert list(
        search_supplier_payments(
            status=SupplierPaymentStatus.POSTED,
            method=SupplierPaymentMethod.BANK_TRANSFER,
            supplier_invoice_id=supplier_invoice.pk,
            supplier_id=supplier_invoice.supplier_id,
        )
    ) == [payment]

    with django_assert_num_queries(1):
        selected = get_supplier_payment_by_id(supplier_payment_id=payment.pk)

        assert selected.supplier_invoice.supplier_invoice_number
        assert selected.supplier_invoice.supplier.name
        assert selected.recorded_by.username
