"""Application services for invoice workflows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.calculations import (
    calculate_invoice_totals,
    calculate_line_total,
)
from apps.billing.constants import (
    BillingPermissionName,
    InvoiceStatus,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    InvoiceProductLine,
    InvoiceServiceLine,
    Payment,
)
from apps.inventory.constants import StockMovementType
from apps.inventory.models import StockMovement
from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskStatus,
)
from apps.workshop.models import (
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
)


@dataclass(frozen=True, slots=True)
class CreateInvoiceCommand:
    """Contain initial invoice information."""

    notes: str = ""


@dataclass(frozen=True, slots=True)
class IssueInvoiceCommand:
    """Contain invoice issue information."""

    due_date: date


@dataclass(frozen=True, slots=True)
class VoidInvoiceCommand:
    """Contain an invoice-voiding reason."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: BillingPermissionName,
) -> None:
    """Require one billing permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this billing action."
        )


def _invoice_number(
    *,
    work_order_id: int,
) -> str:
    """Return a readable invoice number."""

    return f"INV-{work_order_id:06d}"


def _net_consumed_quantity(
    *,
    requirement: WorkProductRequirement,
) -> Decimal:
    """Return issued quantity minus returned quantity."""

    issue_total = StockMovement.objects.filter(
        reservation__work_product_requirement=(requirement),
        movement_type=StockMovementType.ISSUE,
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0.000")

    return_total = StockMovement.objects.filter(
        reservation__work_product_requirement=(requirement),
        movement_type=StockMovementType.RETURN,
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0.000")

    quantity = issue_total - return_total

    if quantity < Decimal("0"):
        raise ValidationError(
            {"stock_movements": ("Returned stock cannot exceed issued stock.")}
        )

    return quantity


@transaction.atomic
def create_invoice(
    *,
    actor: User,
    work_order_id: int,
    command: CreateInvoiceCommand,
) -> Invoice:
    """Create a frozen draft invoice from completed work."""

    _require_permission(
        actor=actor,
        permission=BillingPermissionName.ADD_INVOICE,
    )

    try:
        work_order = (
            WorkOrder.objects.select_for_update()
            .select_related(
                "job_card",
                "approved_quotation",
            )
            .get(pk=work_order_id)
        )
    except WorkOrder.DoesNotExist as exc:
        raise ValidationError(
            {"work_order": ("The selected work order does not exist.")}
        ) from exc

    if work_order.status != WorkOrderStatus.COMPLETED:
        raise ValidationError(
            {"work_order": ("Only a completed work order can be invoiced.")}
        )

    if Invoice.objects.filter(work_order=work_order).exists():
        raise ValidationError(
            {"work_order": ("This work order already has an invoice.")}
        )

    tasks = list(
        WorkTask.objects.select_for_update()
        .filter(work_order=work_order)
        .order_by("position", "pk")
    )

    if not tasks:
        raise ValidationError({"work_order": ("The work order has no service tasks.")})

    incomplete_tasks = [
        task for task in tasks if task.status != WorkTaskStatus.COMPLETED
    ]

    if incomplete_tasks:
        raise ValidationError(
            {"work_order": ("All workshop tasks must be completed before invoicing.")}
        )

    requirements = list(
        WorkProductRequirement.objects.select_for_update()
        .filter(work_order=work_order)
        .order_by("position", "pk")
    )

    service_subtotal = sum(
        (
            calculate_line_total(
                quantity=task.approved_quantity,
                unit_price=task.approved_unit_price,
            )
            for task in tasks
        ),
        Decimal("0.00"),
    )

    consumed_products: list[tuple[WorkProductRequirement, Decimal]] = []

    product_subtotal = Decimal("0.00")

    for requirement in requirements:
        consumed_quantity = _net_consumed_quantity(requirement=requirement)

        if consumed_quantity == Decimal("0"):
            continue

        consumed_products.append(
            (
                requirement,
                consumed_quantity,
            )
        )

        product_subtotal += calculate_line_total(
            quantity=consumed_quantity,
            unit_price=requirement.approved_unit_price,
        )

    quotation = work_order.approved_quotation

    totals = calculate_invoice_totals(
        service_subtotal=service_subtotal,
        product_subtotal=product_subtotal,
        discount_percentage=(quotation.discount_percentage),
        tax_percentage=quotation.tax_percentage,
    )

    if totals.total <= Decimal("0"):
        raise ValidationError(
            {"work_order": ("An invoice must have a positive total.")}
        )

    job_card = work_order.job_card

    invoice = Invoice(
        invoice_number=_invoice_number(work_order_id=work_order.pk),
        work_order=work_order,
        status=InvoiceStatus.DRAFT,
        currency=quotation.currency,
        work_order_number_snapshot=(work_order.work_order_number),
        job_number_snapshot=job_card.job_number,
        quotation_number_snapshot=(quotation.quotation_number),
        customer_name_snapshot=(job_card.customer_name_snapshot),
        customer_phone_snapshot=(job_card.customer_phone_snapshot),
        customer_email_snapshot=(job_card.customer_email_snapshot),
        vehicle_registration_snapshot=(job_card.vehicle_registration_snapshot),
        vehicle_make_snapshot=(job_card.vehicle_make_snapshot),
        vehicle_model_snapshot=(job_card.vehicle_model_snapshot),
        vehicle_year_snapshot=(job_card.vehicle_year_snapshot),
        vehicle_color_snapshot=(job_card.vehicle_color_snapshot),
        service_subtotal=totals.service_subtotal,
        product_subtotal=totals.product_subtotal,
        subtotal=totals.subtotal,
        discount_percentage=(quotation.discount_percentage),
        discount_amount=totals.discount_amount,
        taxable_amount=totals.taxable_amount,
        tax_percentage=quotation.tax_percentage,
        tax_amount=totals.tax_amount,
        total=totals.total,
        notes=command.notes,
        created_by=actor,
        updated_by=actor,
    )
    invoice.full_clean()
    invoice.save()

    for task in tasks:
        service_line = InvoiceServiceLine(
            invoice=invoice,
            source_work_task=task,
            position=task.position,
            service_code_snapshot=(task.service_code_snapshot),
            service_name_snapshot=(task.service_name_snapshot),
            description_snapshot=(task.description_snapshot),
            quantity=task.approved_quantity,
            unit_price=task.approved_unit_price,
            created_by=actor,
        )
        service_line.full_clean()
        service_line.save()

    for requirement, consumed_quantity in consumed_products:
        product_line = InvoiceProductLine(
            invoice=invoice,
            source_product_requirement=requirement,
            position=requirement.position,
            product_sku_snapshot=(requirement.product_sku_snapshot),
            product_name_snapshot=(requirement.product_name_snapshot),
            unit_snapshot=requirement.unit_snapshot,
            description_snapshot=(requirement.description_snapshot),
            quantity=consumed_quantity,
            unit_price=(requirement.approved_unit_price),
            created_by=actor,
        )
        product_line.full_clean()
        product_line.save()

    return invoice


@transaction.atomic
def issue_invoice(
    *,
    actor: User,
    invoice_id: int,
    command: IssueInvoiceCommand,
) -> Invoice:
    """Issue a draft invoice to the customer."""

    _require_permission(
        actor=actor,
        permission=BillingPermissionName.ISSUE_INVOICE,
    )

    try:
        invoice = (
            Invoice.objects.select_for_update()
            .select_related(
                "work_order",
                "work_order__approved_quotation",
            )
            .get(pk=invoice_id)
        )
    except Invoice.DoesNotExist as exc:
        raise ValidationError(
            {"invoice": ("The selected invoice does not exist.")}
        ) from exc

    if invoice.status != InvoiceStatus.DRAFT:
        raise ValidationError({"invoice": ("Only a draft invoice can be issued.")})

    issued_at = timezone.now()

    if command.due_date < issued_at.date():
        raise ValidationError({"due_date": ("Payment due date cannot be in the past.")})

    invoice.status = InvoiceStatus.ISSUED
    invoice.issued_at = issued_at
    invoice.due_date = command.due_date
    invoice.updated_by = actor

    invoice.full_clean()
    invoice.save(
        update_fields=(
            "status",
            "issued_at",
            "due_date",
            "updated_by",
            "updated_at",
        )
    )

    return invoice


@transaction.atomic
def void_invoice(
    *,
    actor: User,
    invoice_id: int,
    command: VoidInvoiceCommand,
) -> Invoice:
    """Void an issued invoice with no active payments."""

    _require_permission(
        actor=actor,
        permission=BillingPermissionName.VOID_INVOICE,
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("Record why the invoice is being voided.")})

    try:
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise ValidationError(
            {"invoice": ("The selected invoice does not exist.")}
        ) from exc

    if invoice.status == InvoiceStatus.VOIDED:
        raise ValidationError({"invoice": ("This invoice has already been voided.")})

    if invoice.status != InvoiceStatus.ISSUED:
        raise ValidationError(
            {
                "invoice": (
                    "Only an issued invoice with no posted payments can be voided."
                )
            }
        )

    posted_payment_ids = list(
        Payment.objects.select_for_update()
        .filter(
            invoice=invoice,
            status=PaymentStatus.POSTED,
        )
        .values_list(
            "pk",
            flat=True,
        )
    )

    if posted_payment_ids:
        raise ValidationError(
            {"invoice": ("Void all posted payments before voiding this invoice.")}
        )

    invoice.status = InvoiceStatus.VOIDED
    invoice.voided_at = timezone.now()
    invoice.voided_by = actor
    invoice.void_reason = reason
    invoice.updated_by = actor

    invoice.full_clean()
    invoice.save(
        update_fields=(
            "status",
            "voided_at",
            "voided_by",
            "void_reason",
            "updated_by",
            "updated_at",
        )
    )

    return invoice
