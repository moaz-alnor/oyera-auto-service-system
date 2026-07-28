"""Factories shared by goods-receipt tests."""

from dataclasses import dataclass
from decimal import Decimal

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
from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
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


@dataclass(frozen=True, slots=True)
class PostedReceiptContext:
    """Contain one posted supplier delivery."""

    purchase_order: PurchaseOrder
    purchase_order_line: PurchaseOrderLine
    inventory_item: InventoryItem
    goods_receipt: GoodsReceipt
    goods_receipt_line: GoodsReceiptLine
    stock_movement: StockMovement
    product: Product


def create_posted_receipt(
    *,
    context: PurchasingTestContext,
    quantity_received: Decimal = Decimal("4.000"),
) -> PostedReceiptContext:
    """Create one approved order and post a delivery."""

    category = ProductCategory(
        code="RECEIPT-AUDIT",
        name="Receipt Audit Products",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="AUDIT-PART-001",
        name="Audit Brake Pad",
        category=category,
        unit=ProductUnit.EACH,
        description="Goods-receipt audit product.",
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    location = StockLocation(
        code="AUDIT-STORE",
        name="Audit Parts Store",
        created_by=context.manager,
        updated_by=context.manager,
    )
    location.full_clean()
    location.save()

    inventory_item = InventoryItem(
        product=product,
        location=location,
        reorder_level=Decimal("0.000"),
        created_by=context.manager,
        updated_by=context.manager,
    )
    inventory_item.full_clean()
    inventory_item.save()

    supplier = register_supplier(
        actor=context.manager,
        command=RegisterSupplierCommand(
            code="AUDIT-SUPPLIER",
            name="Audit Parts Supplier",
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            supplier_reference="SUP-AUDIT-100",
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

    goods_receipt = receive_purchase_order(
        actor=context.manager,
        command=ReceivePurchaseOrderCommand(
            purchase_order_id=purchase_order.pk,
            lines=(
                GoodsReceiptLineCommand(
                    purchase_order_line_id=(purchase_order_line.pk),
                    inventory_item_id=(inventory_item.pk),
                    quantity_received=(quantity_received),
                ),
            ),
            supplier_delivery_reference=("DELIVERY-AUDIT-100"),
            notes="Selector and audit test delivery.",
        ),
    )

    goods_receipt_line = GoodsReceiptLine.objects.select_related("stock_movement").get(
        goods_receipt=goods_receipt
    )

    return PostedReceiptContext(
        purchase_order=purchase_order,
        purchase_order_line=purchase_order_line,
        inventory_item=inventory_item,
        goods_receipt=goods_receipt,
        goods_receipt_line=goods_receipt_line,
        stock_movement=(goods_receipt_line.stock_movement),
        product=product,
    )
