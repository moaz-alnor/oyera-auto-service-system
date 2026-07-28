"""Tests for purchase-order database models."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.product_catalogue.constants import (
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)


def _create_supplier(
    *,
    context: PurchasingTestContext,
) -> Supplier:
    """Create a supplier for order-model tests."""

    supplier = Supplier(
        supplier_number="SUP-TEST-001",
        code="ORDER-SUPPLIER",
        name="Order Test Supplier",
        preferred_currency="UGX",
        created_by=context.manager,
        updated_by=context.manager,
    )
    supplier.full_clean()
    supplier.save()

    return supplier


def _create_product(
    *,
    context: PurchasingTestContext,
) -> Product:
    """Create a product for order-line tests."""

    category = ProductCategory(
        code="PO-TEST",
        name="Purchase Order Test Parts",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="PO-PART-001",
        name="Purchase Order Test Part",
        category=category,
        unit=ProductUnit.EACH,
        description="Test product description.",
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    return product


def _draft_order(
    *,
    context: PurchasingTestContext,
    supplier: Supplier,
) -> PurchaseOrder:
    """Build a valid draft purchase order."""

    return PurchaseOrder(
        purchase_order_number="PO-TEST-001",
        supplier=supplier,
        supplier_number_snapshot=(supplier.supplier_number or ""),
        supplier_code_snapshot=supplier.code,
        supplier_name_snapshot=supplier.name,
        status=PurchaseOrderStatus.DRAFT,
        currency="ugx",
        discount_percentage=Decimal("5.00"),
        tax_percentage=Decimal("18.00"),
        delivery_cost=Decimal("2500.00"),
        created_by=context.manager,
        updated_by=context.manager,
    )


@pytest.mark.django_db
def test_valid_draft_purchase_order_normalizes_fields(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Validate and normalize a draft order."""

    supplier = _create_supplier(context=purchasing_context)
    order = _draft_order(
        context=purchasing_context,
        supplier=supplier,
    )
    order.supplier_reference = "  SUP-REF-100  "
    order.notes = "  Deliver to the main store.  "

    order.full_clean()
    order.save()

    assert order.currency == "UGX"
    assert order.supplier_reference == "SUP-REF-100"
    assert order.notes == "Deliver to the main store."


@pytest.mark.django_db
def test_purchase_order_rejects_invalid_currency(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require a three-letter purchase currency."""

    supplier = _create_supplier(context=purchasing_context)
    order = _draft_order(
        context=purchasing_context,
        supplier=supplier,
    )
    order.currency = "UGANDA"

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert "currency" in exc_info.value.message_dict


@pytest.mark.django_db
def test_submitted_order_requires_submission_metadata(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require actor and time for submitted status."""

    supplier = _create_supplier(context=purchasing_context)
    order = _draft_order(
        context=purchasing_context,
        supplier=supplier,
    )
    order.status = PurchaseOrderStatus.SUBMITTED

    with pytest.raises(ValidationError) as exc_info:
        order.full_clean()

    assert "submitted_at" in (exc_info.value.message_dict)

    order.submitted_at = timezone.now()
    order.submitted_by = purchasing_context.manager
    order.full_clean()


@pytest.mark.django_db
def test_purchase_order_line_calculates_total(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Calculate a supplier product-line total."""

    supplier = _create_supplier(context=purchasing_context)
    product = _create_product(context=purchasing_context)
    order = _draft_order(
        context=purchasing_context,
        supplier=supplier,
    )
    order.full_clean()
    order.save()

    line = PurchaseOrderLine(
        purchase_order=order,
        product=product,
        position=1,
        product_sku_snapshot=product.sku,
        product_name_snapshot=product.name,
        unit_snapshot=product.unit,
        description_snapshot=product.description,
        quantity_ordered=Decimal("3.000"),
        unit_cost=Decimal("25000.00"),
        created_by=purchasing_context.manager,
        updated_by=purchasing_context.manager,
    )
    line.full_clean()
    line.save()

    assert line.line_total == Decimal("75000.00")
    assert order.totals.line_subtotal == Decimal("75000.00")


@pytest.mark.django_db
def test_non_draft_order_rejects_line_changes(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent line editing after order submission."""

    supplier = _create_supplier(context=purchasing_context)
    product = _create_product(context=purchasing_context)
    order = _draft_order(
        context=purchasing_context,
        supplier=supplier,
    )
    order.status = PurchaseOrderStatus.SUBMITTED
    order.submitted_at = timezone.now()
    order.submitted_by = purchasing_context.manager
    order.full_clean()
    order.save()

    line = PurchaseOrderLine(
        purchase_order=order,
        product=product,
        position=1,
        product_sku_snapshot=product.sku,
        product_name_snapshot=product.name,
        unit_snapshot=product.unit,
        description_snapshot="",
        quantity_ordered=Decimal("1.000"),
        unit_cost=Decimal("25000.00"),
        created_by=purchasing_context.manager,
    )

    with pytest.raises(ValidationError) as exc_info:
        line.full_clean()

    assert "purchase_order" in (exc_info.value.message_dict)
