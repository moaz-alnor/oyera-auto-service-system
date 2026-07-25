"""Application services for workshop stock reservations."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.constants import (
    InventoryPermissionName,
    ReservationStatus,
)
from apps.inventory.models import (
    InventoryItem,
    StockReservation,
)
from apps.inventory.selectors import (
    get_available_quantity,
)
from apps.workshop.constants import (
    ProductRequirementStatus,
    WorkOrderStatus,
)
from apps.workshop.models import WorkProductRequirement


@dataclass(frozen=True, slots=True)
class ReserveStockCommand:
    """Contain one stock-reservation request."""

    inventory_item_id: int
    work_product_requirement_id: int
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class ReleaseReservationCommand:
    """Contain a request to release reserved stock."""

    reservation_id: int
    reason: str


_ACTIVE_RESERVATION_STATUSES = {
    ReservationStatus.ACTIVE,
    ReservationStatus.PARTIALLY_ISSUED,
}

_RESERVABLE_WORK_ORDER_STATUSES = {
    WorkOrderStatus.PLANNED,
    WorkOrderStatus.READY,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
}


def _require_permission(
    *,
    actor: User,
    permission: InventoryPermissionName,
) -> None:
    """Require one inventory permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied("Your account cannot perform this inventory action.")


def _validate_inventory_item(
    *,
    inventory_item: InventoryItem,
) -> None:
    """Require an active item, product, and location."""

    if not inventory_item.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be reserved from an inactive inventory item."
                )
            }
        )

    if not inventory_item.product.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be reserved for an inactive catalogue product."
                )
            }
        )

    if not inventory_item.location.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be reserved from an inactive storage location."
                )
            }
        )


def _get_requirement_reservation_totals(
    *,
    reservations: list[StockReservation],
) -> tuple[Decimal, Decimal]:
    """Return issued and outstanding reserved quantities."""

    issued_quantity = sum(
        (reservation.quantity_issued for reservation in reservations),
        Decimal("0.000"),
    )

    reserved_quantity = sum(
        (
            reservation.remaining_quantity
            for reservation in reservations
            if reservation.status in _ACTIVE_RESERVATION_STATUSES
        ),
        Decimal("0.000"),
    )

    return issued_quantity, reserved_quantity


def sync_product_requirement_status(
    *,
    requirement: WorkProductRequirement,
    reservations: list[StockReservation] | None = None,
) -> WorkProductRequirement:
    """Synchronise workshop demand with inventory activity."""

    if reservations is None:
        reservations = list(
            StockReservation.objects.filter(work_product_requirement_id=requirement.pk)
        )

    if requirement.work_order.status == WorkOrderStatus.CANCELLED:
        expected_status = ProductRequirementStatus.CANCELLED
    else:
        issued_quantity, reserved_quantity = _get_requirement_reservation_totals(
            reservations=reservations
        )

        if issued_quantity >= requirement.approved_quantity:
            expected_status = ProductRequirementStatus.ISSUED
        elif issued_quantity > Decimal("0"):
            expected_status = ProductRequirementStatus.PARTIALLY_ISSUED
        elif reserved_quantity >= requirement.approved_quantity:
            expected_status = ProductRequirementStatus.RESERVED
        elif reserved_quantity > Decimal("0"):
            expected_status = ProductRequirementStatus.PARTIALLY_RESERVED
        else:
            expected_status = ProductRequirementStatus.NOT_RESERVED

    if requirement.inventory_status == expected_status:
        return requirement

    requirement.inventory_status = expected_status
    requirement.full_clean()
    requirement.save(
        update_fields=(
            "inventory_status",
            "updated_at",
        )
    )

    return requirement


