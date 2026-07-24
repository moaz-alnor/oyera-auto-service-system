"""Application services for quotation workflows."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.jobs.constants import JobStatus
from apps.jobs.models import JobCard
from apps.product_catalogue.models import (
    Product,
    ProductPrice,
)
from apps.quotations.calculations import (
    calculate_quotation_totals,
)
from apps.quotations.constants import (
    CustomerDecisionMethod,
    QuotationPermissionName,
    QuotationStatus,
)
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)
from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
    ServicePrice,
)


@dataclass(frozen=True, slots=True)
class CreateQuotationCommand:
    """Contain initial quotation information."""

    currency: str = "UGX"
    discount_percentage: Decimal = Decimal("0.00")
    tax_percentage: Decimal = Decimal("0.00")
    valid_until: date | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class AddServiceLineCommand:
    """Contain one service line request."""

    service_id: int
    quantity: Decimal = Decimal("1.00")
    description_override: str = ""


@dataclass(frozen=True, slots=True)
class AddProductLineCommand:
    """Contain one product line request."""

    product_id: int
    quantity: Decimal = Decimal("1.000")
    description_override: str = ""


@dataclass(frozen=True, slots=True)
class RecordCustomerDecisionCommand:
    """Contain a customer approval or rejection record."""

    customer_name: str
    method: CustomerDecisionMethod
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: QuotationPermissionName,
) -> None:
    """Require a quotation permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this quotation action."
        )


def _quotation_number(
    *,
    job_card_id: int,
    revision_number: int,
) -> str:
    """Return a readable quotation revision number."""

    return f"QTN-{job_card_id:06d}-R{revision_number:02d}"


def _get_locked_quotation(
    *,
    quotation_id: int,
) -> Quotation:
    """Return one locked quotation with its job vehicle."""

    return (
        Quotation.objects.select_for_update()
        .select_related(
            "job_card",
            "job_card__vehicle",
        )
        .get(pk=quotation_id)
    )


def _require_current_draft(
    quotation: Quotation,
) -> None:
    """Require an editable current draft."""

    if quotation.status != QuotationStatus.DRAFT or not quotation.is_current:
        raise ValidationError(
            {"quotation": ("Only the current draft quotation can be modified.")}
        )


def _next_line_position(quotation: Quotation) -> int:
    """Return the next combined line position."""

    return (
        QuotationServiceLine.objects.filter(quotation=quotation).count()
        + QuotationProductLine.objects.filter(quotation=quotation).count()
        + 1
    )


@transaction.atomic
def create_quotation(
    *,
    actor: User,
    job_card_id: int,
    command: CreateQuotationCommand,
) -> Quotation:
    """Create the first quotation revision for a job card."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.ADD_QUOTATION,
    )

    job_card = JobCard.objects.select_for_update().get(pk=job_card_id)

    if job_card.status == JobStatus.CANCELLED:
        raise ValidationError(
            {"job_card": ("A quotation cannot be created for a cancelled job card.")}
        )

    if Quotation.objects.filter(
        job_card=job_card,
        is_current=True,
    ).exists():
        raise ValidationError(
            {"job_card": ("This job already has a current quotation.")}
        )

    quotation = Quotation(
        quotation_number=_quotation_number(
            job_card_id=job_card.pk,
            revision_number=1,
        ),
        job_card=job_card,
        revision_number=1,
        currency=command.currency,
        discount_percentage=(command.discount_percentage),
        tax_percentage=command.tax_percentage,
        valid_until=command.valid_until,
        notes=command.notes,
        status=QuotationStatus.DRAFT,
        is_current=True,
        created_by=actor,
        updated_by=actor,
    )

    quotation.full_clean()
    quotation.save()

    return quotation


@transaction.atomic
def add_service_line(
    *,
    actor: User,
    quotation_id: int,
    command: AddServiceLineCommand,
) -> QuotationServiceLine:
    """Add a service using current catalogue snapshots."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.CHANGE_QUOTATION,
    )

    quotation = _get_locked_quotation(quotation_id=quotation_id)
    _require_current_draft(quotation)

    service = Service.objects.select_for_update().get(pk=command.service_id)

    if not service.is_active:
        raise ValidationError({"service": ("An inactive service cannot be quoted.")})

    vehicle_category = quotation.job_card.vehicle.category

    if not ServiceApplicability.objects.filter(
        service=service,
        vehicle_category=vehicle_category,
    ).exists():
        raise ValidationError(
            {"service": ("This service is not applicable to the job vehicle category.")}
        )

    price = (
        ServicePrice.objects.select_for_update()
        .filter(
            service=service,
            effective_until__isnull=True,
        )
        .first()
    )

    if price is None:
        raise ValidationError(
            {"service": ("The selected service has no current price.")}
        )

    if price.currency != quotation.currency:
        raise ValidationError(
            {
                "service": (
                    "The service price currency does not match the quotation currency."
                )
            }
        )

    line = QuotationServiceLine(
        quotation=quotation,
        service=service,
        position=_next_line_position(quotation),
        service_code_snapshot=service.code,
        service_name_snapshot=service.name,
        description_snapshot=(
            command.description_override.strip() or service.description.strip()
        ),
        quantity=command.quantity,
        unit_price=price.amount,
        created_by=actor,
    )

    line.full_clean()
    line.save()

    return line


