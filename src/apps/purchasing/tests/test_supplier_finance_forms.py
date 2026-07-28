"""Tests for supplier-finance browser forms."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django import forms
from django.utils import timezone

from apps.purchasing.constants import (
    SupplierPaymentMethod,
)
from apps.purchasing.forms import (
    SupplierInvoiceCreateForm,
    SupplierInvoiceLineForm,
    SupplierInvoiceLineFormSet,
    SupplierInvoicePostForm,
    SupplierInvoiceVoidForm,
    SupplierPaymentRecordForm,
    SupplierPaymentVoidForm,
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


@pytest.mark.django_db
def test_invoice_form_lists_received_purchase_orders(
    purchasing_context: PurchasingTestContext,
) -> None:
    """List purchase orders containing received goods."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    form = SupplierInvoiceCreateForm()
    field = form.fields["purchase_order"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )

    queryset = field.queryset
    assert queryset is not None

    assert list(queryset) == [receipt_context.purchase_order]


@pytest.mark.django_db
def test_invoice_form_normalises_reference(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Normalise valid supplier-invoice data."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()

    form = SupplierInvoiceCreateForm(
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": ("  supplier   form  001 "),
            "invoice_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
            "notes": " Form test. ",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["supplier_reference"] == "supplier form 001"
    assert form.cleaned_data["notes"] == ("Form test.")


@pytest.mark.django_db
def test_invoice_form_rejects_early_due_date(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a due date before the invoice date."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()

    form = SupplierInvoiceCreateForm(
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": "SUP-FORM-001",
            "invoice_date": today.isoformat(),
            "due_date": (today - timedelta(days=1)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
        }
    )

    assert not form.is_valid()
    assert "due_date" in form.errors


@pytest.mark.django_db
def test_invoice_form_rejects_duplicate_reference(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a repeated reference for one supplier."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    today = timezone.localdate()

    create_supplier_invoice(
        actor=purchasing_context.manager,
        command=CreateSupplierInvoiceCommand(
            purchase_order_id=(receipt_context.purchase_order.pk),
            supplier_reference="SUP-DUP-FORM",
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

    form = SupplierInvoiceCreateForm(
        {
            "purchase_order": (receipt_context.purchase_order.pk),
            "supplier_reference": (" sup-dup-form "),
            "invoice_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "tax_amount": "0.00",
            "other_charges": "0.00",
        }
    )

    assert not form.is_valid()
    assert "supplier_reference" in form.errors


@pytest.mark.django_db
def test_line_form_lists_available_receipt_lines(
    purchasing_context: PurchasingTestContext,
) -> None:
    """List receipt lines with uninvoiced quantity."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    form = SupplierInvoiceLineForm(purchase_order=(receipt_context.purchase_order))
    field = form.fields["goods_receipt_line"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )

    queryset = field.queryset
    assert queryset is not None

    assert list(queryset) == [receipt_context.goods_receipt_line]


@pytest.mark.django_db
def test_line_form_rejects_excess_quantity(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject quantity above the received amount."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    form = SupplierInvoiceLineForm(
        {
            "goods_receipt_line": (receipt_context.goods_receipt_line.pk),
            "quantity_invoiced": "4.001",
            "unit_cost": "25000.00",
        },
        purchase_order=(receipt_context.purchase_order),
    )

    assert not form.is_valid()
    assert "quantity_invoiced" in form.errors


@pytest.mark.django_db
def test_line_form_rejects_cost_mismatch(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require the received supplier unit cost."""

    receipt_context = create_posted_receipt(context=purchasing_context)

    form = SupplierInvoiceLineForm(
        {
            "goods_receipt_line": (receipt_context.goods_receipt_line.pk),
            "quantity_invoiced": "4.000",
            "unit_cost": "26000.00",
        },
        purchase_order=(receipt_context.purchase_order),
    )

    assert not form.is_valid()
    assert "unit_cost" in form.errors


@pytest.mark.django_db
def test_line_formset_rejects_duplicate_receipt_line(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent the same receipt line appearing twice."""

    receipt_context = create_posted_receipt(context=purchasing_context)
    receipt_line_id = receipt_context.goods_receipt_line.pk

    formset = SupplierInvoiceLineFormSet(
        {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "50",
            "form-0-goods_receipt_line": (str(receipt_line_id)),
            "form-0-quantity_invoiced": "2.000",
            "form-0-unit_cost": "25000.00",
            "form-1-goods_receipt_line": (str(receipt_line_id)),
            "form-1-quantity_invoiced": "2.000",
            "form-1-unit_cost": "25000.00",
        },
        form_kwargs={"purchase_order": (receipt_context.purchase_order)},
    )

    assert not formset.is_valid()
    assert formset.non_form_errors()


@pytest.mark.django_db
def test_payment_form_enforces_outstanding_balance(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Set the maximum amount and reject overpayment."""

    context = create_supplier_finance_context(
        context=purchasing_context,
        payment_amount=Decimal("40000.00"),
    )
    supplier_invoice = context.supplier_invoice

    form = SupplierPaymentRecordForm(supplier_invoice=supplier_invoice)
    amount_field = form.fields["amount"]

    assert amount_field.widget.attrs["max"] == ("60000.00")

    invalid_form = SupplierPaymentRecordForm(
        {
            "amount": "60000.01",
            "method": (SupplierPaymentMethod.BANK_TRANSFER),
            "external_reference": "",
            "paid_at": "",
            "notes": "",
        },
        supplier_invoice=supplier_invoice,
    )

    assert not invalid_form.is_valid()
    assert "amount" in invalid_form.errors


@pytest.mark.django_db
def test_payment_form_rejects_future_time(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a supplier-payment time in the future."""

    context = create_supplier_finance_context(context=purchasing_context)
    future_time = timezone.localtime(timezone.now() + timedelta(hours=1))

    form = SupplierPaymentRecordForm(
        {
            "amount": "10000.00",
            "method": SupplierPaymentMethod.CASH,
            "external_reference": "",
            "paid_at": future_time.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        },
        supplier_invoice=context.supplier_invoice,
    )

    assert not form.is_valid()
    assert "paid_at" in form.errors


def test_post_form_requires_confirmation() -> None:
    """Require explicit three-way-match confirmation."""

    form = SupplierInvoicePostForm({})

    assert not form.is_valid()
    assert "confirmation" in form.errors


def test_void_forms_normalise_reasons() -> None:
    """Normalise invoice and payment void reasons."""

    invoice_form = SupplierInvoiceVoidForm(
        {"reason": ("  Supplier cancelled invoice. ")}
    )
    payment_form = SupplierPaymentVoidForm(
        {"reason": ("  Duplicate supplier payment. ")}
    )

    assert invoice_form.is_valid()
    assert payment_form.is_valid()

    assert invoice_form.cleaned_data["reason"] == ("Supplier cancelled invoice.")
    assert payment_form.cleaned_data["reason"] == ("Duplicate supplier payment.")