@transaction.atomic
def reserve_stock(
    *,
    actor: User,
    command: ReserveStockCommand,
) -> StockReservation:
    """Reserve available physical stock for workshop demand."""

    _require_permission(
        actor=actor,
        permission=InventoryPermissionName.RESERVE_STOCK,
    )

    if command.quantity <= Decimal("0"):
        raise ValidationError(
            {"quantity": ("Reserved quantity must be greater than zero.")}
        )

    try:
        inventory_item = (
            InventoryItem.objects.select_for_update()
            .select_related(
                "product",
                "location",
            )
            .get(pk=command.inventory_item_id)
        )
    except InventoryItem.DoesNotExist as exc:
        raise ValidationError(
            {"inventory_item": ("The selected inventory item does not exist.")}
        ) from exc

    _validate_inventory_item(inventory_item=inventory_item)

    try:
        requirement = (
            WorkProductRequirement.objects.select_for_update()
            .select_related(
                "work_order",
                "source_product_line",
                "source_product_line__product",
            )
            .get(pk=command.work_product_requirement_id)
        )
    except WorkProductRequirement.DoesNotExist as exc:
        raise ValidationError(
            {
                "work_product_requirement": (
                    "The selected workshop product requirement does not exist."
                )
            }
        ) from exc

    if requirement.work_order.status not in _RESERVABLE_WORK_ORDER_STATUSES:
        raise ValidationError(
            {
                "work_product_requirement": (
                    "Stock cannot be reserved for this work order in its current state."
                )
            }
        )

    if inventory_item.product_id != requirement.source_product_line.product_id:
        raise ValidationError(
            {
                "inventory_item": (
                    "The selected inventory item does not match "
                    "the required workshop product."
                )
            }
        )

    reservations = list(
        StockReservation.objects.select_for_update()
        .filter(work_product_requirement=requirement)
        .order_by("pk")
    )

    duplicate_active_reservation = any(
        (
            reservation.inventory_item_id == inventory_item.pk
            and reservation.status in _ACTIVE_RESERVATION_STATUSES
        )
        for reservation in reservations
    )

    if duplicate_active_reservation:
        raise ValidationError(
            {
                "inventory_item": (
                    "This inventory item already has an active "
                    "reservation for the requirement."
                )
            }
        )

    issued_quantity, reserved_quantity = _get_requirement_reservation_totals(
        reservations=reservations
    )

    remaining_demand = (
        requirement.approved_quantity - issued_quantity - reserved_quantity
    )

    if remaining_demand <= Decimal("0"):
        raise ValidationError(
            {
                "quantity": (
                    "The approved workshop requirement is "
                    "already fully reserved or issued."
                )
            }
        )

    if command.quantity > remaining_demand:
        raise ValidationError(
            {
                "quantity": (
                    "Reserved quantity cannot exceed the "
                    "remaining approved workshop demand."
                )
            }
        )

    available_quantity = get_available_quantity(inventory_item_id=inventory_item.pk)

    if command.quantity > available_quantity:
        raise ValidationError(
            {
                "quantity": (
                    "The selected inventory item does not have enough available stock."
                )
            }
        )

    reservation = StockReservation(
        inventory_item=inventory_item,
        work_product_requirement=requirement,
        status=ReservationStatus.ACTIVE,
        quantity_reserved=command.quantity,
        quantity_issued=Decimal("0.000"),
        quantity_released=Decimal("0.000"),
        reserved_by=actor,
    )
    reservation.full_clean()
    reservation.save()

    reservations.append(reservation)

    sync_product_requirement_status(
        requirement=requirement,
        reservations=reservations,
    )

    return reservation


@transaction.atomic
def release_stock_reservation(
    *,
    actor: User,
    command: ReleaseReservationCommand,
) -> StockReservation:
    """Release unissued stock while preserving reservation history."""

    _require_permission(
        actor=actor,
        permission=(InventoryPermissionName.RELEASE_RESERVATION),
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError(
            {"reason": ("Record why the stock reservation is being released.")}
        )

    try:
        reservation = (
            StockReservation.objects.select_for_update()
            .select_related(
                "inventory_item",
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
            {"reservation": ("This stock reservation is no longer active.")}
        )

    remaining_quantity = reservation.remaining_quantity

    if remaining_quantity <= Decimal("0"):
        raise ValidationError(
            {"reservation": ("This reservation has no remaining stock to release.")}
        )

    reservation.quantity_released += remaining_quantity
    reservation.status = ReservationStatus.RELEASED
    reservation.released_by = actor
    reservation.released_at = timezone.now()
    reservation.release_reason = reason
    reservation.full_clean()
    reservation.save(
        update_fields=(
            "quantity_released",
            "status",
            "released_by",
            "released_at",
            "release_reason",
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

    return reservation
