"""Read-only queries for inventory balances and records."""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
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


def _stock_movement_total_subquery() -> QuerySet[StockMovement]:
    """Return signed stock totals for one outer item."""

    signed_quantity = Case(
        When(
            movement_type__in=tuple(StockMovement.POSITIVE_TYPES),
            then=F("quantity"),
        ),
        default=-F("quantity"),
        output_field=_BALANCE_FIELD,
    )

    return (
        StockMovement.objects.filter(inventory_item_id=OuterRef("pk"))
        .order_by()
        .values("inventory_item_id")
        .annotate(total=Sum(signed_quantity))
        .values("total")[:1]
    )


def _reservation_total_subquery() -> QuerySet[StockReservation]:
    """Return active reserved stock for one outer item."""

    remaining_quantity = ExpressionWrapper(
        F("quantity_reserved") - F("quantity_issued") - F("quantity_released"),
        output_field=_BALANCE_FIELD,
    )

    return (
        StockReservation.objects.filter(
            inventory_item_id=OuterRef("pk"),
            status__in=(_ACTIVE_RESERVATION_STATUSES),
        )
        .order_by()
        .values("inventory_item_id")
        .annotate(total=Sum(remaining_quantity))
        .values("total")[:1]
    )


def get_low_stock_items() -> list[InventoryBalance]:
    """Return low-stock balances using one database query."""

    inventory_items = (
        get_inventory_items()
        .filter(is_active=True)
        .annotate(
            calculated_on_hand=Coalesce(
                Subquery(
                    _stock_movement_total_subquery(),
                    output_field=_BALANCE_FIELD,
                ),
                Value(Decimal("0.000")),
                output_field=_BALANCE_FIELD,
            ),
            calculated_reserved=Coalesce(
                Subquery(
                    _reservation_total_subquery(),
                    output_field=_BALANCE_FIELD,
                ),
                Value(Decimal("0.000")),
                output_field=_BALANCE_FIELD,
            ),
        )
        .annotate(
            calculated_available=(
                ExpressionWrapper(
                    F("calculated_on_hand") - F("calculated_reserved"),
                    output_field=_BALANCE_FIELD,
                )
            )
        )
        .filter(calculated_available__lte=(F("reorder_level")))
    )

    return [
        InventoryBalance(
            inventory_item=inventory_item,
            on_hand_quantity=(inventory_item.calculated_on_hand),
            reserved_quantity=(inventory_item.calculated_reserved),
            available_quantity=(inventory_item.calculated_available),
        )
        for inventory_item in inventory_items
    ]


def search_inventory_balances(
    *,
    query: str = "",
    location_id: int | None = None,
    low_stock_only: bool = False,
) -> list[InventoryBalance]:
    """Return inventory balances matching browser filters."""

    inventory_items = get_inventory_items()

    normalized_query = query.strip()

    if normalized_query:
        inventory_items = inventory_items.filter(
            Q(product__sku__icontains=normalized_query)
            | Q(product__name__icontains=normalized_query)
            | Q(product__manufacturer_part_number__icontains=(normalized_query))
            | Q(location__code__icontains=normalized_query)
            | Q(location__name__icontains=normalized_query)
        )

    if location_id is not None:
        inventory_items = inventory_items.filter(location_id=location_id)

    balances = [
        get_inventory_balance(inventory_item_id=inventory_item.pk)
        for inventory_item in inventory_items
    ]

    if low_stock_only:
        balances = [balance for balance in balances if balance.is_low_stock]

    return balances


def get_inventory_item_by_id(
    *,
    inventory_item_id: int,
) -> InventoryItem:
    """Return one inventory item with related records."""

    return get_inventory_items().get(pk=inventory_item_id)


def get_inventory_item_reservations(
    *,
    inventory_item_id: int,
) -> QuerySet[StockReservation]:
    """Return reservation history for one inventory item."""

    return (
        StockReservation.objects.filter(inventory_item_id=inventory_item_id)
        .select_related(
            "inventory_item",
            "work_product_requirement",
            "work_product_requirement__work_order",
            "reserved_by",
            "released_by",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_inventory_item_movements(
    *,
    inventory_item_id: int,
) -> QuerySet[StockMovement]:
    """Return movement history for one inventory item."""

    return (
        StockMovement.objects.filter(inventory_item_id=inventory_item_id)
        .select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "reservation",
            "source_movement",
            "created_by",
        )
        .order_by(
            "-occurred_at",
            "-pk",
        )
    )


def search_stock_movements(
    *,
    query: str = "",
    movement_type: str = "",
) -> QuerySet[StockMovement]:
    """Return stock-ledger entries matching browser filters."""

    movements = StockMovement.objects.select_related(
        "inventory_item",
        "inventory_item__product",
        "inventory_item__location",
        "reservation",
        "source_movement",
        "created_by",
    )

    normalized_query = query.strip()

    if normalized_query:
        movements = movements.filter(
            Q(movement_number__icontains=(normalized_query))
            | Q(inventory_item__product__sku__icontains=(normalized_query))
            | Q(inventory_item__product__name__icontains=(normalized_query))
            | Q(inventory_item__location__code__icontains=(normalized_query))
            | Q(external_reference__icontains=(normalized_query))
        )

    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    return movements.order_by(
        "-occurred_at",
        "-pk",
    )
