"""Tests for workshop stock issues and returns."""

from decimal import Decimal

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.inventory.constants import (
    ReservationStatus,
    StockMovementType,
)
from apps.inventory.models import StockMovement
from apps.inventory.selectors import (
    get_available_quantity,
    get_on_hand_quantity,
    get_reserved_quantity,
)
from apps.inventory.services.issues import (
    IssueStockCommand,
    ReturnStockCommand,
    issue_reserved_stock,
    return_issued_stock,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.services.reservations import (
    ReserveStockCommand,
    reserve_stock,
)
from apps.inventory.tests.conftest import (
    InventoryReservationContext,
)
from apps.workshop.constants import (
    ProductRequirementStatus,
    WorkOrderStatus,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)


def _prepare_reservation(
    *,
    context: InventoryReservationContext,
    reserved_quantity: Decimal = Decimal("2.000"),
):
    """Receive stock, ready the order, and reserve demand."""

    receive_stock(
        actor=context.inventory.manager,
        command=ReceiveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            quantity=Decimal("10.000"),
            notes="Issue test opening stock.",
        ),
    )

    task = context.work_order.tasks.get()

    assign_technician(
        actor=context.inventory.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(context.inventory.technician.pk),
        ),
    )

    context.work_order.refresh_from_db()

    assert context.work_order.status == WorkOrderStatus.READY

    return reserve_stock(
        actor=context.inventory.manager,
        command=ReserveStockCommand(
            inventory_item_id=(context.inventory.inventory_item.pk),
            work_product_requirement_id=(context.requirement.pk),
            quantity=reserved_quantity,
        ),
    )


@pytest.mark.django_db
def test_manager_partially_issues_reserved_stock(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Issue part of a workshop stock reservation."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    movement = issue_reserved_stock(
        actor=context.inventory.manager,
        command=IssueStockCommand(
            reservation_id=reservation.pk,
            quantity=Decimal("1.000"),
            notes="Issued one filter to the technician.",
        ),
    )

    reservation.refresh_from_db()
    context.requirement.refresh_from_db()

    assert movement.movement_number == (f"MOV-{movement.pk:06d}")
    assert movement.movement_type == StockMovementType.ISSUE
    assert movement.quantity == Decimal("1.000")
    assert movement.signed_quantity == Decimal("-1.000")

    assert reservation.status == ReservationStatus.PARTIALLY_ISSUED
    assert reservation.quantity_issued == Decimal("1.000")
    assert reservation.remaining_quantity == Decimal("1.000")

    assert get_on_hand_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("9.000")
    assert get_reserved_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("1.000")
    assert get_available_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("8.000")

    assert (
        context.requirement.inventory_status
        == ProductRequirementStatus.PARTIALLY_ISSUED
    )


@pytest.mark.django_db
def test_full_issue_fulfils_reservation_and_requirement(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Mark reservation and requirement as fully issued."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    issue_reserved_stock(
        actor=context.inventory.manager,
        command=IssueStockCommand(
            reservation_id=reservation.pk,
            quantity=Decimal("2.000"),
        ),
    )

    reservation.refresh_from_db()
    context.requirement.refresh_from_db()

    assert reservation.status == ReservationStatus.FULFILLED
    assert reservation.quantity_issued == Decimal("2.000")
    assert reservation.remaining_quantity == Decimal("0.000")
    assert context.requirement.inventory_status == ProductRequirementStatus.ISSUED
    assert get_reserved_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("0.000")
    assert get_on_hand_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("8.000")


@pytest.mark.django_db
def test_issue_cannot_exceed_reserved_quantity(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Reject stock issues beyond the reservation balance."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    with pytest.raises(
        ValidationError,
        match="remaining on the reservation",
    ):
        issue_reserved_stock(
            actor=context.inventory.manager,
            command=IssueStockCommand(
                reservation_id=reservation.pk,
                quantity=Decimal("3.000"),
            ),
        )

    reservation.refresh_from_db()

    assert reservation.quantity_issued == Decimal("0.000")
    assert StockMovement.objects.count() == 1


@pytest.mark.django_db
def test_technician_cannot_issue_stock(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent ordinary technicians from issuing inventory."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    with pytest.raises(PermissionDenied):
        issue_reserved_stock(
            actor=context.inventory.technician,
            command=IssueStockCommand(
                reservation_id=reservation.pk,
                quantity=Decimal("1.000"),
            ),
        )

    assert StockMovement.objects.count() == 1


@pytest.mark.django_db
def test_manager_returns_part_of_original_issue(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Return stock while preserving its original issue link."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    issue = issue_reserved_stock(
        actor=context.inventory.manager,
        command=IssueStockCommand(
            reservation_id=reservation.pk,
            quantity=Decimal("2.000"),
        ),
    )

    returned = return_issued_stock(
        actor=context.inventory.manager,
        command=ReturnStockCommand(
            source_movement_id=issue.pk,
            quantity=Decimal("1.000"),
            notes="One unused filter returned to store.",
        ),
    )

    reservation.refresh_from_db()
    context.requirement.refresh_from_db()

    assert returned.movement_number == (f"MOV-{returned.pk:06d}")
    assert returned.movement_type == StockMovementType.RETURN
    assert returned.source_movement == issue
    assert returned.reservation == reservation
    assert returned.signed_quantity == Decimal("1.000")

    assert reservation.status == ReservationStatus.PARTIALLY_ISSUED
    assert reservation.quantity_issued == Decimal("1.000")
    assert reservation.remaining_quantity == Decimal("1.000")

    assert get_on_hand_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("9.000")
    assert get_reserved_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("1.000")
    assert get_available_quantity(
        inventory_item_id=(context.inventory.inventory_item.pk)
    ) == Decimal("8.000")
    assert (
        context.requirement.inventory_status
        == ProductRequirementStatus.PARTIALLY_ISSUED
    )


@pytest.mark.django_db
def test_return_cannot_exceed_original_issue(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Reject cumulative returns beyond the source issue."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    issue = issue_reserved_stock(
        actor=context.inventory.manager,
        command=IssueStockCommand(
            reservation_id=reservation.pk,
            quantity=Decimal("1.000"),
        ),
    )

    return_issued_stock(
        actor=context.inventory.manager,
        command=ReturnStockCommand(
            source_movement_id=issue.pk,
            quantity=Decimal("0.750"),
        ),
    )

    with pytest.raises(
        ValidationError,
        match="original issue",
    ):
        return_issued_stock(
            actor=context.inventory.manager,
            command=ReturnStockCommand(
                source_movement_id=issue.pk,
                quantity=Decimal("0.500"),
            ),
        )

    assert (
        StockMovement.objects.filter(movement_type=StockMovementType.RETURN).count()
        == 1
    )


@pytest.mark.django_db
def test_technician_cannot_return_stock(
    inventory_reservation_context: InventoryReservationContext,
) -> None:
    """Prevent ordinary technicians from returning inventory."""

    context = inventory_reservation_context
    reservation = _prepare_reservation(context=context)

    issue = issue_reserved_stock(
        actor=context.inventory.manager,
        command=IssueStockCommand(
            reservation_id=reservation.pk,
            quantity=Decimal("1.000"),
        ),
    )

    with pytest.raises(PermissionDenied):
        return_issued_stock(
            actor=context.inventory.technician,
            command=ReturnStockCommand(
                source_movement_id=issue.pk,
                quantity=Decimal("1.000"),
            ),
        )

    assert (
        StockMovement.objects.filter(movement_type=StockMovementType.RETURN).count()
        == 0
    )
