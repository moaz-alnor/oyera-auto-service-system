"""Tests for goods-receipt browser views."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

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
from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.models import (
    GoodsReceipt,
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


def _create_receivable_context(
    *,
    context: PurchasingTestContext,
    approve: bool = True,
):
    """Create an order, line and inventory target."""

    category = ProductCategory(
        code="GR-VIEW-CATEGORY",
        name="Goods Receipt View Category",
        created_by=context.manager,
        updated_by=context.manager,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku="GR-VIEW-001",
        name="Goods Receipt View Product",
        category=category,
        unit=ProductUnit.EACH,
        description="Goods-receipt view product.",
        is_active=True,
        created_by=context.manager,
        updated_by=context.manager,
    )
    product.full_clean()
    product.save()

    location = StockLocation(
        code="GR-VIEW-STORE",
        name="Goods Receipt View Store",
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
            code="GR-VIEW-SUPPLIER",
            name="Goods Receipt View Supplier",
            preferred_currency="UGX",
        ),
    )

    purchase_order = create_purchase_order(
        actor=context.manager,
        command=CreatePurchaseOrderCommand(
            supplier_id=supplier.pk,
            currency="UGX",
            supplier_reference="GR-VIEW-PO",
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

    if approve:
        submit_purchase_order(
            actor=context.manager,
            purchase_order_id=(purchase_order.pk),
        )
        purchase_order = approve_purchase_order(
            actor=context.manager,
            purchase_order_id=(purchase_order.pk),
        )

    return (
        purchase_order,
        purchase_order_line,
        inventory_item,
    )


def _receipt_post_data(
    *,
    purchase_order_line_id: int,
    inventory_item_id: int,
    receive: bool = True,
) -> dict[str, str]:
    """Return one goods-receipt browser submission."""

    data = {
        "supplier_delivery_reference": ("DELIVERY-VIEW-001"),
        "received_at": "",
        "notes": "Browser goods receipt.",
        "lines-TOTAL_FORMS": "1",
        "lines-INITIAL_FORMS": "1",
        "lines-MIN_NUM_FORMS": "0",
        "lines-MAX_NUM_FORMS": "100",
        ("lines-0-purchase_order_line_id"): str(purchase_order_line_id),
        "lines-0-inventory_item": str(inventory_item_id),
        "lines-0-quantity_received": "4.000",
    }

    if receive:
        data["lines-0-receive"] = "on"

    return data


def test_goods_receipt_urls_reverse() -> None:
    """Reverse list, create and detail routes."""

    assert reverse("purchasing:goods_receipt_list") == "/purchasing/goods-receipts/"

    assert reverse(
        "purchasing:goods_receipt_create",
        args=(1,),
    ) == ("/purchasing/purchase-orders/1/receipts/new/")

    assert reverse(
        "purchasing:goods_receipt_detail",
        args=(1,),
    ) == ("/purchasing/goods-receipts/1/")


def test_anonymous_user_is_redirected_from_receipts(
    client: Client,
) -> None:
    """Require authentication for receipt records."""

    response = client.get(reverse("purchasing:goods_receipt_list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


def test_receptionist_can_view_receipt_list_and_detail(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Allow read-only receipt access."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    list_response = client.get(reverse("purchasing:goods_receipt_list"))
    detail_response = client.get(
        reverse(
            "purchasing:goods_receipt_detail",
            args=(context.goods_receipt.pk,),
        )
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert list(list_response.context["goods_receipts"]) == [context.goods_receipt]
    assert detail_response.context["goods_receipt"] == context.goods_receipt
    assert list(detail_response.context["goods_receipt_lines"]) == [
        context.goods_receipt_line
    ]
    assert list(detail_response.context["stock_movements"]) == [context.stock_movement]


def test_manager_opens_goods_receipt_form(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Display outstanding order lines."""

    (
        purchase_order,
        purchase_order_line,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        )
    )

    formset = response.context["line_formset"]

    assert response.status_code == 200
    assert response.context["purchase_order"] == purchase_order
    assert formset.total_form_count() == 1
    assert formset.forms[0].initial["purchase_order_line_id"] == purchase_order_line.pk
    assert list(formset.forms[0].fields["inventory_item"].queryset) == [inventory_item]


