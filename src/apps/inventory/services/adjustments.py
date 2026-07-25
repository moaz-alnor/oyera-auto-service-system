"""Application services for controlled stock adjustments."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.constants import (
    InventoryPermissionName,
    StockMovementType,
)
from apps.inventory.models import (
    InventoryItem,
    StockMovement,
)
from apps.inventory.selectors import get_on_hand_quantity


@dataclass(frozen=True, slots=True)
class AdjustStockCommand:
    """Contain one controlled stock adjustment."""

    inventory_item_id: int
    movement_type: StockMovementType
    quantity: Decimal
    reason: str
    external_reference: str = ""
    occurred_at: datetime | None = None


_ADJUSTMENT_TYPES = {
    StockMovementType.ADJUSTMENT_IN,
    StockMovementType.ADJUSTMENT_OUT,
}


def _require_adjustment_permission(
    *,
    actor: User,
) -> None:
    """Require permission to adjust inventory."""

    if not actor.has_perm(InventoryPermissionName.ADJUST_STOCK.value):
        raise PermissionDenied("Your account cannot adjust inventory stock.")


def _validate_inventory_item(
    *,
    inventory_item: InventoryItem,
) -> None:
    """Require an active inventory record."""

    if not inventory_item.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be adjusted for an inactive inventory item."
                )
            }
        )

    if not inventory_item.product.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be adjusted for an inactive catalogue product."
                )
            }
        )

    if not inventory_item.location.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be adjusted in an inactive storage location."
                )
            }
        )


@transaction.atomic
def adjust_stock(
    *,
    actor: User,
    command: AdjustStockCommand,
) -> StockMovement:
    """Record a positive or negative inventory adjustment."""

    _require_adjustment_permission(actor=actor)

    if command.movement_type not in _ADJUSTMENT_TYPES:
        raise ValidationError(
            {"movement_type": ("Select a positive or negative stock adjustment.")}
        )

    if command.quantity <= Decimal("0"):
        raise ValidationError(
            {"quantity": ("Adjustment quantity must be greater than zero.")}
        )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError(
            {"reason": ("Record why the stock balance is being adjusted.")}
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

    if command.movement_type == StockMovementType.ADJUSTMENT_OUT:
        on_hand_quantity = get_on_hand_quantity(inventory_item_id=inventory_item.pk)

        if command.quantity > on_hand_quantity:
            raise ValidationError(
                {
                    "quantity": (
                        "A negative adjustment cannot reduce physical stock below zero."
                    )
                }
            )

    movement = StockMovement(
        movement_number=(f"TMP-{uuid4().hex[:20].upper()}"),
        inventory_item=inventory_item,
        movement_type=command.movement_type,
        quantity=command.quantity,
        external_reference=command.external_reference,
        notes=reason,
        occurred_at=(command.occurred_at or timezone.now()),
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
