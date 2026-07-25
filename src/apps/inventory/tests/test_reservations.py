"""Tests for workshop stock reservations."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.constants import ReservationStatus
from apps.inventory.models import StockReservation
from apps.inventory.selectors import (
    get_available_quantity,
    get_reserved_quantity,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.services.reservations import (
    ReleaseReservationCommand,
    ReserveStockCommand,
    release_stock_reservation,
    reserve_stock,
)
from apps.inventory.tests.conftest import (
    InventoryReservationContext,
)
from apps.workshop.constants import (
    ProductRequirementStatus,
)


def _receive_opening_stock(
    *,
    context: InventoryReservationContext,
    quantity: Decimal = Decimal("10.000"),
) -> None:
    """Receive physical stock for reservation tests."""

    receive_stock(
        actor=context.inventory.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            quantity=quantity,
            notes="Reservation test stock.",
        ),
    )


@pytest.mark.django_db
def test_manager_reserves_stock_for_workshop_requirement(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Reserve the complete approved workshop demand."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    reservation = reserve_stock(
        actor=context.inventory.manager,
        command=ReserveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            work_product_requirement_id=(context.requirement.pk),
            quantity=Decimal("2.000"),
        ),
    )

    context.requirement.refresh_from_db()

    assert reservation.status == ReservationStatus.ACTIVE
    assert reservation.quantity_reserved == Decimal("2.000")
    assert get_reserved_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("2.000")
    assert get_available_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("8.000")
    assert context.requirement.inventory_status == ProductRequirementStatus.RESERVED


@pytest.mark.django_db
def test_partial_reservation_updates_requirement_status(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Identify partially reserved approved demand."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    reserve_stock(
        actor=context.inventory.manager,
        command=ReserveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            work_product_requirement_id=(context.requirement.pk),
            quantity=Decimal("1.000"),
        ),
    )

    context.requirement.refresh_from_db()

    assert (
        context.requirement.inventory_status
        == ProductRequirementStatus.PARTIALLY_RESERVED
    )


@pytest.mark.django_db
def test_reservation_cannot_exceed_available_stock(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent commitments beyond physical availability."""

    context = inventory_reservation_context
    _receive_opening_stock(
        context=context,
        quantity=Decimal("1.000"),
    )

    with pytest.raises(
        ValidationError,
        match="enough available stock",
    ):
        reserve_stock(
            actor=context.inventory.manager,
            command=ReserveStockCommand(
                inventory_item_id=(context.inventory.inventory_item.pk),
                work_product_requirement_id=(context.requirement.pk),
                quantity=Decimal("2.000"),
            ),
        )

    assert not StockReservation.objects.exists()


@pytest.mark.django_db
def test_reservation_cannot_exceed_approved_demand(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent reserving more than the quotation approved."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    with pytest.raises(
        ValidationError,
        match="remaining approved workshop demand",
    ):
        reserve_stock(
            actor=context.inventory.manager,
            command=ReserveStockCommand(
                inventory_item_id=(context.inventory.inventory_item.pk),
                work_product_requirement_id=(context.requirement.pk),
                quantity=Decimal("3.000"),
            ),
        )


@pytest.mark.django_db
def test_duplicate_active_reservation_is_rejected(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent duplicate active reservations for one item."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    reserve_stock(
        actor=context.inventory.manager,
        command=ReserveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            work_product_requirement_id=(context.requirement.pk),
            quantity=Decimal("1.000"),
        ),
    )

    with pytest.raises(
        ValidationError,
        match="already has an active reservation",
    ):
        reserve_stock(
            actor=context.inventory.manager,
            command=ReserveStockCommand(
                inventory_item_id=(context.inventory.inventory_item.pk),
                work_product_requirement_id=(context.requirement.pk),
                quantity=Decimal("1.000"),
            ),
        )

    assert StockReservation.objects.count() == 1


@pytest.mark.django_db
def test_releasing_reservation_restores_availability(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Release unissued stock without deleting its history."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    reservation = reserve_stock(
        actor=context.inventory.manager,
        command=ReserveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            work_product_requirement_id=(context.requirement.pk),
            quantity=Decimal("2.000"),
        ),
    )

    released = release_stock_reservation(
        actor=context.inventory.manager,
        command=ReleaseReservationCommand(
            reservation_id=reservation.pk,
            reason="Customer cancelled the requested part.",
        ),
    )

    context.requirement.refresh_from_db()

    assert released.status == ReservationStatus.RELEASED
    assert released.quantity_released == Decimal("2.000")
    assert released.released_at is not None
    assert released.release_reason == "Customer cancelled the requested part."
    assert get_reserved_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("0.000")
    assert get_available_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("10.000")
    assert context.requirement.inventory_status == ProductRequirementStatus.NOT_RESERVED
    assert StockReservation.objects.count() == 1


@pytest.mark.django_db
def test_technician_cannot_reserve_stock(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent ordinary technicians from committing inventory."""

    context = inventory_reservation_context
    _receive_opening_stock(context=context)

    with pytest.raises(PermissionDenied):
        reserve_stock(
            actor=context.inventory.technician,
            command=ReserveStockCommand(
                inventory_item_id=(context.inventory.inventory_item.pk),
                work_product_requirement_id=(context.requirement.pk),
                quantity=Decimal("1.000"),
            ),
        )

    assert not StockReservation.objects.exists()
