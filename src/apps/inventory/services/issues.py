"""Application services for workshop stock issues and returns."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.constants import (
    InventoryPermissionName,
    ReservationStatus,
    StockMovementType,
)
from apps.inventory.models import (
    StockMovement,
    StockReservation,
)
from apps.inventory.selectors import get_on_hand_quantity
from apps.inventory.services.reservations import (
    sync_product_requirement_status,
)
from apps.workshop.constants import WorkOrderStatus


@dataclass(frozen=True, slots=True)
class IssueStockCommand:
    """Contain a request to issue reserved workshop stock."""

    reservation_id: int
    quantity: Decimal
    notes: str = ""
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReturnStockCommand:
    """Contain a request to return previously issued stock."""

    source_movement_id: int
    quantity: Decimal
    notes: str = ""
    occurred_at: datetime | None = None


_ACTIVE_RESERVATION_STATUSES = {
    ReservationStatus.ACTIVE,
    ReservationStatus.PARTIALLY_ISSUED,
}

_ISSUABLE_WORK_ORDER_STATUSES = {
    WorkOrderStatus.READY,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
}


def _require_permission(
    *,
    actor: User,
    permission: InventoryPermissionName,
) -> None:
    """Require one inventory transaction permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied("Your account cannot perform this inventory action.")


def _validate_positive_quantity(
    *,
    quantity: Decimal,
) -> None:
    """Require a positive stock transaction quantity."""

    if quantity <= Decimal("0"):
        raise ValidationError(
            {"quantity": ("Stock quantity must be greater than zero.")}
        )


def _validate_inventory_item(
    *,
    reservation: StockReservation,
) -> None:
    """Require an active item, product, and location."""

    inventory_item = reservation.inventory_item

    if not inventory_item.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be issued from an inactive inventory item."
                )
            }
        )

    if not inventory_item.product.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be issued for an inactive catalogue product."
                )
            }
        )

    if not inventory_item.location.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be issued from an inactive storage location."
                )
            }
        )


def _create_numbered_movement(
    *,
    actor: User,
    reservation: StockReservation,
    movement_type: StockMovementType,
    quantity: Decimal,
    notes: str,
    occurred_at: datetime | None,
    source_movement: StockMovement | None = None,
) -> StockMovement:
    """Create a stock movement with a stable ledger number."""

    temporary_number = f"TMP-{uuid4().hex[:20].upper()}"

    movement = StockMovement(
        movement_number=temporary_number,
        inventory_item=reservation.inventory_item,
        movement_type=movement_type,
        quantity=quantity,
        reservation=reservation,
        source_movement=source_movement,
        notes=notes,
        occurred_at=occurred_at or timezone.now(),
        created_by=actor,
    )
    movement.full_clean()
    movement.save()

    if movement.pk is None:
        raise RuntimeError("The stock movement was saved without a primary key.")

    movement.movement_number = f"MOV-{movement.pk:06d}"
    movement.save(
        update_fields=(
            "movement_number",
            "updated_at",
        )
    )

    return movement


