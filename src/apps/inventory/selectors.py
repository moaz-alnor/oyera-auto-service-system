"""Read-only queries for inventory balances and records."""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from apps.inventory.constants import ReservationStatus
from apps.inventory.models import (
    InventoryItem,
    StockMovement,
    StockReservation,
)

_BALANCE_FIELD = DecimalField(
    max_digits=18,
    decimal_places=3,
)

_ACTIVE_RESERVATION_STATUSES = (
    ReservationStatus.ACTIVE,
    ReservationStatus.PARTIALLY_ISSUED,
)


@dataclass(frozen=True, slots=True)
class InventoryBalance:
    """Contain calculated quantities for one inventory item."""

    inventory_item: InventoryItem
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal

    @property
    def is_low_stock(self) -> bool:
        """Return whether available stock reached reorder level."""

        return self.available_quantity <= self.inventory_item.reorder_level


def get_inventory_items() -> QuerySet[InventoryItem]:
    """Return inventory items with product and location details."""

    return InventoryItem.objects.select_related(
        "product",
        "product__category",
        "location",
        "created_by",
        "updated_by",
    ).order_by(
        "product__name",
        "location__name",
    )


def get_on_hand_quantity(
    *,
    inventory_item_id: int,
) -> Decimal:
    """Calculate physical stock from the append-only ledger."""

    signed_quantity = Case(
        When(
            movement_type__in=tuple(StockMovement.POSITIVE_TYPES),
            then=F("quantity"),
        ),
        default=-F("quantity"),
        output_field=_BALANCE_FIELD,
    )

    result = StockMovement.objects.filter(
        inventory_item_id=inventory_item_id
    ).aggregate(
        total=Coalesce(
            Sum(signed_quantity),
            Value(Decimal("0.000")),
            output_field=_BALANCE_FIELD,
        )
    )

    return result["total"]


def get_reserved_quantity(
    *,
    inventory_item_id: int,
) -> Decimal:
    """Return stock still committed to active reservations."""

    remaining_quantity = ExpressionWrapper(
        F("quantity_reserved") - F("quantity_issued") - F("quantity_released"),
        output_field=_BALANCE_FIELD,
    )

    result = StockReservation.objects.filter(
        inventory_item_id=inventory_item_id,
        status__in=_ACTIVE_RESERVATION_STATUSES,
    ).aggregate(
        total=Coalesce(
            Sum(remaining_quantity),
            Value(Decimal("0.000")),
            output_field=_BALANCE_FIELD,
        )
    )

    return result["total"]


def get_available_quantity(
    *,
    inventory_item_id: int,
) -> Decimal:
    """Return unreserved physical stock available for use."""

    return get_on_hand_quantity(
        inventory_item_id=inventory_item_id
    ) - get_reserved_quantity(inventory_item_id=inventory_item_id)


def get_inventory_balance(
    *,
    inventory_item_id: int,
) -> InventoryBalance:
    """Return physical, reserved, and available quantities."""

    inventory_item = get_inventory_items().get(pk=inventory_item_id)

    on_hand_quantity = get_on_hand_quantity(inventory_item_id=inventory_item.pk)
    reserved_quantity = get_reserved_quantity(inventory_item_id=inventory_item.pk)

    return InventoryBalance(
        inventory_item=inventory_item,
        on_hand_quantity=on_hand_quantity,
        reserved_quantity=reserved_quantity,
        available_quantity=(on_hand_quantity - reserved_quantity),
    )


def get_low_stock_items() -> list[InventoryBalance]:
    """Return active inventory items at or below reorder level."""

    balances = [
        get_inventory_balance(inventory_item_id=inventory_item.pk)
        for inventory_item in get_inventory_items().filter(is_active=True)
    ]

    return [balance for balance in balances if balance.is_low_stock]
