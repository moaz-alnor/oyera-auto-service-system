"""Application services for vehicle-release workflows."""

from dataclasses import dataclass
from datetime import datetime
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
    InvoiceBalance,
    calculate_invoice_balance,
)
from apps.billing.constants import (
    InvoiceStatus,
    PaymentStatus,
)
from apps.billing.models import (
    Invoice,
    Payment,
)
from apps.jobs.constants import (
    JobPermissionName,
    JobStatus,
)
from apps.jobs.models import (
    JobCard,
    VehicleRelease,
)
from apps.vehicles.models import Vehicle
from apps.workshop.constants import WorkOrderStatus
from apps.workshop.models import WorkOrder


@dataclass(frozen=True, slots=True)
class ReleaseVehicleCommand:
    """Contain final vehicle-handover information."""

    job_card_id: int
    final_mileage: int
    final_condition: str
    received_by_name: str
    received_by_contact: str = ""
    handover_notes: str = ""
    payment_override: bool = False
    payment_override_reason: str = ""
    released_at: datetime | None = None


def _require_permission(
    *,
    actor: User,
    permission: JobPermissionName,
) -> None:
    """Require one vehicle-release permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this vehicle-release action."
        )


def _release_number(
    *,
    job_card_id: int,
) -> str:
    """Return a readable vehicle-release number."""

    return f"REL-{job_card_id:06d}"


def _get_locked_job_card(
    *,
    job_card_id: int,
) -> JobCard:
    """Return a locked job card."""

    try:
        return JobCard.objects.select_for_update().get(pk=job_card_id)
    except JobCard.DoesNotExist as exc:
        raise ValidationError(
            {"job_card": ("The selected job card does not exist.")}
        ) from exc


def _get_locked_work_order(
    *,
    job_card_id: int,
) -> WorkOrder:
    """Return the job's locked work order."""

    try:
        return WorkOrder.objects.select_for_update().get(job_card_id=job_card_id)
    except WorkOrder.DoesNotExist as exc:
        raise ValidationError(
            {"work_order": ("The selected job has no work order.")}
        ) from exc


def _get_locked_invoice(
    *,
    work_order_id: int,
) -> Invoice:
    """Return the work order's locked invoice."""

    try:
        return Invoice.objects.select_for_update().get(work_order_id=work_order_id)
    except Invoice.DoesNotExist as exc:
        raise ValidationError(
            {"invoice": ("The completed work order has no invoice.")}
        ) from exc


def _get_locked_vehicle(
    *,
    vehicle_id: int,
) -> Vehicle:
    """Return the locked vehicle being released."""

    try:
        return Vehicle.objects.select_for_update().get(pk=vehicle_id)
    except Vehicle.DoesNotExist as exc:
        raise ValidationError(
            {"vehicle": ("The job vehicle no longer exists.")}
        ) from exc