@transaction.atomic
def issue_reserved_stock(
    *,
    actor: User,
    command: IssueStockCommand,
) -> StockMovement:
    """Issue physical stock against an active reservation."""

    _require_permission(
        actor=actor,
        permission=InventoryPermissionName.ISSUE_STOCK,
    )
    _validate_positive_quantity(quantity=command.quantity)

    try:
        reservation = (
            StockReservation.objects.select_for_update()
            .select_related(
                "inventory_item",
                "inventory_item__product",
                "inventory_item__location",
                "work_product_requirement",
                "work_product_requirement__work_order",
            )
            .get(pk=command.reservation_id)
        )
    except StockReservation.DoesNotExist as exc:
        raise ValidationError(
            {"reservation": ("The selected stock reservation does not exist.")}
        ) from exc

    if reservation.status not in (
        ReservationStatus.ACTIVE,
        ReservationStatus.PARTIALLY_ISSUED,
    ):
        raise ValidationError(
            {
                "reservation": (
                    "This stock reservation is no longer available for issuing."
                )
            }
        )

    work_order = reservation.work_product_requirement.work_order

    if work_order.status not in _ISSUABLE_WORK_ORDER_STATUSES:
        raise ValidationError(
            {
                "reservation": (
                    "Stock cannot be issued for this work order in its current state."
                )
            }
        )

    _validate_inventory_item(reservation=reservation)

    remaining_quantity = reservation.remaining_quantity

    if command.quantity > remaining_quantity:
        raise ValidationError(
            {
                "quantity": (
                    "Issued quantity cannot exceed the stock "
                    "remaining on the reservation."
                )
            }
        )

    on_hand_quantity = get_on_hand_quantity(
        inventory_item_id=(reservation.inventory_item_id)
    )

    if command.quantity > on_hand_quantity:
        raise ValidationError(
            {"quantity": ("There is not enough physical stock to complete this issue.")}
        )

    movement = _create_numbered_movement(
        actor=actor,
        reservation=reservation,
        movement_type=StockMovementType.ISSUE,
        quantity=command.quantity,
        notes=command.notes,
        occurred_at=command.occurred_at,
    )

    reservation.quantity_issued += command.quantity

    if reservation.remaining_quantity == Decimal("0"):
        reservation.status = ReservationStatus.FULFILLED
    else:
        reservation.status = ReservationStatus.PARTIALLY_ISSUED

    reservation.full_clean()
    reservation.save(
        update_fields=(
            "quantity_issued",
            "status",
            "updated_at",
        )
    )

    requirement = reservation.work_product_requirement

    reservations = list(
        StockReservation.objects.select_for_update().filter(
            work_product_requirement=requirement
        )
    )

    sync_product_requirement_status(
        requirement=requirement,
        reservations=reservations,
    )

    return movement


@transaction.atomic
def return_issued_stock(
    *,
    actor: User,
    command: ReturnStockCommand,
) -> StockMovement:
    """Return physical stock from an earlier workshop issue."""

    _require_permission(
        actor=actor,
        permission=InventoryPermissionName.RETURN_STOCK,
    )
    _validate_positive_quantity(quantity=command.quantity)

    try:
        source_movement = (
            StockMovement.objects.select_for_update()
            .select_related(
                "reservation",
                "inventory_item",
            )
            .get(pk=command.source_movement_id)
        )
    except StockMovement.DoesNotExist as exc:
        raise ValidationError(
            {"source_movement": ("The selected stock issue does not exist.")}
        ) from exc

    if source_movement.movement_type != StockMovementType.ISSUE:
        raise ValidationError(
            {"source_movement": ("Only a workshop stock issue can be returned.")}
        )

    if source_movement.reservation_id is None:
        raise ValidationError(
            {"source_movement": ("The original issue has no stock reservation.")}
        )

    reservation = (
        StockReservation.objects.select_for_update()
        .select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "work_product_requirement",
            "work_product_requirement__work_order",
        )
        .get(pk=source_movement.reservation_id)
    )

    returned_quantity = StockMovement.objects.filter(
        source_movement=source_movement,
        movement_type=StockMovementType.RETURN,
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0.000")

    returnable_quantity = source_movement.quantity - returned_quantity

    if command.quantity > returnable_quantity:
        raise ValidationError(
            {
                "quantity": (
                    "Returned quantity cannot exceed the "
                    "quantity remaining on the original issue."
                )
            }
        )

    if command.quantity > reservation.quantity_issued:
        raise ValidationError(
            {
                "quantity": (
                    "Returned quantity cannot exceed the reservation's issued quantity."
                )
            }
        )

    movement = _create_numbered_movement(
        actor=actor,
        reservation=reservation,
        movement_type=StockMovementType.RETURN,
        quantity=command.quantity,
        notes=command.notes,
        occurred_at=command.occurred_at,
        source_movement=source_movement,
    )

    reservation.quantity_issued -= command.quantity

    if reservation.quantity_issued == Decimal("0"):
        reservation.status = ReservationStatus.ACTIVE
    else:
        reservation.status = ReservationStatus.PARTIALLY_ISSUED

    reservation.full_clean()
    reservation.save(
        update_fields=(
            "quantity_issued",
            "status",
            "updated_at",
        )
    )

    requirement = reservation.work_product_requirement

    reservations = list(
        StockReservation.objects.select_for_update().filter(
            work_product_requirement=requirement
        )
    )

    sync_product_requirement_status(
        requirement=requirement,
        reservations=reservations,
    )

    return movement
