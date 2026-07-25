"""Tests for inventory model validation and balances."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.inventory.constants import StockMovementType
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
)
from apps.inventory.tests.conftest import (
    InventoryTestContext,
)


@pytest.mark.django_db
def test_location_code_is_normalized(
    inventory_context: InventoryTestContext,
) -> None:
    """Create a stable storage-location identifier."""

    location = StockLocation(
        code="  shelf a / 01  ",
        name="Shelf A 01",
        created_by=inventory_context.manager,
        updated_by=inventory_context.manager,
    )
    location.full_clean()

    assert location.normalized_code == "SHELF-A-01"


@pytest.mark.django_db
def test_reorder_level_cannot_be_negative(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject an invalid negative reorder level."""

    item = InventoryItem(
        product=inventory_context.product,
        location=inventory_context.location,
        reorder_level=Decimal("-1.000"),
        created_by=inventory_context.manager,
        updated_by=inventory_context.manager,
    )

    with pytest.raises(
        ValidationError,
        match="cannot be negative",
    ):
        item.full_clean()


@pytest.mark.django_db
def test_stock_movement_returns_signed_quantity(
    inventory_context: InventoryTestContext,
) -> None:
    """Apply positive and negative ledger directions."""

    receipt = StockMovement(
        movement_number="MOV-TEST-001",
        inventory_item=inventory_context.inventory_item,
        movement_type=StockMovementType.RECEIPT,
        quantity=Decimal("10.000"),
        created_by=inventory_context.manager,
    )
    issue = StockMovement(
        movement_number="MOV-TEST-002",
        inventory_item=inventory_context.inventory_item,
        movement_type=StockMovementType.ADJUSTMENT_OUT,
        quantity=Decimal("3.000"),
        notes="Test negative movement.",
        created_by=inventory_context.manager,
    )

    receipt.full_clean()
    issue.full_clean()

    assert receipt.signed_quantity == Decimal("10.000")
    assert issue.signed_quantity == Decimal("-3.000")


@pytest.mark.django_db
def test_workshop_issue_requires_reservation(
    inventory_context: InventoryTestContext,
) -> None:
    """Require traceability for stock issued to workshop."""

    movement = StockMovement(
        movement_number="MOV-TEST-003",
        inventory_item=inventory_context.inventory_item,
        movement_type=StockMovementType.ISSUE,
        quantity=Decimal("1.000"),
        created_by=inventory_context.manager,
    )

    with pytest.raises(
        ValidationError,
        match="must reference a stock reservation",
    ):
        movement.full_clean()
