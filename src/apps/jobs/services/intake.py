"""Application services for job-card intake and cancellation."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.jobs.constants import (
    ACTIVE_JOB_STATUSES,
    FuelLevel,
    JobPermissionName,
    JobPriority,
    JobStatus,
)
from apps.jobs.models import JobCard
from apps.vehicles.models import Vehicle


@dataclass(frozen=True, slots=True)
class OpenJobCardCommand:
    """Contain validated intake information for a vehicle visit."""

    customer_id: int
    vehicle_id: int
    arrival_mileage: int
    customer_complaint: str
    visible_condition: str = ""
    fuel_level: FuelLevel = FuelLevel.UNKNOWN
    priority: JobPriority = JobPriority.NORMAL
    arrival_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CancelJobCardCommand:
    """Contain the reason for cancelling a job card."""

    reason: str


def _require_permission(
    *,
    actor: User,
    permission: JobPermissionName,
) -> None:
    """Require an employee to hold a job-card permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this job-card action."
        )


def _assign_final_job_number(job_card: JobCard) -> None:
    """Assign a human-readable number using the database key."""

    job_card_id = job_card.pk

    if job_card_id is None:
        raise RuntimeError("The job card must be saved before numbering.")

    job_card.job_number = f"JOB-{job_card_id:06d}"
    job_card.full_clean()
    job_card.save(
        update_fields=(
            "job_number",
            "updated_at",
        )
    )


@transaction.atomic
def open_job_card(
    *,
    actor: User,
    command: OpenJobCardCommand,
) -> JobCard:
    """Open one job card for an active customer and vehicle."""

    _require_permission(
        actor=actor,
        permission=JobPermissionName.ADD_JOB_CARD,
    )

    customer = Customer.objects.select_for_update().get(pk=command.customer_id)
    vehicle = (
        Vehicle.objects.select_for_update()
        .select_related("current_owner")
        .get(pk=command.vehicle_id)
    )

    if not customer.is_active:
        raise ValidationError(
            {"customer": ("A job cannot be opened for an inactive customer.")}
        )

    if not vehicle.is_active:
        raise ValidationError(
            {"vehicle": ("A job cannot be opened for an inactive vehicle.")}
        )

    if vehicle.current_owner.pk != customer.pk:
        raise ValidationError(
            {"customer": ("The selected customer is not the vehicle's current owner.")}
        )

    if (
        vehicle.current_mileage is not None
        and command.arrival_mileage < vehicle.current_mileage
    ):
        raise ValidationError(
            {
                "arrival_mileage": (
                    "Arrival mileage cannot be lower than "
                    f"the vehicle's current mileage of "
                    f"{vehicle.current_mileage}."
                )
            }
        )

    if JobCard.objects.filter(
        vehicle=vehicle,
        status__in=ACTIVE_JOB_STATUSES,
    ).exists():
        raise ValidationError(
            {"vehicle": ("This vehicle already has an active job card.")}
        )

    job_card = JobCard(
        job_number=f"TMP-{uuid4().hex[:24]}",
        customer=customer,
        vehicle=vehicle,
        customer_name_snapshot=customer.name,
        customer_phone_snapshot=customer.phone_number,
        customer_email_snapshot=customer.email,
        vehicle_registration_snapshot=(vehicle.registration_number),
        vehicle_make_snapshot=vehicle.make,
        vehicle_model_snapshot=vehicle.model,
        vehicle_year_snapshot=vehicle.year,
        vehicle_color_snapshot=vehicle.color,
        arrival_at=command.arrival_at or timezone.now(),
        arrival_mileage=command.arrival_mileage,
        customer_complaint=(command.customer_complaint.strip()),
        visible_condition=(command.visible_condition.strip()),
        fuel_level=command.fuel_level,
        priority=command.priority,
        status=JobStatus.OPEN,
        created_by=actor,
        updated_by=actor,
    )

    job_card.full_clean()
    job_card.save()

    _assign_final_job_number(job_card)

    if vehicle.current_mileage != command.arrival_mileage:
        vehicle.current_mileage = command.arrival_mileage
        vehicle.updated_by = actor
        vehicle.save(
            update_fields=(
                "current_mileage",
                "updated_by",
                "updated_at",
            )
        )

    return job_card


@transaction.atomic
def cancel_job_card(
    *,
    actor: User,
    job_card_id: int,
    command: CancelJobCardCommand,
) -> JobCard:
    """Cancel a job card while preserving its history."""

    _require_permission(
        actor=actor,
        permission=JobPermissionName.CANCEL_JOB_CARD,
    )

    job_card = JobCard.objects.select_for_update().get(pk=job_card_id)

    if job_card.status == JobStatus.CANCELLED:
        return job_card

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("A cancellation reason is required.")})

    job_card.status = JobStatus.CANCELLED
    job_card.cancellation_reason = reason
    job_card.updated_by = actor

    job_card.full_clean()
    job_card.save(
        update_fields=(
            "status",
            "cancellation_reason",
            "updated_by",
            "updated_at",
        )
    )

    return job_card