def test_manager_records_partial_goods_receipt(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Post a supplier delivery into Inventory."""

    (
        purchase_order,
        purchase_order_line,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        ),
        _receipt_post_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
        ),
    )

    goods_receipt = GoodsReceipt.objects.get(purchase_order=purchase_order)
    goods_receipt_line = goods_receipt.lines.get()

    purchase_order.refresh_from_db()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "purchasing:goods_receipt_detail",
        args=(goods_receipt.pk,),
    )
    assert goods_receipt.goods_receipt_number == (f"GRN-{goods_receipt.pk:06d}")
    assert goods_receipt.supplier_delivery_reference == ("DELIVERY-VIEW-001")
    assert goods_receipt_line.quantity_received == (Decimal("4.000"))
    assert goods_receipt_line.inventory_item == (inventory_item)
    assert goods_receipt_line.stock_movement.quantity == (Decimal("4.000"))
    assert purchase_order.status == (PurchaseOrderStatus.PARTIALLY_RECEIVED)


def test_goods_receipt_requires_selected_line(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject an empty supplier delivery."""

    (
        purchase_order,
        purchase_order_line,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        ),
        _receipt_post_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
            receive=False,
        ),
    )

    assert response.status_code == 200
    assert (
        "Select at least one delivered product."
        in response.context["line_formset"].non_form_errors()
    )
    assert not GoodsReceipt.objects.exists()


def test_draft_purchase_order_cannot_be_received(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Reject receipt posting before approval."""

    (
        purchase_order,
        purchase_order_line,
        inventory_item,
    ) = _create_receivable_context(
        context=purchasing_context,
        approve=False,
    )

    client.force_login(purchasing_context.manager)

    response = client.post(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        ),
        _receipt_post_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
        ),
    )

    assert response.status_code == 200
    assert not GoodsReceipt.objects.exists()
    assert "Only an approved or partially received" in " ".join(
        response.context["header_form"].non_field_errors()
    )


def test_receptionist_cannot_create_goods_receipt(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Keep receipt posting under management."""

    (
        purchase_order,
        purchase_order_line,
        inventory_item,
    ) = _create_receivable_context(context=purchasing_context)

    client.force_login(purchasing_context.receptionist)

    response = client.post(
        reverse(
            "purchasing:goods_receipt_create",
            args=(purchase_order.pk,),
        ),
        _receipt_post_data(
            purchase_order_line_id=(purchase_order_line.pk),
            inventory_item_id=(inventory_item.pk),
        ),
    )

    assert response.status_code == 403
    assert not GoodsReceipt.objects.exists()


def test_goods_receipt_list_applies_filters(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Apply query, order and supplier filters."""

    context = create_posted_receipt(context=purchasing_context)

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse("purchasing:goods_receipt_list"),
        {
            "q": (context.goods_receipt.goods_receipt_number),
            "purchase_order": (context.purchase_order.pk),
            "supplier": (context.purchase_order.supplier_id),
        },
    )

    assert response.status_code == 200
    assert list(response.context["goods_receipts"]) == [context.goods_receipt]
    assert response.context["selected_purchase_order_id"] == context.purchase_order.pk
    assert (
        response.context["selected_supplier_id"] == context.purchase_order.supplier_id
    )


def test_missing_goods_receipt_returns_404(
    client: Client,
    purchasing_context: PurchasingTestContext,
) -> None:
    """Return HTTP 404 for an unknown receipt."""

    client.force_login(purchasing_context.manager)

    response = client.get(
        reverse(
            "purchasing:goods_receipt_detail",
            args=(999999,),
        )
    )

    assert response.status_code == 404
