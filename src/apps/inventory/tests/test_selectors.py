"""Tests for calculated inventory balances."""

from decimal import Decimal

import pytest

from apps.inventory.selectors import (
    get_inventory_balance,
    get_low_stock_items,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.tests.conftest import InventoryTestContext


@pytest.mark.django_db
def test_inventory_balance_starts_at_zero(
    inventory_context: InventoryTestContext,
) -> None:
    """Return zero balances when the ledger is empty."""

    balance = get_inventory_balance(
        inventory_item_id=(inventory_context.inventory_item.pk)
    )

    assert balance.on_hand_quantity == Decimal("0.000")
    assert balance.reserved_quantity == Decimal("0.000")
    assert balance.available_quantity == Decimal("0.000")
    assert balance.is_low_stock


@pytest.mark.django_db
def test_low_stock_selector_uses_available_quantity(
    inventory_context: InventoryTestContext,
) -> None:
    """Exclude an item once stock exceeds its reorder level."""

    assert [balance.inventory_item for balance in get_low_stock_items()] == [
        inventory_context.inventory_item
    ]

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("6.000"),
        ),
    )

    assert get_low_stock_items() == []
