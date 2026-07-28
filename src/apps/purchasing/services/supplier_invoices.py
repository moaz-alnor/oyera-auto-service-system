"""Application services for supplier-invoice workflows."""

from dataclasses import dataclass
from datetime import date
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
from apps.purchasing.calculations import (
    calculate_line_total,
    calculate_supplier_invoice_totals,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    PurchasingPermissionName,
    SupplierInvoiceStatus,
    SupplierPaymentStatus,
)
from apps.purchasing.models import (
    GoodsReceiptLine,
    PurchaseOrder,
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierPayment,
)


@dataclass(frozen=True, slots=True)
class SupplierInvoiceLineCommand:
    """Contain one invoiced received-product line."""

    goods_receipt_line_id: int
    quantity_invoiced: Decimal
    unit_cost: Decimal


@dataclass(frozen=True, slots=True)
class CreateSupplierInvoiceCommand:
    """Contain information for one supplier invoice."""

    purchase_order_id: int
    supplier_reference: str
    invoice_date: date
    due_date: date
    lines: tuple[SupplierInvoiceLineCommand, ...]
    tax_amount: Decimal = Decimal("0.00")
    other_charges: Decimal = Decimal("0.00")
    notes: str = ""


@dataclass(frozen=True, slots=True)
class VoidSupplierInvoiceCommand:
    """Contain supplier-invoice void evidence."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: PurchasingPermissionName,
) -> None:
    """Require one supplier-finance permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this supplier-invoice action."
        )


def _temporary_supplier_invoice_number() -> str:
    """Return a unique number used before persistence."""

    return f"TMP-SINV-{uuid4().hex[:16].upper()}"


def _final_supplier_invoice_number(
    *,
    supplier_invoice_id: int,
) -> str:
    """Return the permanent internal invoice number."""

    return f"SINV-{supplier_invoice_id:06d}"


def _normalise_supplier_reference(
    *,
    supplier_reference: str,
) -> tuple[str, str]:
    """Return display and matching supplier references."""

    display_reference = " ".join(supplier_reference.strip().split())
    normalised_reference = display_reference.casefold()

    if not display_reference:
        raise ValidationError(
            {"supplier_reference": ("Enter the supplier's invoice reference.")}
        )

    return display_reference, normalised_reference


