"""Tests for purchase-order goods receipts."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
)
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
    GoodsReceipt,
    GoodsReceiptLine,
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


def _create_product(
    *,
    context: PurchasingTestContext,
    sku: str = "RECEIPT-PART-001",
) -> Product:
    """Create one active purchasing product."""

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
        description="Goods receipt test product.",
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
    location_code: str = "RECEIPT-STORE",
) -> InventoryItem:
    """Create an inventory target for a product."""

    location = StockLocation(
        code=location_code,
        name=f"{location_code} Location",
        created_by=context.manager,
        updated_by=context.manager,
    )
    location.full_clean()
    location.save()

    item = InventoryItem(
        product=product,
        location=location,
        reorder_level=Decimal("0.000"),
        created_by=context.manager,
        updated_by=context.manager,
    )
    item.full_clean()
    item.save()

    return item


def _approved_order(
    *,
    context: PurchasingTestContext,
    product: Product,
    quantity: Decimal = Decimal("10.000"),
):
    """Create an approved purchase order and line."""

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="RECEIPT-SUPPLIER",
            name="Goods Receipt Supplier",
            preferred_currency="UGX",
        ),
    )

    order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
        ),
    )

    line = add_purchase_order_line(
        actor=context.manager,
        purchase_order_id=order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=quantity,
            unit_cost=Decimal("25000.00"),
        ),
    )

    submit_purchase_order(
        actor=context.manager,
        purchase_order_id=order.pk,
    )

    order = approve_purchase_order(
        actor=context.manager,
        purchase_order_id=order.pk,
    )

    return order, line


def _receive(
    *,
    context: PurchasingTestContext,
    order_id: int,
    line_id: int,
    inventory_item_id: int,
    quantity: Decimal,
):
    """Post one standard supplier delivery."""

    return receive_purchase_order(
        actor=context.manager,
        command=ReceivePurchaseOrderCommand(
            purchase_order_id=order_id,
            lines=(
                GoodsReceiptLineCommand(
                    purchase_order_line_id=line_id,
                    inventory_item_id=inventory_item_id,
                    quantity_received=quantity,
                ),
            ),
            supplier_delivery_reference=("DELIVERY-1001"),
            notes="Goods received in good condition.",
        ),
    )


@pytest.mark.django_db
def test_manager_partially_receives_purchase_order(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Create a partial goods receipt and stock movement."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=product,
    )

    receipt = _receive(
        context=purchasing_context,
        order_id=order.pk,
        line_id=line.pk,
        inventory_item_id=inventory_item.pk,
        quantity=Decimal("4.000"),
    )

    order.refresh_from_db()
    line.refresh_from_db()

    receipt_line = receipt.lines.get()

    assert receipt.goods_receipt_number == ("GRN-000001")
    assert order.status == (PurchaseOrderStatus.PARTIALLY_RECEIVED)
    assert receipt_line.quantity_received == Decimal("4.000")
    assert receipt_line.stock_movement.quantity == Decimal("4.000")
    assert receipt_line.stock_movement.unit_cost == Decimal("25000.00")
    assert receipt_line.stock_movement.currency == "UGX"
    assert line.quantity_received == Decimal("4.000")
    assert line.remaining_quantity == Decimal("6.000")


@pytest.mark.django_db
def test_second_receipt_completes_purchase_order(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Complete the outstanding quantity in another receipt."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=product,
    )

    _receive(
        context=purchasing_context,
        order_id=order.pk,
        line_id=line.pk,
        inventory_item_id=inventory_item.pk,
        quantity=Decimal("4.000"),
    )

    _receive(
        context=purchasing_context,
        order_id=order.pk,
        line_id=line.pk,
        inventory_item_id=inventory_item.pk,
        quantity=Decimal("6.000"),
    )

    order.refresh_from_db()
    line.refresh_from_db()

    assert order.status == PurchaseOrderStatus.RECEIVED
    assert line.quantity_received == Decimal("10.000")
    assert line.remaining_quantity == Decimal("0.000")
    assert GoodsReceipt.objects.count() == 2
    assert StockMovement.objects.count() == 2


@pytest.mark.django_db
def test_over_receipt_is_rejected_without_movement(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Prevent receiving more than the ordered quantity."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=product,
    )

    _receive(
        context=purchasing_context,
        order_id=order.pk,
        line_id=line.pk,
        inventory_item_id=inventory_item.pk,
        quantity=Decimal("8.000"),
    )

    receipt_count = GoodsReceipt.objects.count()
    movement_count = StockMovement.objects.count()

    with pytest.raises(ValidationError) as exc_info:
        _receive(
            context=purchasing_context,
            order_id=order.pk,
            line_id=line.pk,
            inventory_item_id=inventory_item.pk,
            quantity=Decimal("3.000"),
        )

    assert "quantity_received" in (exc_info.value.message_dict)
    assert GoodsReceipt.objects.count() == receipt_count
    assert StockMovement.objects.count() == movement_count


@pytest.mark.django_db
def test_receptionist_cannot_receive_purchase_order(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject supplier receiving without authority."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=product,
    )

    with pytest.raises(PermissionDenied):
        receive_purchase_order(
            actor=purchasing_context.receptionist,
            command=ReceivePurchaseOrderCommand(
                purchase_order_id=order.pk,
                lines=(
                    GoodsReceiptLineCommand(
                        purchase_order_line_id=line.pk,
                        inventory_item_id=(inventory_item.pk),
                        quantity_received=Decimal("1.000"),
                    ),
                ),
            ),
        )


@pytest.mark.django_db
def test_draft_purchase_order_cannot_be_received(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Require approval before supplier delivery."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    supplier = register_supplier(
        actor=purchasing_context.manager,
        command=RegisterSupplierCommand(
            code="DRAFT-RECEIPT-SUPPLIER",
            name="Draft Receipt Supplier",
        ),
    )
    order = create_purchase_order(
        actor=purchasing_context.manager,
        command=CreatePurchaseOrderCommand(supplier_id=supplier.pk),
    )
    line = add_purchase_order_line(
        actor=purchasing_context.manager,
        purchase_order_id=order.pk,
        command=AddPurchaseOrderLineCommand(
            product_id=product.pk,
            quantity_ordered=Decimal("2.000"),
            unit_cost=Decimal("25000.00"),
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        _receive(
            context=purchasing_context,
            order_id=order.pk,
            line_id=line.pk,
            inventory_item_id=inventory_item.pk,
            quantity=Decimal("1.000"),
        )

    assert "purchase_order" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_inventory_product_must_match_order_line(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject receiving into another product's stock item."""

    ordered_product = _create_product(
        context=purchasing_context,
        sku="ORDERED-PART-001",
    )
    different_product = _create_product(
        context=purchasing_context,
        sku="DIFFERENT-PART-001",
    )
    wrong_inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=different_product,
        location_code="WRONG-STORE",
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=ordered_product,
    )

    with pytest.raises(ValidationError) as exc_info:
        _receive(
            context=purchasing_context,
            order_id=order.pk,
            line_id=line.pk,
            inventory_item_id=(wrong_inventory_item.pk),
            quantity=Decimal("1.000"),
        )

    assert "inventory_item" in (exc_info.value.message_dict)
    assert GoodsReceiptLine.objects.count() == 0
    assert StockMovement.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_receipt_line_command_is_rejected(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject the same order line twice in one receipt."""

    product = _create_product(context=purchasing_context)
    inventory_item = _create_inventory_item(
        context=purchasing_context,
        product=product,
    )
    order, line = _approved_order(
        context=purchasing_context,
        product=product,
    )

    duplicated_line = GoodsReceiptLineCommand(
        purchase_order_line_id=line.pk,
        inventory_item_id=inventory_item.pk,
        quantity_received=Decimal("1.000"),
    )

    with pytest.raises(ValidationError) as exc_info:
        receive_purchase_order(
            actor=purchasing_context.manager,
            command=ReceivePurchaseOrderCommand(
                purchase_order_id=order.pk,
                lines=(
                    duplicated_line,
                    duplicated_line,
                ),
            ),
        )

    assert "lines" in exc_info.value.message_dict
    assert GoodsReceipt.objects.count() == 0
    assert StockMovement.objects.count() == 0
