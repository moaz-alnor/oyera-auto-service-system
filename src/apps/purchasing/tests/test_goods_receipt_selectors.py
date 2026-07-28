"""Tests for goods-receipt selectors."""

import pytest

from apps.purchasing.selectors import (
    get_goods_receipt_by_id,
    get_goods_receipt_movements,
    get_goods_receipts_for_purchase_order,
    search_goods_receipts,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    create_posted_receipt,
)


@pytest.mark.django_db
def test_search_goods_receipts_by_identity(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find receipts by receipt and supplier identity."""

    context = create_posted_receipt(context=purchasing_context)

    assert list(
        search_goods_receipts(query=(context.goods_receipt.goods_receipt_number))
    ) == [context.goods_receipt]

    assert list(search_goods_receipts(query="Audit Parts Supplier")) == [
        context.goods_receipt
    ]

    assert list(search_goods_receipts(query="DELIVERY-AUDIT-100")) == [
        context.goods_receipt
    ]


@pytest.mark.django_db
def test_search_goods_receipts_by_product_and_movement(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Find a receipt through product and ledger data."""

    context = create_posted_receipt(context=purchasing_context)

    assert list(search_goods_receipts(query="AUDIT-PART-001")) == [
        context.goods_receipt
    ]

    assert list(
        search_goods_receipts(query=context.stock_movement.movement_number)
    ) == [context.goods_receipt]

    assert list(search_goods_receipts(query="AUDIT-STORE")) == [context.goods_receipt]


@pytest.mark.django_db
def test_filter_receipts_by_order_and_supplier(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Filter receipt records by business parents."""

    context = create_posted_receipt(context=purchasing_context)

    assert list(
        search_goods_receipts(purchase_order_id=(context.purchase_order.pk))
    ) == [context.goods_receipt]

    assert list(
        search_goods_receipts(supplier_id=(context.purchase_order.supplier.pk))
    ) == [context.goods_receipt]

    assert list(
        get_goods_receipts_for_purchase_order(
            purchase_order_id=(context.purchase_order.pk)
        )
    ) == [context.goods_receipt]


@pytest.mark.django_db
def test_goods_receipt_detail_loads_audit_data(
    purchasing_context: PurchasingTestContext,
    django_assert_num_queries,
) -> None:
    """Load receipt header and lines efficiently."""

    context = create_posted_receipt(context=purchasing_context)

    with django_assert_num_queries(2):
        selected = get_goods_receipt_by_id(goods_receipt_id=(context.goods_receipt.pk))
        lines = list(selected.lines.all())

        assert selected.purchase_order == (context.purchase_order)
        assert len(lines) == 1
        assert lines[0].inventory_item.product == (context.product)
        assert lines[0].stock_movement == (context.stock_movement)

    assert list(
        get_goods_receipt_movements(goods_receipt_id=(context.goods_receipt.pk))
    ) == [context.stock_movement]