def _get_locked_purchase_order(
    *,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Return one PostgreSQL-safe locked purchase order."""

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


def _require_received_purchase_order(
    *,
    purchase_order: PurchaseOrder,
) -> None:
    """Require an order with received supplier goods."""

    allowed_statuses = {
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
        PurchaseOrderStatus.RECEIVED,
    }

    if purchase_order.status not in allowed_statuses:
        raise ValidationError(
            {
                "purchase_order": (
                    "Supplier invoices require a purchase order with received goods."
                )
            }
        )


def _get_locked_receipt_lines(
    *,
    receipt_line_ids: tuple[int, ...],
) -> dict[int, GoodsReceiptLine]:
    """Return the requested locked receipt lines."""

    if not receipt_line_ids:
        raise ValidationError(
            {"lines": ("Add at least one received product to the supplier invoice.")}
        )

    if len(set(receipt_line_ids)) != len(receipt_line_ids):
        raise ValidationError(
            {
                "lines": (
                    "A goods-receipt line cannot appear "
                    "more than once on the same invoice."
                )
            }
        )

    receipt_lines = list(
        GoodsReceiptLine.objects.select_for_update()
        .select_related(
            "goods_receipt",
            "purchase_order_line",
            "purchase_order_line__product",
        )
        .filter(pk__in=receipt_line_ids)
    )

    if len(receipt_lines) != len(receipt_line_ids):
        raise ValidationError(
            {"lines": ("One or more selected goods-receipt lines do not exist.")}
        )

    return {receipt_line.pk: receipt_line for receipt_line in receipt_lines}


def _already_invoiced_quantity(
    *,
    receipt_line: GoodsReceiptLine,
    exclude_supplier_invoice_id: int | None = None,
) -> Decimal:
    """Return active invoiced quantity for one receipt."""

    queryset = (
        SupplierInvoiceLine.objects.select_for_update()
        .filter(goods_receipt_line=receipt_line)
        .exclude(supplier_invoice__status=(SupplierInvoiceStatus.VOIDED))
    )

    if exclude_supplier_invoice_id is not None:
        queryset = queryset.exclude(supplier_invoice_id=(exclude_supplier_invoice_id))

    return queryset.aggregate(total=Sum("quantity_invoiced"))["total"] or Decimal(
        "0.000"
    )


def _validate_three_way_match(
    *,
    purchase_order: PurchaseOrder,
    receipt_line: GoodsReceiptLine,
    quantity_invoiced: Decimal,
    unit_cost: Decimal,
    exclude_supplier_invoice_id: int | None = None,
) -> Decimal:
    """Validate order, receipt, and invoice agreement."""

    errors: dict[str, str] = {}

    order_line = receipt_line.purchase_order_line

    if receipt_line.goods_receipt.purchase_order_id != purchase_order.pk:
        errors["goods_receipt_line"] = (
            "The goods receipt belongs to a different purchase order."
        )

    if quantity_invoiced <= Decimal("0.000"):
        errors["quantity_invoiced"] = "Invoiced quantity must be greater than zero."

    if unit_cost <= Decimal("0.00"):
        errors["unit_cost"] = "Supplier unit cost must be greater than zero."

    if receipt_line.currency_snapshot != (purchase_order.currency):
        errors["currency"] = (
            "Goods-receipt currency must match the purchase-order currency."
        )

    if unit_cost != order_line.unit_cost:
        errors["unit_cost"] = (
            "Supplier-invoice unit cost must match the purchase-order unit cost."
        )

    if unit_cost != receipt_line.unit_cost_snapshot:
        errors["unit_cost"] = (
            "Supplier-invoice unit cost must match the received unit cost."
        )

    already_invoiced = _already_invoiced_quantity(
        receipt_line=receipt_line,
        exclude_supplier_invoice_id=(exclude_supplier_invoice_id),
    )

    available_quantity = receipt_line.quantity_received - already_invoiced

    if quantity_invoiced > available_quantity:
        errors["quantity_invoiced"] = (
            "Invoiced quantity exceeds the remaining uninvoiced received quantity."
        )

    if errors:
        raise ValidationError(errors)

    return calculate_line_total(
        quantity=quantity_invoiced,
        unit_cost=unit_cost,
    )


@transaction.atomic
def create_supplier_invoice(
    *,
    actor: User,
    command: CreateSupplierInvoiceCommand,
) -> SupplierInvoice:
    """Create a draft invoice from received supplier goods."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.ADD_SUPPLIER_INVOICE),
    )

    purchase_order = _get_locked_purchase_order(
        purchase_order_id=command.purchase_order_id
    )
    _require_received_purchase_order(purchase_order=purchase_order)

    (
        supplier_reference,
        normalised_reference,
    ) = _normalise_supplier_reference(supplier_reference=command.supplier_reference)

    if SupplierInvoice.objects.filter(
        supplier=purchase_order.supplier,
        normalized_supplier_reference=(normalised_reference),
    ).exists():
        raise ValidationError(
            {
                "supplier_reference": (
                    "This supplier invoice reference has already been recorded."
                )
            }
        )

    receipt_line_ids = tuple(line.goods_receipt_line_id for line in command.lines)
    receipt_lines = _get_locked_receipt_lines(receipt_line_ids=receipt_line_ids)

    prepared_lines: list[
        tuple[
            SupplierInvoiceLineCommand,
            GoodsReceiptLine,
            Decimal,
        ]
    ] = []

    for line_command in command.lines:
        receipt_line = receipt_lines[line_command.goods_receipt_line_id]

        line_total = _validate_three_way_match(
            purchase_order=purchase_order,
            receipt_line=receipt_line,
            quantity_invoiced=(line_command.quantity_invoiced),
            unit_cost=line_command.unit_cost,
        )

        prepared_lines.append(
            (
                line_command,
                receipt_line,
                line_total,
            )
        )

    try:
        totals = calculate_supplier_invoice_totals(
            line_totals=(line_total for _, _, line_total in prepared_lines),
            tax_amount=command.tax_amount,
            other_charges=command.other_charges,
        )
    except ValueError as exc:
        raise ValidationError({"totals": str(exc)}) from exc

    if totals.total <= Decimal("0.00"):
        raise ValidationError(
            {"total": ("A supplier invoice must have a positive total.")}
        )

    supplier = purchase_order.supplier

    supplier_invoice = SupplierInvoice(
        supplier_invoice_number=(_temporary_supplier_invoice_number()),
        supplier_reference=supplier_reference,
        normalized_supplier_reference=(normalised_reference),
        supplier=supplier,
        purchase_order=purchase_order,
        purchase_order_number_snapshot=(purchase_order.purchase_order_number),
        supplier_number_snapshot=(purchase_order.supplier_number_snapshot),
        supplier_name_snapshot=(purchase_order.supplier_name_snapshot),
        status=SupplierInvoiceStatus.DRAFT,
        currency=purchase_order.currency,
        invoice_date=command.invoice_date,
        due_date=command.due_date,
        line_subtotal=totals.line_subtotal,
        tax_amount=totals.tax_amount,
        other_charges=totals.other_charges,
        total=totals.total,
        notes=command.notes,
        created_by=actor,
        updated_by=actor,
    )
    supplier_invoice.full_clean()
    supplier_invoice.save()

    supplier_invoice.supplier_invoice_number = _final_supplier_invoice_number(
        supplier_invoice_id=supplier_invoice.pk
    )
    supplier_invoice.full_clean()
    supplier_invoice.save(
        update_fields=(
            "supplier_invoice_number",
            "updated_at",
        )
    )

    for (
        line_command,
        receipt_line,
        line_total,
    ) in prepared_lines:
        purchase_order_line = receipt_line.purchase_order_line

        supplier_invoice_line = SupplierInvoiceLine(
            supplier_invoice=supplier_invoice,
            purchase_order_line=purchase_order_line,
            goods_receipt_line=receipt_line,
            product_sku_snapshot=(receipt_line.product_sku_snapshot),
            product_name_snapshot=(receipt_line.product_name_snapshot),
            unit_snapshot=receipt_line.unit_snapshot,
            quantity_invoiced=(line_command.quantity_invoiced),
            unit_cost=line_command.unit_cost,
            line_total=line_total,
            created_by=actor,
        )
        supplier_invoice_line.full_clean()
        supplier_invoice_line.save()

    return supplier_invoice


