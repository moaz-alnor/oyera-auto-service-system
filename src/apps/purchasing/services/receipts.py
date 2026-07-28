"""Application services for receiving purchase orders."""

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
from apps.inventory.models import InventoryItem
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    PurchasingPermissionName,
)
from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)


@dataclass(frozen=True, slots=True)
class GoodsReceiptLineCommand:
    """Contain one delivered purchase-order line."""

    purchase_order_line_id: int
    inventory_item_id: int
    quantity_received: Decimal


@dataclass(frozen=True, slots=True)
class ReceivePurchaseOrderCommand:
    """Contain one supplier-delivery transaction."""

    purchase_order_id: int
    lines: tuple[GoodsReceiptLineCommand, ...]
    supplier_delivery_reference: str = ""
    notes: str = ""
    received_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class _ValidatedReceiptLine:
    """Contain validated records used during posting."""

    purchase_order_line: PurchaseOrderLine
    inventory_item: InventoryItem
    quantity_received: Decimal


def _require_permission(
    *,
    actor: User,
) -> None:
    """Require purchasing receipt authority."""

    if not actor.has_perm(PurchasingPermissionName.RECEIVE_PURCHASE_ORDER.value):
        raise PermissionDenied(
            "You do not have permission to receive a purchase order."
        )


def _get_locked_purchase_order(
    *,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Return one locked purchase order."""

    try:
        return (
            PurchaseOrder.objects.select_for_update()
            .select_related("supplier")
            .get(pk=purchase_order_id)
        )
    except PurchaseOrder.DoesNotExist as exc:
        raise ValidationError(
            {"purchase_order": ("The selected purchase order does not exist.")}
        ) from exc


def _validate_purchase_order_status(
    *,
    purchase_order: PurchaseOrder,
) -> None:
    """Require an approved, incomplete order."""

    if purchase_order.status not in {
        PurchaseOrderStatus.APPROVED,
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
    }:
        raise ValidationError(
            {
                "purchase_order": (
                    "Only an approved or partially "
                    "received purchase order can receive "
                    "more stock."
                )
            }
        )


def _validate_unique_commands(
    *,
    commands: tuple[
        GoodsReceiptLineCommand,
        ...,
    ],
) -> None:
    """Reject duplicate purchase-order lines."""

    if not commands:
        raise ValidationError({"lines": ("Add at least one delivered product.")})

    line_ids = [command.purchase_order_line_id for command in commands]

    if len(line_ids) != len(set(line_ids)):
        raise ValidationError(
            {
                "lines": (
                    "Each purchase-order line may appear only once in a goods receipt."
                )
            }
        )


def _existing_received_quantities(
    *,
    purchase_order_line_ids: list[int],
) -> dict[int, Decimal]:
    """Return quantities already received per order line."""

    rows = (
        GoodsReceiptLine.objects.filter(
            purchase_order_line_id__in=(purchase_order_line_ids)
        )
        .values("purchase_order_line_id")
        .annotate(total=Sum("quantity_received"))
    )

    return {row["purchase_order_line_id"]: row["total"] for row in rows}


def _validate_inventory_target(
    *,
    order_line: PurchaseOrderLine,
    inventory_item: InventoryItem,
) -> None:
    """Require matching active inventory records."""

    if order_line.product_id != inventory_item.product_id:
        raise ValidationError(
            {
                "inventory_item": (
                    "The inventory product must match the ordered product."
                )
            }
        )

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


def _validated_lines(
    *,
    purchase_order: PurchaseOrder,
    commands: tuple[
        GoodsReceiptLineCommand,
        ...,
    ],
) -> list[_ValidatedReceiptLine]:
    """Lock and validate all delivered lines."""

    line_ids = [command.purchase_order_line_id for command in commands]
    inventory_item_ids = [command.inventory_item_id for command in commands]

    order_lines = {
        line.pk: line
        for line in (
            PurchaseOrderLine.objects.select_for_update()
            .select_related("product")
            .filter(
                purchase_order=purchase_order,
                pk__in=line_ids,
            )
        )
    }

    if len(order_lines) != len(line_ids):
        raise ValidationError(
            {
                "lines": (
                    "One or more selected lines do not belong to this purchase order."
                )
            }
        )

    inventory_items = {
        item.pk: item
        for item in (
            InventoryItem.objects.select_for_update()
            .select_related(
                "product",
                "location",
            )
            .filter(pk__in=inventory_item_ids)
        )
    }

    if len(inventory_items) != len(set(inventory_item_ids)):
        raise ValidationError(
            {"inventory_item": ("One or more selected inventory items do not exist.")}
        )

    received_quantities = _existing_received_quantities(
        purchase_order_line_ids=line_ids
    )

    validated: list[_ValidatedReceiptLine] = []

    for command in commands:
        order_line = order_lines[command.purchase_order_line_id]
        inventory_item = inventory_items[command.inventory_item_id]

        if command.quantity_received <= Decimal("0.000"):
            raise ValidationError(
                {"quantity_received": ("Received quantity must be greater than zero.")}
            )

        _validate_inventory_target(
            order_line=order_line,
            inventory_item=inventory_item,
        )

        already_received = received_quantities.get(
            order_line.pk,
            Decimal("0.000"),
        )
        remaining = order_line.quantity_ordered - already_received

        if command.quantity_received > remaining:
            raise ValidationError(
                {
                    "quantity_received": (
                        f"Only {remaining} remains "
                        "outstanding for "
                        f"{order_line.product_name_snapshot}."
                    )
                }
            )

        validated.append(
            _ValidatedReceiptLine(
                purchase_order_line=order_line,
                inventory_item=inventory_item,
                quantity_received=(command.quantity_received),
            )
        )

    return validated


def _temporary_receipt_number() -> str:
    """Return a unique pre-save receipt number."""

    return f"TMP-{uuid4().hex[:20].upper()}"


def _movement_reference(
    *,
    purchase_order: PurchaseOrder,
    receipt: GoodsReceipt,
    supplier_reference: str,
) -> str:
    """Return a concise Inventory ledger reference."""

    values = [
        purchase_order.purchase_order_number,
        receipt.goods_receipt_number,
        supplier_reference.strip(),
    ]

    return " / ".join(value for value in values if value)[:120]


def _purchase_order_is_fully_received(
    *,
    purchase_order: PurchaseOrder,
) -> bool:
    """Return whether every order line is complete."""

    order_lines = (
        PurchaseOrderLine.objects.filter(purchase_order=purchase_order)
        .prefetch_related("receipt_lines")
        .order_by("position", "pk")
    )

    for order_line in order_lines:
        received = sum(
            (
                receipt_line.quantity_received
                for receipt_line in order_line.receipt_lines.all()
            ),
            Decimal("0.000"),
        )

        if received < order_line.quantity_ordered:
            return False

    return True


@transaction.atomic
def receive_purchase_order(
    *,
    actor: User,
    command: ReceivePurchaseOrderCommand,
) -> GoodsReceipt:
    """Post a supplier delivery into Inventory."""

    _require_permission(actor=actor)
    _validate_unique_commands(commands=command.lines)

    purchase_order = _get_locked_purchase_order(
        purchase_order_id=(command.purchase_order_id)
    )
    _validate_purchase_order_status(purchase_order=purchase_order)

    validated_lines = _validated_lines(
        purchase_order=purchase_order,
        commands=command.lines,
    )

    receipt = GoodsReceipt(
        goods_receipt_number=(_temporary_receipt_number()),
        purchase_order=purchase_order,
        purchase_order_number_snapshot=(purchase_order.purchase_order_number),
        supplier_number_snapshot=(purchase_order.supplier_number_snapshot),
        supplier_name_snapshot=(purchase_order.supplier_name_snapshot),
        supplier_delivery_reference=(command.supplier_delivery_reference),
        received_at=(command.received_at or timezone.now()),
        notes=command.notes,
        received_by=actor,
    )
    receipt.full_clean()
    receipt.save()

    if receipt.pk is None:
        raise RuntimeError("Goods receipt was saved without a primary key.")

    receipt.goods_receipt_number = f"GRN-{receipt.pk:06d}"
    receipt.save(
        update_fields=(
            "goods_receipt_number",
            "updated_at",
        )
    )

    for validated_line in validated_lines:
        order_line = validated_line.purchase_order_line

        movement = receive_stock(
            actor=actor,
            command=ReceiveStockCommand(
                inventory_item_id=(validated_line.inventory_item.pk),
                quantity=(validated_line.quantity_received),
                unit_cost=order_line.unit_cost,
                currency=purchase_order.currency,
                external_reference=(
                    _movement_reference(
                        purchase_order=(purchase_order),
                        receipt=receipt,
                        supplier_reference=(command.supplier_delivery_reference),
                    )
                ),
                notes=(
                    f"Supplier delivery recorded by {receipt.goods_receipt_number}."
                ),
                occurred_at=receipt.received_at,
            ),
        )

        receipt_line = GoodsReceiptLine(
            goods_receipt=receipt,
            purchase_order_line=order_line,
            inventory_item=(validated_line.inventory_item),
            stock_movement=movement,
            product_sku_snapshot=(order_line.product_sku_snapshot),
            product_name_snapshot=(order_line.product_name_snapshot),
            unit_snapshot=(order_line.unit_snapshot),
            quantity_received=(validated_line.quantity_received),
            unit_cost_snapshot=(order_line.unit_cost),
            currency_snapshot=(purchase_order.currency),
            created_by=actor,
        )
        receipt_line.full_clean()
        receipt_line.save()

    if _purchase_order_is_fully_received(purchase_order=purchase_order):
        purchase_order.status = PurchaseOrderStatus.RECEIVED
    else:
        purchase_order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

    purchase_order.updated_by = actor
    purchase_order.full_clean()
    purchase_order.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    return receipt
