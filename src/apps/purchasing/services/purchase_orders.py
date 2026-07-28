"""Application services for purchase-order workflows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.models import User
from apps.product_catalogue.models import Product
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    PurchasingPermissionName,
)
from apps.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)


@dataclass(frozen=True, slots=True)
class CreatePurchaseOrderCommand:
    """Contain initial purchase-order information."""

    supplier_id: int
    currency: str = ""
    discount_percentage: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    delivery_cost: Decimal = Decimal("0.00")
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class UpdatePurchaseOrderCommand:
    """Contain replacement draft-order information."""

    supplier_id: int
    currency: str
    discount_percentage: Decimal
    tax_percentage: Decimal
    delivery_cost: Decimal
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class AddPurchaseOrderLineCommand:
    """Contain one product requested from a supplier."""

    product_id: int
    quantity_ordered: Decimal
    unit_cost: Decimal
    description_override: str = ""


@dataclass(frozen=True, slots=True)
class UpdatePurchaseOrderLineCommand:
    """Contain replacement purchase-order line values."""

    quantity_ordered: Decimal
    unit_cost: Decimal
    description_override: str = ""


@dataclass(frozen=True, slots=True)
class CancelPurchaseOrderCommand:
    """Contain purchase-order cancellation evidence."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: PurchasingPermissionName,
) -> None:
    """Require one purchasing permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this purchase-order action."
        )


def _temporary_purchase_order_number() -> str:
    """Return a unique number used before the database ID exists."""

    return f"TMP-{uuid4().hex[:20].upper()}"


def _final_purchase_order_number(
    *,
    purchase_order_id: int,
) -> str:
    """Return the permanent purchase-order number."""

    return f"PO-{purchase_order_id:06d}"


def _get_locked_supplier(
    *,
    supplier_id: int,
) -> Supplier:
    """Return one locked supplier."""

    try:
        return Supplier.objects.select_for_update().get(pk=supplier_id)
    except Supplier.DoesNotExist as exc:
        raise ValidationError(
            {"supplier": ("The selected supplier does not exist.")}
        ) from exc


def _require_active_supplier(
    *,
    supplier: Supplier,
) -> None:
    """Require a supplier that can accept new orders."""

    if not supplier.is_active:
        raise ValidationError(
            {"supplier": ("An inactive supplier cannot receive a purchase order.")}
        )


def _get_locked_purchase_order(
    *,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Return one locked purchase order."""

    try:
        # Lock only the purchase-order row. The nullable audit
        # relationships must not be included in a PostgreSQL
        # FOR UPDATE outer join.
        return (
            PurchaseOrder.objects.select_for_update()
            .select_related("supplier")
            .get(pk=purchase_order_id)
        )
    except PurchaseOrder.DoesNotExist as exc:
        raise ValidationError(
            {"purchase_order": ("The selected purchase order does not exist.")}
        ) from exc


def _require_draft(
    *,
    purchase_order: PurchaseOrder,
) -> None:
    """Require an editable draft purchase order."""

    if purchase_order.status != PurchaseOrderStatus.DRAFT:
        raise ValidationError(
            {"purchase_order": ("Only a draft purchase order can be modified.")}
        )


def _next_line_position(
    *,
    purchase_order: PurchaseOrder,
) -> int:
    """Return the next line position for an order."""

    highest_position = (
        PurchaseOrderLine.objects.filter(purchase_order=purchase_order).aggregate(
            value=Max("position")
        )["value"]
        or 0
    )

    return highest_position + 1


