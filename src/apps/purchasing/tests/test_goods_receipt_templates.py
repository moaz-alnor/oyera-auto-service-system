"""Tests for goods-receipt templates and navigation."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.inventory.models import (
    InventoryItem,
    StockLocation,
)
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CreatePurchaseOrderCommand,
    add_purchase_order_line,
    approve_purchase_order,
    create_purchase_order,
    submit_purchase_order,
)
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    register_supplier,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    create_posted_receipt,
)

pytestmark = pytest.mark.django_db


def _create_approved_order(
    *,
    context: PurchasingTestContext,
):
    """Create one approved order awaiting delivery."""

    category = ProductCategory(
        code="GR-TEMPLATE-CATEGORY",
        name="Goods Receipt Template Category",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="GR-TEMPLATE-001",
        name="Goods Receipt Template Product",
        category=category,
        unit=ProductUnit.EACH,
        description="Template receipt product.",
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    location = StockLocation(
        code="GR-TEMPLATE-STORE",
        name="Goods Receipt Template Store",
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
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    inventory_item.full_clean()
    inventory_item.save()

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="GR-TEMPLATE-SUPPLIER",
            name="Goods Receipt Template Supplier",
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
            supplier_reference="GR-TEMPLATE-PO",
        ),
    )

    purchase_order_line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("10.000"),
            unit_cost=Decimal("25000.00"),
        ),
    )

    submit_purchase_order(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
    )
    purchase_order = approve_purchase_order(
        actor=context.manager,
        purchase_order_id=purchase_order.pk,
    )

    return (
        purchase_order,
        purchase_order_line,
        product,
        inventory_item,
    )


def test_goods_receipt_list_displays_delivery(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display receipt, order and supplier evidence."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:goods_receipt_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert context.goods_receipt.goods_receipt_number in content
    assert context.purchase_order.purchase_order_number in content
    assert context.goods_receipt.supplier_name_snapshot in content
    assert "DELIVERY-AUDIT-100" in content
    assert "Purchase orders" in content
    assert "Inventory" in content


def test_goods_receipt_form_displays_delivery_controls(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display delivery header and line controls."""

    (
        purchase_order,
        purchase_order_line,
        product,
        inventory_item,
    ) = _create_approved_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Receive supplier delivery" in content
    assert 'name="supplier_delivery_reference"' in content
    assert 'name="received_at"' in content
    assert 'name="notes"' in content
    assert 'name="lines-TOTAL_FORMS"' in content
    assert 'name="lines-0-receive"' in content
    assert 'name="lines-0-inventory_item"' in content
    assert 'name="lines-0-quantity_received"' in content
    assert product.sku in content
    assert product.name in content
    assert inventory_item.location.name in content
    assert str(purchase_order_line.pk) in content
    assert "Post goods receipt" in content


def test_goods_receipt_detail_displays_inventory_audit(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display receipt lines and linked movement."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    response = client.get(
        reverse(
            "purchasing:goods_receipt_detail",
            args=(context.goods_receipt.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert context.goods_receipt.goods_receipt_number in content
    assert context.product.sku in content
    assert context.product.name in content
    assert "4.000" in content
    assert "UGX" in content
    assert context.inventory_item.location.code in content
    assert context.inventory_item.location.name in content
    assert context.stock_movement.movement_number in content
    assert "Inventory movement audit" in content
    assert (
        reverse(
            "inventory:detail",
            args=(context.inventory_item.pk,),
        )
        in content
    )


def test_purchase_order_list_links_goods_receipts(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Expose receipt navigation from purchase orders."""

    client.force_login(purchasing_context.manager)

    response = client.get(reverse("purchasing:purchase_order_list"))

    content = response.content.decode()

    assert response.status_code == 200
    assert "Goods receipts" in content
    assert reverse("purchasing:goods_receipt_list") in content


def test_approved_order_displays_receive_action(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Offer receipt posting on an approved order."""

    (
        purchase_order,
        _purchase_order_line,
        _product,
        _inventory_item,
    ) = _create_approved_order(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Receive delivery" in content
    assert "Receive first delivery" in content
    assert (
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        )
        in content
    )


def test_partial_order_displays_receipt_history(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display previous delivery and another receipt action."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(context.purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Goods receipts" in content
    assert context.goods_receipt.goods_receipt_number in content
    assert (
        reverse(
            "purchasing:goods_receipt_detail",
            args=(context.goods_receipt.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:goods_receipt_create",
            args=(context.purchase_order.pk,),
        )
        in content
    )


def test_fully_received_order_hides_receive_action(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Hide further delivery posting after completion."""

    context = create_posted_receipt(
        context=purchasing_context,
        quantity_received=Decimal("10.000"),
    )

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(context.purchase_order.pk,),
        )
    )

    content = response.content.decode()
    create_url = reverse(
        "purchasing:goods_receipt_create",
        args=(context.purchase_order.pk,),
    )

    assert response.status_code == 200
    assert context.goods_receipt.goods_receipt_number in content
    assert create_url not in content
    assert "Receive delivery" not in content


def test_receptionist_sees_history_without_receive_action(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep receiving controls under management."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    response = client.get(
        reverse(
            "purchasing:purchase_order_detail",
            args=(context.purchase_order.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert context.goods_receipt.goods_receipt_number in content
    assert (
        reverse(
            "purchasing:goods_receipt_detail",
            args=(context.goods_receipt.pk,),
        )
        in content
    )
    assert (
        reverse(
            "purchasing:goods_receipt_create",
            args=(context.purchase_order.pk,),
        )
        not in content
    )
    assert "Receive delivery" not in content
