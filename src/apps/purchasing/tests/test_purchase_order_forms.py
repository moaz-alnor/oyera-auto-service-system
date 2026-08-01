"""Tests for purchase-order browser forms."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django import forms
from django.utils import timezone

from apps.product_catalogue.constants import (
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.forms import (
    PurchaseOrderApprovalForm,
    PurchaseOrderCancellationForm,
    PurchaseOrderCreateForm,
    PurchaseOrderLineCreateForm,
    PurchaseOrderLineUpdateForm,
    PurchaseOrderSubmitForm,
)
from apps.purchasing.models import Supplier
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
    create_purchase_order,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    deactivate_supplier,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _create_supplier(
    *,
    context: PurchasingTestContext,
    code: str,
    name: str,
) -> Supplier:
    """Create one supplier for form tests."""

    return register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code=code,
            name=name,
            payment_terms_days=30,
            preferred_currency="UGX",
        ),
    )


def _create_category(
    *,
    context: PurchasingTestContext,
) -> ProductCategory:
    """Create one product category."""

    category = ProductCategory(
        code="PO-FORM-PARTS",
        name="Purchase Order Form Parts",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    return category


def _create_product(
    *,
    context: PurchasingTestContext,
    category: ProductCategory,
    sku: str,
    name: str,
    is_active: bool = True,
) -> Product:
    """Create one catalogue product."""

    product = Product(
        sku=sku,
        name=name,
        category=category,
        unit=ProductUnit.EACH,
        description="Purchase-order form product.",
        is_active=is_active,
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _valid_header_data(
    *,
    supplier_id: int,
) -> dict[str, str]:
    """Return valid purchase-order input."""

    return {
        "supplier": str(supplier_id),
        "currency": "ugx",
        "discount_percentage": "5.00",
        "tax_percentage": "18.00",
        "delivery_cost": "15000.00",
        "expected_delivery_date": (
            timezone.localdate() + timedelta(days=7)
        ).isoformat(),
        "supplier_reference": "QUOTE-PO-001",
        "notes": "Purchase-order form test.",
    }


def test_purchase_order_create_form_is_valid(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Accept and normalise purchase-order input."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PO-FORM-SUPPLIER",
        name="Purchase Order Form Supplier",
    )

    form = PurchaseOrderCreateForm(_valid_header_data(supplier_id=supplier.pk))

    assert form.is_valid(), form.errors
    assert form.cleaned_data["supplier"] == (supplier)
    assert form.cleaned_data["currency"] == ("UGX")
    assert form.cleaned_data["discount_percentage"] == Decimal("5.00")
    assert form.cleaned_data["tax_percentage"] == Decimal("18.00")


def test_purchase_order_form_lists_only_active_suppliers(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Exclude inactive suppliers from ordering."""

    active_supplier = _create_supplier(
        context=purchasing_context,
        code="ACTIVE-PO-SUPPLIER",
        name="Active Purchase Supplier",
    )
    inactive_supplier = _create_supplier(
        context=purchasing_context,
        code="INACTIVE-PO-SUPPLIER",
        name="Inactive Purchase Supplier",
    )

    deactivate_supplier(
        actor=purchasing_context.manager,
        supplier_id=inactive_supplier.pk,
    )

    form = PurchaseOrderCreateForm()
    field = form.fields["supplier"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )
    assert field.queryset is not None
    assert list(field.queryset) == [active_supplier]


