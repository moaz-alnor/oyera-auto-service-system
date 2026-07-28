"""Tests for controlled inventory adjustments."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.constants import StockMovementType
from apps.inventory.models import StockMovement
from apps.inventory.selectors import get_on_hand_quantity
from apps.inventory.services.adjustments import (
    AdjustStockCommand,
    adjust_stock,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.tests.conftest import InventoryTestContext


@pytest.mark.django_db
def test_manager_records_positive_adjustment(
    inventory_context: InventoryTestContext,
) -> None:
    """Increase stock through an auditable adjustment."""

    movement = adjust_stock(
        actor=inventory_context.manager,
        command=AdjustStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            movement_type=(StockMovementType.ADJUSTMENT_IN),
            quantity=Decimal("3.000"),
            reason="Opening count correction.",
        ),
    )

    assert movement.movement_number == (f"MOV-{movement.pk:06d}")
    assert movement.movement_type == StockMovementType.ADJUSTMENT_IN
    assert movement.signed_quantity == Decimal("3.000")
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("3.000")


@pytest.mark.django_db
def test_manager_records_negative_adjustment(
    inventory_context: InventoryTestContext,
) -> None:
    """Decrease physical stock without editing a balance."""

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("5.000"),
        ),
    )

    movement = adjust_stock(
        actor=inventory_context.manager,
        command=AdjustStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            movement_type=(StockMovementType.ADJUSTMENT_OUT),
            quantity=Decimal("2.000"),
            reason="Two damaged filters removed.",
        ),
    )

    assert movement.movement_number == (f"MOV-{movement.pk:06d}")
    assert movement.signed_quantity == Decimal("-2.000")
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("3.000")


@pytest.mark.django_db
def test_negative_adjustment_cannot_overdraw_stock(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent adjustments from producing negative stock."""

    with pytest.raises(
        ValidationError,
        match="below zero",
    ):
        adjust_stock(
            actor=inventory_context.manager,
            command=AdjustStockCommand(
                inventory_item_id=(inventory_context.inventory_item.pk),
                movement_type=(StockMovementType.ADJUSTMENT_OUT),
                quantity=Decimal("1.000"),
                reason="Invalid count correction.",
            ),
        )

    assert not StockMovement.objects.exists()


@pytest.mark.django_db
def test_adjustment_requires_reason(
    inventory_context: InventoryTestContext,
) -> None:
    """Require an explanation for every stock correction."""

    with pytest.raises(
        ValidationError,
        match="Record why",
    ):
        adjust_stock(
            actor=inventory_context.manager,
            command=AdjustStockCommand(
                inventory_item_id=(inventory_context.inventory_item.pk),
                movement_type=(StockMovementType.ADJUSTMENT_IN),
                quantity=Decimal("1.000"),
                reason="   ",
            ),
        )


@pytest.mark.django_db
def test_technician_cannot_adjust_stock(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent ordinary technicians from correcting balances."""

    with pytest.raises(PermissionDenied):
        adjust_stock(
            actor=inventory_context.technician,
            command=AdjustStockCommand(
                inventory_item_id=(inventory_context.inventory_item.pk),
                movement_type=(StockMovementType.ADJUSTMENT_IN),
                quantity=Decimal("1.000"),
                reason="Unauthorised adjustment.",
            ),
        )

    assert not StockMovement.objects.exists()
