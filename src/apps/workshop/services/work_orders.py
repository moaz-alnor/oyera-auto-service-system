"""Application services for workshop work orders."""

from dataclasses import dataclass
from uuid import uuid4

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from apps.accounts.models import User
from apps.jobs.constants import JobStatus
from apps.jobs.models import JobCard
from apps.quotations.constants import QuotationStatus
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)
from apps.workshop.constants import (
    ProductRequirementStatus,
    WorkOrderStatus,
    WorkshopPermissionName,
    WorkTaskStatus,
)
from apps.workshop.models import (
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
)


@dataclass(frozen=True, slots=True)
class CreateWorkOrderCommand:
    """Contain the approved quotation used for execution."""

    approved_quotation_id: int


def _require_permission(
    *,
    actor: User,
    permission: WorkshopPermissionName,
) -> None:
    """Require one workshop permission from an employee."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied("Your account cannot perform this workshop action.")


def _validate_work_order_source(
    *,
    quotation: Quotation,
    job_card: JobCard,
    service_lines: list[QuotationServiceLine],
) -> None:
    """Validate an approved quotation before execution."""

    if quotation.status != QuotationStatus.APPROVED:
        raise ValidationError(
            {
                "approved_quotation": (
                    "Only an approved quotation can create a work order."
                )
            }
        )

    if not quotation.is_current:
        raise ValidationError(
            {
                "approved_quotation": (
                    "The approved quotation must be the current revision."
                )
            }
        )

    if job_card.status == JobStatus.CANCELLED:
        raise ValidationError(
            {"job_card": ("A cancelled job cannot enter workshop execution.")}
        )

    if WorkOrder.objects.filter(job_card_id=job_card.pk).exists():
        raise ValidationError(
            {"job_card": ("This job already has a workshop work order.")}
        )

    if WorkOrder.objects.filter(approved_quotation_id=quotation.pk).exists():
        raise ValidationError(
            {
                "approved_quotation": (
                    "This quotation already has a workshop work order."
                )
            }
        )

    if not service_lines:
        raise ValidationError(
            {
                "approved_quotation": (
                    "A workshop work order requires at least one approved service line."
                )
            }
        )


def _create_service_tasks(
    *,
    actor: User,
    work_order: WorkOrder,
    service_lines: list[QuotationServiceLine],
) -> None:
    """Copy approved service snapshots into work tasks."""

    for line in service_lines:
        task = WorkTask(
            work_order=work_order,
            source_service_line=line,
            position=line.position,
            service_code_snapshot=(line.service_code_snapshot),
            service_name_snapshot=(line.service_name_snapshot),
            description_snapshot=(line.description_snapshot),
            approved_quantity=line.quantity,
            approved_unit_price=line.unit_price,
            status=WorkTaskStatus.PENDING,
            created_by=actor,
            updated_by=actor,
        )
        task.full_clean()
        task.save()


def _create_product_requirements(
    *,
    actor: User,
    work_order: WorkOrder,
    product_lines: list[QuotationProductLine],
) -> None:
    """Copy approved product demand without changing stock."""

    for line in product_lines:
        requirement = WorkProductRequirement(
            work_order=work_order,
            source_product_line=line,
            position=line.position,
            product_sku_snapshot=(line.product_sku_snapshot),
            product_name_snapshot=(line.product_name_snapshot),
            unit_snapshot=line.unit_snapshot,
            description_snapshot=(line.description_snapshot),
            approved_quantity=line.quantity,
            approved_unit_price=line.unit_price,
            inventory_status=(ProductRequirementStatus.NOT_RESERVED),
            created_by=actor,
        )
        requirement.full_clean()
        requirement.save()


@transaction.atomic
def create_work_order(
    *,
    actor: User,
    command: CreateWorkOrderCommand,
) -> WorkOrder:
    """Create workshop execution from an approved quotation.

    The service copies the approved commercial snapshots into
    workshop records. It does not change quotation lines or
    catalogue prices, and it does not reserve or issue inventory.
    """

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.ADD_WORK_ORDER,
    )

    try:
        quotation = (
            Quotation.objects.select_for_update()
            .select_related("job_card")
            .get(pk=command.approved_quotation_id)
        )
    except Quotation.DoesNotExist as exc:
        raise ValidationError(
            {"approved_quotation": ("The selected quotation does not exist.")}
        ) from exc

    job_card = JobCard.objects.select_for_update().get(pk=quotation.job_card_id)

    service_lines = list(
        QuotationServiceLine.objects.select_for_update()
        .filter(quotation=quotation)
        .order_by("position", "pk")
    )
    product_lines = list(
        QuotationProductLine.objects.select_for_update()
        .filter(quotation=quotation)
        .order_by("position", "pk")
    )

    _validate_work_order_source(
        quotation=quotation,
        job_card=job_card,
        service_lines=service_lines,
    )

    temporary_number = f"TMP-{uuid4().hex[:20].upper()}"

    work_order = WorkOrder(
        work_order_number=temporary_number,
        job_card=job_card,
        approved_quotation=quotation,
        status=WorkOrderStatus.PLANNED,
        created_by=actor,
        updated_by=actor,
    )
    work_order.full_clean()
    work_order.save()

    if work_order.pk is None:
        raise RuntimeError("The work order was saved without a primary key.")

    work_order.work_order_number = f"WO-{work_order.pk:06d}"
    work_order.save(
        update_fields=(
            "work_order_number",
            "updated_by",
            "updated_at",
        )
    )

    _create_service_tasks(
        actor=actor,
        work_order=work_order,
        service_lines=service_lines,
    )
    _create_product_requirements(
        actor=actor,
        work_order=work_order,
        product_lines=product_lines,
    )

    return work_order
