"""Application services for receiving physical stock."""

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


@dataclass(frozen=True, slots=True)
class ReceiveStockCommand:
    """Contain one stock-receipt transaction."""

    inventory_item_id: int
    quantity: Decimal
    unit_cost: Decimal | None = None
    currency: str = "UGX"
    external_reference: str = ""
    notes: str = ""
    occurred_at: datetime | None = None


def _require_receive_permission(
    *,
    actor: User,
) -> None:
    """Require permission to receive physical stock."""

    if not actor.has_perm(InventoryPermissionName.RECEIVE_STOCK.value):
        raise PermissionDenied("Your account cannot receive inventory stock.")


def _validate_receipt_item(
    *,
    inventory_item: InventoryItem,
) -> None:
    """Require an active item, product, and location."""

    if not inventory_item.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be received into an inactive inventory item."
                )
            }
        )

    if not inventory_item.product.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be received for an inactive catalogue product."
                )
            }
        )

    if not inventory_item.location.is_active:
        raise ValidationError(
            {
                "inventory_item": (
                    "Stock cannot be received into an inactive storage location."
                )
            }
        )


@transaction.atomic
def receive_stock(
    *,
    actor: User,
    command: ReceiveStockCommand,
) -> StockMovement:
    """Record an append-only positive stock movement."""

    _require_receive_permission(actor=actor)

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

    _validate_receipt_item(inventory_item=inventory_item)

    temporary_number = f"TMP-{uuid4().hex[:20].upper()}"

    movement = StockMovement(
        movement_number=temporary_number,
        inventory_item=inventory_item,
        movement_type=StockMovementType.RECEIPT,
        quantity=command.quantity,
        unit_cost=command.unit_cost,
        currency=command.currency,
        external_reference=command.external_reference,
        notes=command.notes,
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