@transaction.atomic
def add_product_line(
    *,
    actor: User,
    quotation_id: int,
    command: AddProductLineCommand,
) -> QuotationProductLine:
    """Add a product using current catalogue snapshots."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.CHANGE_QUOTATION,
    )

    quotation = _get_locked_quotation(quotation_id=quotation_id)
    _require_current_draft(quotation)

    product = Product.objects.select_for_update().get(pk=command.product_id)

    if not product.is_active:
        raise ValidationError({"product": ("An inactive product cannot be quoted.")})

    price = (
        ProductPrice.objects.select_for_update()
        .filter(
            product=product,
            effective_until__isnull=True,
        )
        .first()
    )

    if price is None:
        raise ValidationError(
            {"product": ("The selected product has no current price.")}
        )

    if price.currency != quotation.currency:
        raise ValidationError(
            {
                "product": (
                    "The product price currency does not match the quotation currency."
                )
            }
        )

    line = QuotationProductLine(
        quotation=quotation,
        product=product,
        position=_next_line_position(quotation),
        product_sku_snapshot=product.sku,
        product_name_snapshot=product.name,
        unit_snapshot=product.unit,
        description_snapshot=(
            command.description_override.strip() or product.description.strip()
        ),
        quantity=command.quantity,
        unit_price=price.amount,
        created_by=actor,
    )

    line.full_clean()
    line.save()

    return line


@transaction.atomic
def submit_quotation(
    *,
    actor: User,
    quotation_id: int,
) -> Quotation:
    """Submit a complete draft quotation to the customer."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.SUBMIT_QUOTATION,
    )

    quotation = _get_locked_quotation(quotation_id=quotation_id)
    _require_current_draft(quotation)

    has_lines = (
        QuotationServiceLine.objects.filter(quotation=quotation).exists()
        or QuotationProductLine.objects.filter(quotation=quotation).exists()
    )

    if not has_lines:
        raise ValidationError(
            {"quotation": ("Add at least one line before submitting.")}
        )

        totals = calculate_quotation_totals(quotation)

        if totals.total <= Decimal("0"):
            raise ValidationError(
                {"quotation": ("Quotation total must be greater than zero.")}
            )

    quotation.status = QuotationStatus.SENT
    quotation.submitted_at = timezone.now()
    quotation.updated_by = actor

    quotation.full_clean()
    quotation.save(
        update_fields=(
            "status",
            "submitted_at",
            "updated_by",
            "updated_at",
        )
    )

    return quotation