@transaction.atomic
def create_purchase_order(
    *,
    actor: User,
    command: CreatePurchaseOrderCommand,
) -> PurchaseOrder:
    """Create one draft purchase order."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.ADD_PURCHASE_ORDER),
    )

    supplier = _get_locked_supplier(supplier_id=command.supplier_id)
    _require_active_supplier(supplier=supplier)

    currency = command.currency.strip().upper() or supplier.preferred_currency

    purchase_order = PurchaseOrder(
        purchase_order_number=(_temporary_purchase_order_number()),
        supplier=supplier,
        supplier_number_snapshot=(supplier.supplier_number or supplier.code[:20]),
        supplier_code_snapshot=supplier.code,
        supplier_name_snapshot=supplier.name,
        status=PurchaseOrderStatus.DRAFT,
        currency=currency,
        discount_percentage=(command.discount_percentage),
        tax_percentage=command.tax_percentage,
        delivery_cost=command.delivery_cost,
        expected_delivery_date=(command.expected_delivery_date),
        supplier_reference=(command.supplier_reference),
        notes=command.notes,
        created_by=actor,
        updated_by=actor,
    )
    purchase_order.full_clean()
    purchase_order.save()

    if purchase_order.pk is None:
        raise RuntimeError("Purchase-order creation completed without a primary key.")

    purchase_order.purchase_order_number = _final_purchase_order_number(
        purchase_order_id=purchase_order.pk
    )
    purchase_order.save(
        update_fields=(
            "purchase_order_number",
            "updated_at",
        )
    )

    return purchase_order


@transaction.atomic
def update_purchase_order(
    *,
    actor: User,
    purchase_order_id: int,
    command: UpdatePurchaseOrderCommand,
) -> PurchaseOrder:
    """Update one draft purchase-order header."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CHANGE_PURCHASE_ORDER),
    )

    purchase_order = _get_locked_purchase_order(purchase_order_id=purchase_order_id)
    _require_draft(purchase_order=purchase_order)

    supplier = _get_locked_supplier(supplier_id=command.supplier_id)
    _require_active_supplier(supplier=supplier)

    purchase_order.supplier = supplier
    purchase_order.supplier_number_snapshot = (
        supplier.supplier_number or supplier.code[:20]
    )
    purchase_order.supplier_code_snapshot = supplier.code
    purchase_order.supplier_name_snapshot = supplier.name
    purchase_order.currency = command.currency
    purchase_order.discount_percentage = command.discount_percentage
    purchase_order.tax_percentage = command.tax_percentage
    purchase_order.delivery_cost = command.delivery_cost
    purchase_order.expected_delivery_date = command.expected_delivery_date
    purchase_order.supplier_reference = command.supplier_reference
    purchase_order.notes = command.notes
    purchase_order.updated_by = actor

    purchase_order.full_clean()
    purchase_order.save(
        update_fields=(
            "supplier",
            "supplier_number_snapshot",
            "supplier_code_snapshot",
            "supplier_name_snapshot",
            "currency",
            "discount_percentage",
            "tax_percentage",
            "delivery_cost",
            "expected_delivery_date",
            "supplier_reference",
            "notes",
            "updated_by",
            "updated_at",
        )
    )

    return purchase_order


@transaction.atomic
def add_purchase_order_line(
    *,
    actor: User,
    purchase_order_id: int,
    command: AddPurchaseOrderLineCommand,
) -> PurchaseOrderLine:
    """Add one active product to a draft order."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CHANGE_PURCHASE_ORDER),
    )

    purchase_order = _get_locked_purchase_order(purchase_order_id=purchase_order_id)
    _require_draft(purchase_order=purchase_order)

    try:
        product = Product.objects.select_for_update().get(pk=command.product_id)
    except Product.DoesNotExist as exc:
        raise ValidationError(
            {"product": ("The selected product does not exist.")}
        ) from exc

    if not product.is_active:
        raise ValidationError(
            {"product": ("An inactive product cannot be added to a purchase order.")}
        )

    if PurchaseOrderLine.objects.filter(
        purchase_order=purchase_order,
        product=product,
    ).exists():
        raise ValidationError(
            {"product": ("This product is already included in the purchase order.")}
        )

    description = command.description_override.strip() or product.description.strip()

    line = PurchaseOrderLine(
        purchase_order=purchase_order,
        product=product,
        position=_next_line_position(purchase_order=purchase_order),
        product_sku_snapshot=product.sku,
        product_name_snapshot=product.name,
        unit_snapshot=product.unit,
        description_snapshot=description,
        quantity_ordered=(command.quantity_ordered),
        unit_cost=command.unit_cost,
        created_by=actor,
        updated_by=actor,
    )
    line.full_clean()
    line.save()

    return line


@transaction.atomic
def update_purchase_order_line(
    *,
    actor: User,
    purchase_order_line_id: int,
    command: UpdatePurchaseOrderLineCommand,
) -> PurchaseOrderLine:
    """Update quantity, cost and description on a draft line."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CHANGE_PURCHASE_ORDER),
    )

    try:
        line = (
            PurchaseOrderLine.objects.select_for_update()
            .select_related(
                "purchase_order",
                "product",
            )
            .get(pk=purchase_order_line_id)
        )
    except PurchaseOrderLine.DoesNotExist as exc:
        raise ValidationError(
            {
                "purchase_order_line": (
                    "The selected purchase-order line does not exist."
                )
            }
        ) from exc

    _require_draft(purchase_order=line.purchase_order)

    line.quantity_ordered = command.quantity_ordered
    line.unit_cost = command.unit_cost
    line.description_snapshot = (
        command.description_override.strip() or line.product.description.strip()
    )
    line.updated_by = actor

    line.full_clean()
    line.save(
        update_fields=(
            "quantity_ordered",
            "unit_cost",
            "description_snapshot",
            "updated_by",
            "updated_at",
        )
    )

    return line


