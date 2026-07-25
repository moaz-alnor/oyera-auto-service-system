"""Application services for inventory master-data records."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from apps.accounts.models import User
from apps.inventory.constants import InventoryPermissionName
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
)
from apps.product_catalogue.models import Product


@dataclass(frozen=True, slots=True)
class CreateStockLocationCommand:
    """Contain a new physical stock-location definition."""

    code: str
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class CreateInventoryItemCommand:
    """Contain a new product-location inventory record."""

    product_id: int
    location_id: int
    reorder_level: Decimal = Decimal("0.000")
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: InventoryPermissionName,
) -> None:
    """Require one inventory master-data permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied("Your account cannot perform this inventory action.")


@transaction.atomic
def create_stock_location(
    *,
    actor: User,
    command: CreateStockLocationCommand,
) -> StockLocation:
    """Create an active physical stock location."""

    _require_permission(
        actor=actor,
        permission=(InventoryPermissionName.ADD_STOCK_LOCATION),
    )

    location = StockLocation(
        code=command.code,
        name=command.name,
        description=command.description.strip(),
        created_by=actor,
        updated_by=actor,
    )
    location.full_clean()
    location.save()

    return location


@transaction.atomic
def create_inventory_item(
    *,
    actor: User,
    command: CreateInventoryItemCommand,
) -> InventoryItem:
    """Connect one active product to one active location."""

    _require_permission(
        actor=actor,
        permission=(InventoryPermissionName.ADD_INVENTORY_ITEM),
    )

    try:
        product = (
            Product.objects.select_for_update()
            .select_related("category")
            .get(pk=command.product_id)
        )
    except Product.DoesNotExist as exc:
        raise ValidationError(
            {"product": ("The selected catalogue product does not exist.")}
        ) from exc

    if not product.is_active:
        raise ValidationError(
            {"product": ("An inventory item requires an active catalogue product.")}
        )

    try:
        location = StockLocation.objects.select_for_update().get(pk=command.location_id)
    except StockLocation.DoesNotExist as exc:
        raise ValidationError(
            {"location": ("The selected stock location does not exist.")}
        ) from exc

    if not location.is_active:
        raise ValidationError(
            {"location": ("An inventory item requires an active stock location.")}
        )

    if InventoryItem.objects.filter(
        product=product,
        location=location,
    ).exists():
        raise ValidationError(
            {
                "location": (
                    "An inventory item already exists for this "
                    "product and stock location."
                )
            }
        )

    inventory_item = InventoryItem(
        product=product,
        location=location,
        reorder_level=command.reorder_level,
        notes=command.notes.strip(),
        created_by=actor,
        updated_by=actor,
    )
    inventory_item.full_clean()
    inventory_item.save()

    return inventory_item
