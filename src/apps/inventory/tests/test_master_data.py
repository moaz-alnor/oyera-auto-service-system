"""Tests for inventory master-data services."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.models import (
    InventoryItem,
    StockLocation,
)
from apps.inventory.services.master_data import (
    CreateInventoryItemCommand,
    CreateStockLocationCommand,
    create_inventory_item,
    create_stock_location,
)
from apps.inventory.tests.conftest import InventoryTestContext


@pytest.mark.django_db
def test_manager_creates_stock_location(
    inventory_context: InventoryTestContext,
) -> None:
    """Allow a manager to create a physical stock location."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code=" shelf-b / 02 ",
            name="Shelf B 02",
            description="Secondary filter shelf.",
        ),
    )

    assert location.pk is not None
    assert location.normalized_code == "SHELF-B-02"
    assert location.name == "Shelf B 02"
    assert location.is_active
    assert location.created_by == inventory_context.manager
    assert location.updated_by == inventory_context.manager


@pytest.mark.django_db
def test_manager_creates_inventory_item(
    inventory_context: InventoryTestContext,
) -> None:
    """Connect an active product to an active location."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code="SECONDARY-STORE",
            name="Secondary Store",
        ),
    )

    inventory_item = create_inventory_item(
        actor=inventory_context.manager,
        command=CreateInventoryItemCommand(
            product_id=inventory_context.product.pk,
            location_id=location.pk,
            reorder_level=Decimal("3.000"),
            notes="Secondary filter stock.",
        ),
    )

    assert inventory_item.pk is not None
    assert inventory_item.product == inventory_context.product
    assert inventory_item.location == location
    assert inventory_item.reorder_level == Decimal("3.000")
    assert inventory_item.is_active
    assert inventory_item.created_by == inventory_context.manager


@pytest.mark.django_db
def test_technician_cannot_create_stock_location(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from creating storage locations."""

    with pytest.raises(PermissionDenied):
        create_stock_location(
            actor=inventory_context.technician,
            command=CreateStockLocationCommand(
                code="UNAUTHORISED",
                name="Unauthorised Location",
            ),
        )

    assert not StockLocation.objects.filter(normalized_code="UNAUTHORISED").exists()


@pytest.mark.django_db
def test_technician_cannot_create_inventory_item(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from creating inventory records."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code="MANAGER-STORE",
            name="Manager Store",
        ),
    )

    with pytest.raises(PermissionDenied):
        create_inventory_item(
            actor=inventory_context.technician,
            command=CreateInventoryItemCommand(
                product_id=inventory_context.product.pk,
                location_id=location.pk,
            ),
        )

    assert not InventoryItem.objects.filter(
        product=inventory_context.product,
        location=location,
    ).exists()


@pytest.mark.django_db
def test_inventory_item_requires_active_product(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject an inactive catalogue product."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code="ACTIVE-STORE",
            name="Active Store",
        ),
    )

    inventory_context.product.is_active = False
    inventory_context.product.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    with pytest.raises(
        ValidationError,
        match="active catalogue product",
    ):
        create_inventory_item(
            actor=inventory_context.manager,
            command=CreateInventoryItemCommand(
                product_id=inventory_context.product.pk,
                location_id=location.pk,
            ),
        )


@pytest.mark.django_db
def test_inventory_item_requires_active_location(
    inventory_context: InventoryTestContext,
) -> None:
    """Reject an inactive physical stock location."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code="OLD-LOCATION",
            name="Old Location",
        ),
    )
    location.is_active = False
    location.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    with pytest.raises(
        ValidationError,
        match="active stock location",
    ):
        create_inventory_item(
            actor=inventory_context.manager,
            command=CreateInventoryItemCommand(
                product_id=inventory_context.product.pk,
                location_id=location.pk,
            ),
        )


@pytest.mark.django_db
def test_duplicate_product_location_is_rejected(
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent duplicate inventory records."""

    with pytest.raises(
        ValidationError,
        match="already exists",
    ):
        create_inventory_item(
            actor=inventory_context.manager,
            command=CreateInventoryItemCommand(
                product_id=inventory_context.product.pk,
                location_id=inventory_context.location.pk,
                reorder_level=Decimal("2.000"),
            ),
        )

    assert (
        InventoryItem.objects.filter(
            product=inventory_context.product,
            location=inventory_context.location,
        ).count()
        == 1
    )