@transaction.atomic
def approve_quotation(
    *,
    actor: User,
    quotation_id: int,
    command: RecordCustomerDecisionCommand,
) -> Quotation:
    """Record customer approval of a submitted quotation."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.APPROVE_QUOTATION,
    )

    quotation = _get_locked_quotation(quotation_id=quotation_id)

    if quotation.status != QuotationStatus.SENT or not quotation.is_current:
        raise ValidationError(
            {"quotation": ("Only the current submitted quotation can be approved.")}
        )

    quotation.status = QuotationStatus.APPROVED
    quotation.decision_at = timezone.now()
    quotation.customer_decision_by_name = command.customer_name
    quotation.decision_method = command.method
    quotation.decision_notes = command.notes
    quotation.decision_recorded_by = actor
    quotation.updated_by = actor

    quotation.full_clean()
    quotation.save(
        update_fields=(
            "status",
            "decision_at",
            "customer_decision_by_name",
            "decision_method",
            "decision_notes",
            "decision_recorded_by",
            "updated_by",
            "updated_at",
        )
    )

    return quotation


@transaction.atomic
def reject_quotation(
    *,
    actor: User,
    quotation_id: int,
    command: RecordCustomerDecisionCommand,
) -> Quotation:
    """Record customer rejection of a submitted quotation."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.REJECT_QUOTATION,
    )

    quotation = _get_locked_quotation(quotation_id=quotation_id)

    if quotation.status != QuotationStatus.SENT or not quotation.is_current:
        raise ValidationError(
            {"quotation": ("Only the current submitted quotation can be rejected.")}
        )

    if not command.notes.strip():
        raise ValidationError({"notes": ("Record the reason for rejection.")})

    quotation.status = QuotationStatus.REJECTED
    quotation.decision_at = timezone.now()
    quotation.customer_decision_by_name = command.customer_name
    quotation.decision_method = command.method
    quotation.decision_notes = command.notes
    quotation.decision_recorded_by = actor
    quotation.updated_by = actor

    quotation.full_clean()
    quotation.save(
        update_fields=(
            "status",
            "decision_at",
            "customer_decision_by_name",
            "decision_method",
            "decision_notes",
            "decision_recorded_by",
            "updated_by",
            "updated_at",
        )
    )

    return quotation


@transaction.atomic
def create_quotation_revision(
    *,
    actor: User,
    quotation_id: int,
) -> Quotation:
    """Create a draft revision while preserving earlier snapshots."""

    _require_permission(
        actor=actor,
        permission=QuotationPermissionName.REVISE_QUOTATION,
    )

    source = _get_locked_quotation(quotation_id=quotation_id)

    if not source.is_current:
        raise ValidationError(
            {"quotation": ("Only the current quotation can be revised.")}
        )

    if source.status not in {
        QuotationStatus.SENT,
        QuotationStatus.REJECTED,
    }:
        raise ValidationError(
            {"quotation": ("Only a sent or rejected quotation can be revised.")}
        )

    next_revision = source.revision_number + 1

    if source.status == QuotationStatus.SENT:
        source.status = QuotationStatus.SUPERSEDED

    source.is_current = False
    source.updated_by = actor
    source.full_clean()
    source.save(
        update_fields=(
            "status",
            "is_current",
            "updated_by",
            "updated_at",
        )
    )

    revision = Quotation(
        quotation_number=_quotation_number(
            job_card_id=source.job_card.pk,
            revision_number=next_revision,
        ),
        job_card=source.job_card,
        revision_number=next_revision,
        status=QuotationStatus.DRAFT,
        is_current=True,
        currency=source.currency,
        discount_percentage=(source.discount_percentage),
        tax_percentage=source.tax_percentage,
        valid_until=source.valid_until,
        notes=source.notes,
        created_by=actor,
        updated_by=actor,
    )

    revision.full_clean()
    revision.save()

    for source_line in QuotationServiceLine.objects.filter(quotation=source):
        copied_line = QuotationServiceLine(
            quotation=revision,
            service=source_line.service,
            position=source_line.position,
            service_code_snapshot=(source_line.service_code_snapshot),
            service_name_snapshot=(source_line.service_name_snapshot),
            description_snapshot=(source_line.description_snapshot),
            quantity=source_line.quantity,
            unit_price=source_line.unit_price,
            created_by=actor,
        )
        copied_line.full_clean()
        copied_line.save()

    for source_line in QuotationProductLine.objects.filter(quotation=source):
        copied_line = QuotationProductLine(
            quotation=revision,
            product=source_line.product,
            position=source_line.position,
            product_sku_snapshot=(source_line.product_sku_snapshot),
            product_name_snapshot=(source_line.product_name_snapshot),
            unit_snapshot=source_line.unit_snapshot,
            description_snapshot=(source_line.description_snapshot),
            quantity=source_line.quantity,
            unit_price=source_line.unit_price,
            created_by=actor,
        )
        copied_line.full_clean()
        copied_line.save()

    return revision
