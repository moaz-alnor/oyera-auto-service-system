"""Tests for Purchasing-to-Inventory audit integrity."""

from decimal import Decimal

import pytest

from apps.inventory.constants import StockMovementType
from apps.purchasing.selectors import (
    get_goods_receipt_movements,
)
from apps.purchasing.tests.conftest import (
    PurchasingTestContext,
)
from apps.purchasing.tests.receipt_factory import (
    create_posted_receipt,
)


@pytest.mark.django_db
def test_receipt_preserves_inventory_ledger_reference(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Link the supplier receipt to its stock movement."""

    context = create_posted_receipt(context=purchasing_context)
    movement = context.stock_movement

    assert movement.movement_type == (StockMovementType.RECEIPT)
    assert movement.inventory_item == (context.inventory_item)
    assert movement.quantity == Decimal("4.000")
    assert movement.unit_cost == Decimal("25000.00")
    assert movement.currency == "UGX"
    assert context.purchase_order.purchase_order_number in movement.external_reference
    assert context.goods_receipt.goods_receipt_number in movement.external_reference
    assert context.goods_receipt_line.stock_movement == (movement)


@pytest.mark.django_db
def test_receipt_movements_form_positive_inventory_audit(
    purchasing_context: PurchasingTestContext,
) -> None:
    """Expose the complete positive receipt ledger."""

    context = create_posted_receipt(context=purchasing_context)

    movements = list(
        get_goods_receipt_movements(goods_receipt_id=(context.goods_receipt.pk))
    )

    assert len(movements) == 1
    assert sum(
        (movement.signed_quantity for movement in movements),
        Decimal("0.000"),
    ) == Decimal("4.000")
    assert movements[0].created_by == (purchasing_context.manager)
