"""Tests for purchase-order goods-receipt forms."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django import forms
from django.utils import timezone

from apps.inventory.models import (
    InventoryItem,
    StockLocation,
)
from apps.product_catalogue.constants import (
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.forms import (
    GoodsReceiptHeaderForm,
    GoodsReceiptLineFormSet,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
    approve_purchase_order,
    create_purchase_order,
    submit_purchase_order,
)
from apps.purchasing.services.receipts import (
    GoodsReceiptLineCommand,
    ReceivePurchaseOrderCommand,
    receive_purchase_order,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)

pytestmark = pytest.mark.django_db


def _create_product(
    *,
    context: PurchasingTestContext,
    sku: str,
) -> Product:
    """Create one active catalogue product."""

    category = ProductCategory(
        code=f"CAT-{sku}"[:30],
        name=f"Category {sku}"[:120],
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku=sku,
        name=f"Product {sku}",
        category=category,
        unit=ProductUnit.EACH,
        description="Goods-receipt form product.",
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _create_inventory_item(
    *,
    context: PurchasingTestContext,
    product: Product,
    code: str,
    is_active: bool = True,
) -> InventoryItem:
    """Create one inventory destination."""

    location = StockLocation(
        code=code,
        name=f"{code} Location",
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    location.full_clean()
    location.save()

    inventory_item = InventoryItem(
        product=product,
        location=location,
        reorder_level=Decimal("0.000"),
        is_active=is_active,
        created_by=context.manager,
        updated_by=context.manager,
    )
    inventory_item.full_clean()
    inventory_item.save()

    return inventory_item


def _create_receivable_context(
    *,
    context: PurchasingTestContext,
):
    """Create an approved order and inventory item."""

    product = _create_product(
        context=context,
        sku="GR-FORM-001",
    )
    inventory_item = _create_inventory_item(
        context=context,
        product=product,
        code="GR-FORM-STORE",
    )

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="GR-FORM-SUPPLIER",
            name="Goods Receipt Form Supplier",
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
        ),
    )

    purchase_order_line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=(purchase_order.pk),
        command=(
            AddPurchaseOrderLineCommand(
                product_id=product.pk,
                quantity_ordered=Decimal("10.000"),
                unit_cost=Decimal("25000.00"),
            )
        ),
    )

    submit_purchase_order(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
    )
    purchase_order = approve_purchase_order(
        actor=context.manager,
        purchase_order_id=(purchase_order.pk),
    )

    return (
        purchase_order,
        purchase_order_line,
        product,
        inventory_item,
    )


def _formset_data(
    *,
    purchase_order_line_id: int,
    inventory_item_id: int | str = "",
    quantity: str = "",
    receive: bool = False,
) -> dict[str, str]:
    """Return one bound goods-receipt formset."""

    data = {
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "100",
        "form-0-purchase_order_line_id": str(purchase_order_line_id),
        "form-0-inventory_item": str(inventory_item_id),
        "form-0-quantity_received": quantity,
    }

    if receive:
        data["form-0-receive"] = "on"

    return data


def test_goods_receipt_header_form_normalises_input() -> None:
    """Normalise delivery reference and notes."""

    received_at = timezone.now() - timedelta(minutes=5)

    form = GoodsReceiptHeaderForm(
        {
            "supplier_delivery_reference": ("  DELIVERY   NOTE  100  "),
            "received_at": received_at.strftime("%Y-%m-%dT%H:%M"),
            "notes": "  Delivery checked.  ",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["supplier_delivery_reference"] == "DELIVERY NOTE 100"
    assert form.cleaned_data["notes"] == ("Delivery checked.")


def test_goods_receipt_header_rejects_future_time() -> None:
    """Reject future receipt timestamps."""

    future_time = timezone.localtime(timezone.now() + timedelta(hours=1))

    form = GoodsReceiptHeaderForm(
        {
            "supplier_delivery_reference": "",
            "received_at": future_time.strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        }
    )

    assert not form.is_valid()
    assert "received_at" in form.errors


def test_receipt_formset_loads_outstanding_line(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display the line and remaining quantity."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    formset = GoodsReceiptLineFormSet(purchase_order=purchase_order)

    assert formset.total_form_count() == 1

    form = formset.forms[0]
    field = form.fields["inventory_item"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )
    assert list(field.queryset) == [inventory_item]
    assert form.initial["purchase_order_line_id"] == purchase_order_line.pk
    assert form.initial["quantity_received"] == Decimal("10.000")


def test_receipt_formset_excludes_wrong_product(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Only list inventory for the ordered product."""

    (
        purchase_order,
        _purchase_order_line,
        _product,
        matching_inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    other_product = _create_product(
        context=purchasing_context,
        sku="GR-FORM-OTHER",
    )
    _create_inventory_item(
        context=purchasing_context,
        product=other_product,
        code="GR-OTHER-STORE",
    )

    formset = GoodsReceiptLineFormSet(purchase_order=purchase_order)
    field = formset.forms[0].fields["inventory_item"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )
    assert list(field.queryset) == [matching_inventory_item]


def test_receipt_formset_excludes_inactive_item(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Exclude inactive inventory destinations."""

    (
        purchase_order,
        _purchase_order_line,
        product,
        active_inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    _create_inventory_item(
        context=purchasing_context,
        product=product,
        code="GR-INACTIVE-STORE",
        is_active=False,
    )

    formset = GoodsReceiptLineFormSet(purchase_order=purchase_order)
    field = formset.forms[0].fields["inventory_item"]

    assert isinstance(
        field,
        forms.ModelChoiceField,
    )
    assert list(field.queryset) == [active_inventory_item]


def test_receipt_formset_accepts_selected_line(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Accept a valid delivered product."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    formset = GoodsReceiptLineFormSet(
        _formset_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
            quantity="4.000",
            receive=True,
        ),
        purchase_order=purchase_order,
    )

    assert formset.is_valid(), formset.errors

    line_data = formset.forms[0].cleaned_data

    assert line_data["receive"] is True
    assert line_data["inventory_item"] == inventory_item
    assert line_data["quantity_received"] == Decimal("4.000")


def test_receipt_formset_requires_selected_product(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require at least one delivered product."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        _inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    formset = GoodsReceiptLineFormSet(
        _formset_data(
            purchase_order_line_id=(purchase_order_line.pk),
        ),
        purchase_order=purchase_order,
    )

    assert not formset.is_valid()
    assert "Select at least one delivered product." in formset.non_form_errors()


def test_selected_line_requires_inventory_and_quantity(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require destination and delivered quantity."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        _inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    formset = GoodsReceiptLineFormSet(
        _formset_data(
            purchase_order_line_id=(purchase_order_line.pk),
            receive=True,
        ),
        purchase_order=purchase_order,
    )

    assert not formset.is_valid()

    errors = formset.forms[0].errors

    assert "inventory_item" in errors
    assert "quantity_received" in errors


def test_receipt_formset_rejects_over_receipt(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject quantities above the outstanding amount."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    formset = GoodsReceiptLineFormSet(
        _formset_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
            quantity="10.001",
            receive=True,
        ),
        purchase_order=purchase_order,
    )

    assert not formset.is_valid()
    assert "quantity_received" in formset.forms[0].errors


def test_partial_receipt_updates_remaining_initial(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display only the outstanding quantity."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    receive_purchase_order(
        actor=purchasing_context.manager,
        command=ReceivePurchaseOrderCommand(
            purchase_order_id=(purchase_order.pk),
            lines=(
                GoodsReceiptLineCommand(
                    purchase_order_line_id=(purchase_order_line.pk),
                    inventory_item_id=(inventory_item.pk),
                    quantity_received=Decimal("4.000"),
                ),
            ),
        ),
    )

    purchase_order.refresh_from_db()

    formset = GoodsReceiptLineFormSet(purchase_order=purchase_order)

    assert formset.total_form_count() == 1
    assert formset.forms[0].initial["quantity_received"] == Decimal("6.000")


def test_fully_received_line_is_not_displayed(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Remove completed lines from receipt input."""

    (
        purchase_order,
        purchase_order_line,
        _product,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    receive_purchase_order(
        actor=purchasing_context.manager,
        command=ReceivePurchaseOrderCommand(
            purchase_order_id=(purchase_order.pk),
            lines=(
                GoodsReceiptLineCommand(
                    purchase_order_line_id=(purchase_order_line.pk),
                    inventory_item_id=(inventory_item.pk),
                    quantity_received=Decimal("10.000"),
                ),
            ),
        ),
    )

    purchase_order.refresh_from_db()

    formset = GoodsReceiptLineFormSet(purchase_order=purchase_order)

    assert formset.total_form_count() == 0
    assert formset.receivable_lines == []
