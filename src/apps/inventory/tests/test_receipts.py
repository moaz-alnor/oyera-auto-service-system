"""Tests for receiving physical inventory stock."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.constants import StockMovementType
from apps.inventory.models import StockMovement
from apps.inventory.selectors import get_on_hand_quantity
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.tests.conftest import (
    InventoryTestContext,
)


@pytest.mark.django_db
def test_manager_receives_stock(
    inventory_context: InventoryTestContext,
) -> None:
    """Create a positive append-only stock movement."""

    movement = receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("10.000"),
            unit_cost=Decimal("15000.00"),
            external_reference="SUP-INV-001",
            notes="Opening stock receipt.",
        ),
    )

    assert movement.movement_number == "MOV-000001"
    assert movement.movement_type == StockMovementType.RECEIPT
    assert movement.quantity == Decimal("10.000")
    assert movement.signed_quantity == Decimal("10.000")
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("10.000")


@pytest.mark.django_db
def test_multiple_receipts_accumulate_balance(
    inventory_context: InventoryTestContext,
) -> None:
    """Calculate stock from all positive ledger entries."""

    first = receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("10.000"),
        ),
    )
    second = receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("5.500"),
        ),
    )

    assert first.movement_number == "MOV-000001"
    assert second.movement_number == "MOV-000002"
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("15.500")
    assert StockMovement.objects.count() == 2


@pytest.mark.django_db
def test_technician_cannot_receive_stock(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent ordinary technicians from receiving inventory."""

    with pytest.raises(PermissionDenied):
        receive_stock(
            actor=inventory_context.technician,
            command=ReceiveStockCommand(
                inventory_item_id=(inventory_context.inventory_item.pk),
                quantity=Decimal("2.000"),
            ),
        )

    assert not StockMovement.objects.exists()


@pytest.mark.django_db
def test_stock_cannot_be_received_into_inactive_item(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject receipts into inactive inventory records."""

    inventory_context.inventory_item.is_active = False
    inventory_context.inventory_item.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    with pytest.raises(
        ValidationError,
        match="inactive inventory item",
    ):
        receive_stock(
            actor=inventory_context.manager,
            command=ReceiveStockCommand(
                inventory_item_id=(inventory_context.inventory_item.pk),
                quantity=Decimal("2.000"),
            ),
        )

    assert not StockMovement.objects.exists()
