"""Tests for inventory browser workflows."""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.inventory.constants import StockMovementType
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
)
from apps.inventory.selectors import get_on_hand_quantity
from apps.inventory.services.master_data import (
    CreateStockLocationCommand,
    create_stock_location,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.tests.conftest import InventoryTestContext


@pytest.mark.django_db
def test_inventory_list_requires_authentication(
    client,
) -> None:
    """Redirect anonymous users to employee login."""

    response = client.get(reverse("inventory:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in (response.headers["Location"])


@pytest.mark.django_db
def test_technician_can_view_inventory_list(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Allow technicians to inspect inventory balances."""

    client.force_login(inventory_context.technician)

    response = client.get(reverse("inventory:list"))

    assert response.status_code == 200
    assert list(response.context["balances"])


@pytest.mark.django_db
def test_inventory_list_shows_calculated_balance(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Expose physical and available stock calculations."""

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("8.000"),
        ),
    )

    client.force_login(inventory_context.manager)

    response = client.get(reverse("inventory:list"))

    balance = list(response.context["balances"])[0]

    assert response.status_code == 200
    assert balance.inventory_item == inventory_context.inventory_item
    assert balance.on_hand_quantity == Decimal("8.000")
    assert balance.available_quantity == Decimal("8.000")


@pytest.mark.django_db
def test_inventory_list_supports_search(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Search stock using a product SKU or name."""

    client.force_login(inventory_context.manager)

    matching_response = client.get(
        reverse("inventory:list"),
        {"q": "OIL-FILTER"},
    )
    missing_response = client.get(
        reverse("inventory:list"),
        {"q": "DOES-NOT-EXIST"},
    )

    assert len(matching_response.context["balances"]) == 1
    assert len(missing_response.context["balances"]) == 0


@pytest.mark.django_db
def test_technician_can_view_inventory_detail(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Allow technicians to inspect one inventory item."""

    client.force_login(inventory_context.technician)

    response = client.get(
        reverse(
            "inventory:detail",
            args=(inventory_context.inventory_item.pk,),
        )
    )

    assert response.status_code == 200
    assert response.context["inventory_item"] == inventory_context.inventory_item
    assert response.context["balance"].on_hand_quantity == Decimal("0.000")


@pytest.mark.django_db
def test_missing_inventory_detail_returns_404(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Return HTTP 404 for an unknown inventory item."""

    client.force_login(inventory_context.manager)

    response = client.get(
        reverse(
            "inventory:detail",
            args=(999999,),
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_technician_cannot_view_movement_ledger(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from viewing the full stock ledger."""

    client.force_login(inventory_context.technician)

    response = client.get(reverse("inventory:movement_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_can_view_and_filter_movements(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Allow managers to inspect the stock ledger."""

    movement = receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("4.000"),
            external_reference="SUPPLIER-100",
        ),
    )

    client.force_login(inventory_context.manager)

    response = client.get(
        reverse("inventory:movement_list"),
        {
            "q": "SUPPLIER-100",
            "movement_type": (StockMovementType.RECEIPT),
        },
    )

    assert response.status_code == 200
    assert list(response.context["movements"]) == [movement]


@pytest.mark.django_db
def test_manager_creates_stock_location_from_browser(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Allow a manager to register a stock location."""

    client.force_login(inventory_context.manager)

    response = client.post(
        reverse("inventory:location_create"),
        {
            "code": " shelf-c / 03 ",
            "name": "Shelf C 03",
            "description": "Browser-created shelf.",
        },
    )

    assert response.status_code == 302

    location = StockLocation.objects.get(normalized_code="SHELF-C-03")

    assert location.name == "Shelf C 03"
    assert location.created_by == inventory_context.manager


@pytest.mark.django_db
def test_technician_cannot_create_stock_location(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from creating stock locations."""

    client.force_login(inventory_context.technician)

    response = client.get(reverse("inventory:location_create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_creates_inventory_item_from_browser(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Allow a manager to create a product-location item."""

    location = create_stock_location(
        actor=inventory_context.manager,
        command=CreateStockLocationCommand(
            code="BROWSER-STORE",
            name="Browser Store",
        ),
    )

    client.force_login(inventory_context.manager)

    response = client.post(
        reverse("inventory:item_create"),
        {
            "product": inventory_context.product.pk,
            "location": location.pk,
            "reorder_level": "3.000",
            "notes": "Created through browser.",
        },
    )

    assert response.status_code == 302

    inventory_item = InventoryItem.objects.get(
        product=inventory_context.product,
        location=location,
    )

    assert inventory_item.reorder_level == Decimal("3.000")
    assert inventory_item.created_by == inventory_context.manager


@pytest.mark.django_db
def test_technician_cannot_create_inventory_item(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from creating inventory items."""

    client.force_login(inventory_context.technician)

    response = client.get(reverse("inventory:item_create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_receives_stock_from_browser(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Record a receipt through the browser interface."""

    client.force_login(inventory_context.manager)

    response = client.post(
        reverse(
            "inventory:receive",
            args=(inventory_context.inventory_item.pk,),
        ),
        {
            "quantity": "5.000",
            "unit_cost": "15000.00",
            "currency": "UGX",
            "external_reference": "BROWSER-RECEIPT-001",
            "occurred_at": "",
            "notes": "Received from browser.",
        },
    )

    assert response.status_code == 302

    movement = StockMovement.objects.get(movement_type=StockMovementType.RECEIPT)

    assert movement.quantity == Decimal("5.000")
    assert movement.external_reference == "BROWSER-RECEIPT-001"
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("5.000")


@pytest.mark.django_db
def test_invalid_browser_receipt_shows_form_error(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Redisplay an invalid receipt without changing stock."""

    client.force_login(inventory_context.manager)

    response = client.post(
        reverse(
            "inventory:receive",
            args=(inventory_context.inventory_item.pk,),
        ),
        {
            "quantity": "0",
            "unit_cost": "",
            "currency": "UGX",
            "external_reference": "",
            "occurred_at": "",
            "notes": "",
        },
    )

    assert response.status_code == 200
    assert "quantity" in response.context["form"].errors
    assert not StockMovement.objects.exists()


@pytest.mark.django_db
def test_technician_cannot_receive_stock(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from receiving inventory."""

    client.force_login(inventory_context.technician)

    response = client.get(
        reverse(
            "inventory:receive",
            args=(inventory_context.inventory_item.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_adjusts_stock_from_browser(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Record a controlled adjustment through the browser."""

    receive_stock(
        actor=inventory_context.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(inventory_context.inventory_item.pk),
            quantity=Decimal("5.000"),
        ),
    )

    client.force_login(inventory_context.manager)

    response = client.post(
        reverse(
            "inventory:adjust",
            args=(inventory_context.inventory_item.pk,),
        ),
        {
            "movement_type": (StockMovementType.ADJUSTMENT_OUT),
            "quantity": "2.000",
            "reason": "Damaged during storage.",
            "external_reference": "DAMAGE-001",
            "occurred_at": "",
        },
    )

    assert response.status_code == 302
    assert (
        StockMovement.objects.filter(
            movement_type=(StockMovementType.ADJUSTMENT_OUT)
        ).count()
        == 1
    )
    assert get_on_hand_quantity(
        inventory_item_id=(inventory_context.inventory_item.pk)
    ) == Decimal("3.000")


@pytest.mark.django_db
def test_technician_cannot_adjust_stock(
    client,
    inventory_context: InventoryTestContext,
) -> None:
    """Prevent technicians from adjusting inventory."""

    client.force_login(inventory_context.technician)

    response = client.get(
        reverse(
            "inventory:adjust",
            args=(inventory_context.inventory_item.pk,),
        )
    )

    assert response.status_code == 403