@transaction.atomic
def remove_purchase_order_line(
    *,
    actor: User,
    purchase_order_line_id: int,
) -> None:
    """Remove one line from a draft purchase order."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CHANGE_PURCHASE_ORDER),
    )

    try:
        line = (
            PurchaseOrderLine.objects.select_for_update()
            .select_related("purchase_order")
            .get(pk=purchase_order_line_id)
        )
    except PurchaseOrderLine.DoesNotExist as exc:
        raise ValidationError(
            {
                "purchase_order_line": (
                    "The selected purchase-order line does not exist."
                )
            }
        ) from exc

    _require_draft(purchase_order=line.purchase_order)

    line.delete()


@transaction.atomic
def submit_purchase_order(
    *,
    actor: User,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Submit a complete draft for management approval."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.SUBMIT_PURCHASE_ORDER),
    )

    purchase_order = _get_locked_purchase_order(purchase_order_id=purchase_order_id)
    _require_draft(purchase_order=purchase_order)

    _require_active_supplier(supplier=purchase_order.supplier)

    if not PurchaseOrderLine.objects.filter(purchase_order=purchase_order).exists():
        raise ValidationError(
            {
                "purchase_order": (
                    "Add at least one product before submitting the purchase order."
                )
            }
        )

    if purchase_order.totals.total <= Decimal("0.00"):
        raise ValidationError(
            {"purchase_order": ("The purchase-order total must be greater than zero.")}
        )

    purchase_order.status = PurchaseOrderStatus.SUBMITTED
    purchase_order.submitted_at = timezone.now()
    purchase_order.submitted_by = actor
    purchase_order.updated_by = actor

    purchase_order.full_clean()
    purchase_order.save(
        update_fields=(
            "status",
            "submitted_at",
            "submitted_by",
            "updated_by",
            "updated_at",
        )
    )

    return purchase_order


@transaction.atomic
def approve_purchase_order(
    *,
    actor: User,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Approve one submitted purchase order."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.APPROVE_PURCHASE_ORDER),
    )

    purchase_order = _get_locked_purchase_order(purchase_order_id=purchase_order_id)

    if purchase_order.status != PurchaseOrderStatus.SUBMITTED:
        raise ValidationError(
            {"purchase_order": ("Only a submitted purchase order can be approved.")}
        )

    _require_active_supplier(supplier=purchase_order.supplier)

    purchase_order.status = PurchaseOrderStatus.APPROVED
    purchase_order.approved_at = timezone.now()
    purchase_order.approved_by = actor
    purchase_order.updated_by = actor

    purchase_order.full_clean()
    purchase_order.save(
        update_fields=(
            "status",
            "approved_at",
            "approved_by",
            "updated_by",
            "updated_at",
        )
    )

    return purchase_order


@transaction.atomic
def cancel_purchase_order(
    *,
    actor: User,
    purchase_order_id: int,
    command: CancelPurchaseOrderCommand,
) -> PurchaseOrder:
    """Cancel an unreceived purchase order."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CANCEL_PURCHASE_ORDER),
    )

    purchase_order = _get_locked_purchase_order(purchase_order_id=purchase_order_id)

    if purchase_order.status == PurchaseOrderStatus.CANCELLED:
        return purchase_order

    if purchase_order.status in {
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
        PurchaseOrderStatus.RECEIVED,
    }:
        raise ValidationError(
            {
                "purchase_order": (
                    "A partially or fully received purchase order cannot be cancelled."
                )
            }
        )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError(
            {"reason": ("Record why the purchase order was cancelled.")}
        )

    purchase_order.status = PurchaseOrderStatus.CANCELLED
    purchase_order.cancelled_at = timezone.now()
    purchase_order.cancelled_by = actor
    purchase_order.cancellation_reason = reason
    purchase_order.updated_by = actor

    purchase_order.full_clean()
    purchase_order.save(
        update_fields=(
            "status",
            "cancelled_at",
            "cancelled_by",
            "cancellation_reason",
            "updated_by",
            "updated_at",
        )
    )

    return purchase_order