def _get_locked_supplier_invoice(
    *,
    supplier_invoice_id: int,
) -> SupplierInvoice:
    """Return one PostgreSQL-safe locked invoice."""

    try:
        return (
            SupplierInvoice.objects.select_for_update()
            .select_related(
                "supplier",
                "purchase_order",
            )
            .get(pk=supplier_invoice_id)
        )
    except SupplierInvoice.DoesNotExist as exc:
        raise ValidationError(
            {"supplier_invoice": ("The selected supplier invoice does not exist.")}
        ) from exc


@transaction.atomic
def post_supplier_invoice(
    *,
    actor: User,
    supplier_invoice_id: int,
) -> SupplierInvoice:
    """Post a fully matched draft supplier invoice."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.POST_SUPPLIER_INVOICE),
    )

    supplier_invoice = _get_locked_supplier_invoice(
        supplier_invoice_id=supplier_invoice_id
    )

    if supplier_invoice.status != SupplierInvoiceStatus.DRAFT:
        raise ValidationError(
            {"supplier_invoice": ("Only a draft supplier invoice can be posted.")}
        )

    lines = list(
        SupplierInvoiceLine.objects.select_for_update()
        .select_related(
            "purchase_order_line",
            "goods_receipt_line",
            "goods_receipt_line__goods_receipt",
        )
        .filter(supplier_invoice=supplier_invoice)
        .order_by(
            "purchase_order_line__position",
            "pk",
        )
    )

    if not lines:
        raise ValidationError(
            {"lines": ("A supplier invoice must contain at least one matched line.")}
        )

    for line in lines:
        line.full_clean()

        _validate_three_way_match(
            purchase_order=(supplier_invoice.purchase_order),
            receipt_line=line.goods_receipt_line,
            quantity_invoiced=line.quantity_invoiced,
            unit_cost=line.unit_cost,
            exclude_supplier_invoice_id=(supplier_invoice.pk),
        )

    totals = calculate_supplier_invoice_totals(
        line_totals=(line.line_total for line in lines),
        tax_amount=supplier_invoice.tax_amount,
        other_charges=(supplier_invoice.other_charges),
    )

    if (
        supplier_invoice.line_subtotal != totals.line_subtotal
        or supplier_invoice.total != totals.total
    ):
        raise ValidationError(
            {"total": ("Supplier-invoice totals no longer match the invoice lines.")}
        )

    supplier_invoice.status = SupplierInvoiceStatus.POSTED
    supplier_invoice.posted_at = timezone.now()
    supplier_invoice.posted_by = actor
    supplier_invoice.updated_by = actor

    supplier_invoice.full_clean()
    supplier_invoice.save(
        update_fields=(
            "status",
            "posted_at",
            "posted_by",
            "updated_by",
            "updated_at",
        )
    )

    return supplier_invoice


@transaction.atomic
def void_supplier_invoice(
    *,
    actor: User,
    supplier_invoice_id: int,
    command: VoidSupplierInvoiceCommand,
) -> SupplierInvoice:
    """Void a posted supplier invoice with no payments."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.VOID_SUPPLIER_INVOICE),
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError(
            {"reason": ("Record why the supplier invoice is being voided.")}
        )

    supplier_invoice = _get_locked_supplier_invoice(
        supplier_invoice_id=supplier_invoice_id
    )

    if supplier_invoice.status == SupplierInvoiceStatus.VOIDED:
        raise ValidationError(
            {"supplier_invoice": ("This supplier invoice has already been voided.")}
        )

    if supplier_invoice.status != SupplierInvoiceStatus.POSTED:
        raise ValidationError(
            {
                "supplier_invoice": (
                    "Only a posted supplier invoice "
                    "with no active payments can be voided."
                )
            }
        )

    active_payment_ids = list(
        SupplierPayment.objects.select_for_update()
        .filter(
            supplier_invoice=supplier_invoice,
            status=SupplierPaymentStatus.POSTED,
        )
        .values_list(
            "pk",
            flat=True,
        )
    )

    if active_payment_ids:
        raise ValidationError(
            {
                "supplier_invoice": (
                    "Void all posted supplier payments before voiding this invoice."
                )
            }
        )

    supplier_invoice.status = SupplierInvoiceStatus.VOIDED
    supplier_invoice.voided_at = timezone.now()
    supplier_invoice.voided_by = actor
    supplier_invoice.void_reason = reason
    supplier_invoice.updated_by = actor

    supplier_invoice.full_clean()
    supplier_invoice.save(
        update_fields=(
            "status",
            "voided_at",
            "voided_by",
            "void_reason",
            "updated_by",
            "updated_at",
        )
    )

    return supplier_invoice