@pytest.mark.parametrize(
    "currency",
    (
        "",
        "UG",
        "UGXA",
        "12A",
    ),
)
def test_purchase_order_form_rejects_invalid_currency(
    purchasing_context: PurchasingTestContext,
    currency: str,
) -> None:
    """Reject malformed currency codes."""

    supplier = _create_supplier(
        context=purchasing_context,
        code=f"CURRENCY-{currency or 'EMPTY'}",
        name=f"Currency Supplier {currency or 'Empty'}",
    )
    data = _valid_header_data(supplier_id=supplier.pk)
    data["currency"] = currency

    form = PurchaseOrderCreateForm(data)

    assert not form.is_valid()
    assert "currency" in form.errors


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("discount_percentage", "-0.01"),
        ("discount_percentage", "100.01"),
        ("tax_percentage", "-0.01"),
        ("tax_percentage", "100.01"),
    ),
)
def test_purchase_order_form_rejects_invalid_percentages(
    purchasing_context: PurchasingTestContext,
    field_name: str,
    value: str,
) -> None:
    """Keep discount and tax within valid ranges."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="PERCENT-TEST-SUPPLIER",
        name="Percentage Test Supplier",
    )
    data = _valid_header_data(supplier_id=supplier.pk)
    data[field_name] = value

    form = PurchaseOrderCreateForm(data)

    assert not form.is_valid()
    assert field_name in form.errors


def test_purchase_order_form_rejects_negative_delivery_cost(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject a negative delivery charge."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="NEGATIVE-DELIVERY",
        name="Negative Delivery Supplier",
    )
    data = _valid_header_data(supplier_id=supplier.pk)
    data["delivery_cost"] = "-0.01"

    form = PurchaseOrderCreateForm(data)

    assert not form.is_valid()
    assert "delivery_cost" in form.errors


def test_purchase_order_line_form_is_valid(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Accept a product, quantity, cost, and description."""

    category = _create_category(context=purchasing_context)
    product = _create_product(
        context=purchasing_context,
        category=category,
        sku="PO-LINE-001",
        name="Purchase Order Line Product",
    )

    form = PurchaseOrderLineCreateForm(
        {
            "product": str(product.pk),
            "quantity_ordered": "2.500",
            "unit_cost": "25000.00",
            "description_override": ("Special supplier description."),
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["product"] == (product)
    assert form.cleaned_data["quantity_ordered"] == Decimal("2.500")
    assert form.cleaned_data["unit_cost"] == Decimal("25000.00")


def test_line_form_excludes_inactive_and_existing_products(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Show only active products not already ordered."""

    supplier = _create_supplier(
        context=purchasing_context,
        code="LINE-FILTER-SUPPLIER",
        name="Line Filter Supplier",
    )
    category = _create_category(context=purchasing_context)
    existing_product = _create_product(
        context=purchasing_context,
        category=category,
        sku="PO-EXISTING-001",
        name="Existing Ordered Product",
    )
    available_product = _create_product(
        context=purchasing_context,
        category=category,
        sku="PO-AVAILABLE-001",
        name="Available Order Product",
    )
    _create_product(
        context=purchasing_context,
        category=category,
        sku="PO-INACTIVE-001",
        name="Inactive Order Product",
        is_active=False,
    )

    purchase_order = create_purchase_order(
        actor=purchasing_context.manager,
        command=CreatePurchaseOrderCommand(supplier_id=supplier.pk),
    )

    add_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_id=purchase_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=existing_product.pk,
            quantity_ordered=Decimal("1.000"),
            unit_cost=Decimal("10000.00"),
        ),
    )

    form = PurchaseOrderLineCreateForm(purchase_order=purchase_order)
    field = form.fields["product"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )
    assert field.queryset is not None
    assert list(field.queryset) == [available_product]


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("quantity_ordered", "0.000"),
        ("unit_cost", "0.00"),
    ),
)
def test_line_form_rejects_nonpositive_values(
    purchasing_context: PurchasingTestContext,
    field_name: str,
    value: str,
) -> None:
    """Require positive ordered quantity and cost."""

    category = _create_category(context=purchasing_context)
    product = _create_product(
        context=purchasing_context,
        category=category,
        sku=f"NONPOSITIVE-{field_name}",
        name=f"Nonpositive {field_name}",
    )
    data = {
        "product": str(product.pk),
        "quantity_ordered": "1.000",
        "unit_cost": "10000.00",
        "description_override": "",
    }
    data[field_name] = value

    form = PurchaseOrderLineCreateForm(data)

    assert not form.is_valid()
    assert field_name in form.errors


def test_line_update_form_does_not_change_product() -> None:
    """Keep the selected product immutable."""

    form = PurchaseOrderLineUpdateForm()

    assert "product" not in form.fields
    assert "quantity_ordered" in form.fields
    assert "unit_cost" in form.fields


def test_purchase_order_lifecycle_forms_require_confirmation() -> None:
    """Require deliberate submission and approval."""

    for form_class in (
        PurchaseOrderSubmitForm,
        PurchaseOrderApprovalForm,
    ):
        form = form_class({})

        assert not form.is_valid()
        assert "confirmation" in form.errors


def test_purchase_order_cancellation_requires_reason() -> None:
    """Require and normalise cancellation evidence."""

    empty_form = PurchaseOrderCancellationForm(
        {
            "reason": "   ",
        }
    )

    assert not empty_form.is_valid()
    assert "reason" in empty_form.errors

    valid_form = PurchaseOrderCancellationForm(
        {
            "reason": ("  Supplier cannot fulfil order.  "),
        }
    )

    assert valid_form.is_valid(), valid_form.errors
    assert valid_form.cleaned_data["reason"] == ("Supplier cannot fulfil order.")