def _invoice_balance(
    *,
    invoice: Invoice,
) -> InvoiceBalance:
    """Return the current posted-payment balance."""

    paid_amount = Payment.objects.filter(
        invoice_id=invoice.pk,
        status=PaymentStatus.POSTED,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return calculate_invoice_balance(
        invoice_id=invoice.pk,
        currency=invoice.currency,
        total=invoice.total,
        paid_amount=paid_amount,
    )


def _validate_invoice_state(
    *,
    invoice: Invoice,
    balance: InvoiceBalance,
) -> None:
    """Require an issued invoice with consistent payments."""

    if invoice.issued_at is None:
        raise ValidationError(
            {
                "invoice": (
                    "The invoice must be issued before the vehicle can be released."
                )
            }
        )

    if balance.paid_amount == Decimal("0.00"):
        expected_status = InvoiceStatus.ISSUED
    elif balance.outstanding_amount == Decimal("0.00"):
        expected_status = InvoiceStatus.PAID
    else:
        expected_status = InvoiceStatus.PARTIALLY_PAID

    if invoice.status != expected_status:
        raise ValidationError(
            {
                "invoice": (
                    "The invoice status does not match its posted payment balance."
                )
            }
        )


@transaction.atomic
def release_vehicle(
    *,
    actor: User,
    command: ReleaseVehicleCommand,
) -> VehicleRelease:
    """Close a completed job and record vehicle handover."""

    _require_permission(
        actor=actor,
        permission=JobPermissionName.RELEASE_VEHICLE,
    )

    job_card = _get_locked_job_card(job_card_id=command.job_card_id)

    if VehicleRelease.objects.filter(job_card_id=job_card.pk).exists():
        raise ValidationError({"job_card": ("This vehicle has already been released.")})

    releasable_job_statuses = {
        JobStatus.OPEN,
        JobStatus.INSPECTED,
    }

    if job_card.status not in releasable_job_statuses:
        raise ValidationError(
            {"job_card": ("This job cannot be released in its current state.")}
        )

    work_order = _get_locked_work_order(job_card_id=job_card.pk)

    if work_order.status != WorkOrderStatus.COMPLETED:
        raise ValidationError(
            {
                "work_order": (
                    "The workshop work order must be completed before vehicle release."
                )
            }
        )

    invoice = _get_locked_invoice(work_order_id=work_order.pk)
    balance = _invoice_balance(invoice=invoice)

    _validate_invoice_state(
        invoice=invoice,
        balance=balance,
    )

    override_reason = command.payment_override_reason.strip()

    if balance.is_paid:
        if command.payment_override:
            raise ValidationError(
                {
                    "payment_override": (
                        "A fully paid invoice does not require a payment override."
                    )
                }
            )

        payment_override_by = None
        payment_override_at = None
    else:
        if not command.payment_override:
            raise ValidationError(
                {
                    "payment_override": (
                        "The invoice has an outstanding "
                        "balance. An authorised override "
                        "is required."
                    )
                }
            )

        _require_permission(
            actor=actor,
            permission=(JobPermissionName.OVERRIDE_VEHICLE_RELEASE_PAYMENT),
        )

        if not override_reason:
            raise ValidationError(
                {
                    "payment_override_reason": (
                        "Record why the unpaid vehicle release was authorised."
                    )
                }
            )

        payment_override_by = actor
        payment_override_at = timezone.now()

    released_at = command.released_at or timezone.now()

    if released_at < job_card.arrival_at:
        raise ValidationError(
            {
                "released_at": (
                    "Vehicle release cannot occur before the recorded arrival time."
                )
            }
        )

    vehicle = _get_locked_vehicle(vehicle_id=job_card.vehicle_id)

    current_mileage = vehicle.current_mileage
    minimum_mileage = job_card.arrival_mileage

    if current_mileage is not None:
        minimum_mileage = max(
            minimum_mileage,
            current_mileage,
        )

    if command.final_mileage < minimum_mileage:
        raise ValidationError(
            {
                "final_mileage": (
                    "Final mileage cannot be lower than the arrival or current mileage."
                )
            }
        )

    job_card.vehicle = vehicle
    job_card.status = JobStatus.RELEASED
    job_card.updated_by = actor
    job_card.full_clean()
    job_card.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    vehicle.current_mileage = command.final_mileage
    vehicle.updated_by = actor
    vehicle.full_clean()
    vehicle.save(
        update_fields=(
            "current_mileage",
            "updated_by",
            "updated_at",
        )
    )

    release = VehicleRelease(
        release_number=_release_number(job_card_id=job_card.pk),
        job_card=job_card,
        released_at=released_at,
        final_mileage=command.final_mileage,
        final_condition=command.final_condition,
        received_by_name=command.received_by_name,
        received_by_contact=(command.received_by_contact),
        handover_notes=command.handover_notes,
        invoice_number_snapshot=(invoice.invoice_number),
        invoice_status_snapshot=invoice.status,
        invoice_currency_snapshot=invoice.currency,
        invoice_total_snapshot=balance.total,
        paid_amount_snapshot=balance.paid_amount,
        outstanding_amount_snapshot=(balance.outstanding_amount),
        payment_override=command.payment_override,
        payment_override_reason=override_reason,
        payment_override_by=payment_override_by,
        payment_override_at=payment_override_at,
        released_by=actor,
    )
    release.full_clean()
    release.save()

    return release
