"""Database models for vehicle-service job cards."""

from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.customers.models import Customer
from apps.jobs.constants import (
    ACTIVE_JOB_STATUSES,
    FuelLevel,
    InspectionType,
    JobNoteType,
    JobPriority,
    JobStatus,
)
from apps.vehicles.models import Vehicle


class JobCard(TimeStampedModel):
    """Represent one vehicle visit to the service business."""

    if TYPE_CHECKING:
        customer_id: int
        vehicle_id: int

    job_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="job_cards",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="job_cards",
    )

    # Historical customer snapshot.
    customer_name_snapshot = models.CharField(
        max_length=200,
        editable=False,
    )
    customer_phone_snapshot = models.CharField(
        max_length=30,
        blank=True,
        editable=False,
    )
    customer_email_snapshot = models.EmailField(
        blank=True,
        editable=False,
    )

    # Historical vehicle snapshot.
    vehicle_registration_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )
    vehicle_make_snapshot = models.CharField(
        max_length=100,
        editable=False,
    )
    vehicle_model_snapshot = models.CharField(
        max_length=100,
        editable=False,
    )
    vehicle_year_snapshot = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        editable=False,
    )
    vehicle_color_snapshot = models.CharField(
        max_length=50,
        blank=True,
        editable=False,
    )

    arrival_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    arrival_mileage = models.PositiveIntegerField()
    customer_complaint = models.TextField()
    visible_condition = models.TextField(
        blank=True,
    )
    fuel_level = models.CharField(
        max_length=20,
        choices=FuelLevel.choices,
        default=FuelLevel.UNKNOWN,
    )
    priority = models.CharField(
        max_length=20,
        choices=JobPriority.choices,
        default=JobPriority.NORMAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.OPEN,
        db_index=True,
    )
    cancellation_reason = models.TextField(
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="job_cards_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="job_cards_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure job-card ordering and business constraints."""

        ordering = (
            "-arrival_at",
            "-created_at",
        )
        permissions = (
            (
                "cancel_jobcard",
                "Can cancel job card",
            ),
        )
        indexes = (
            models.Index(
                fields=("status", "arrival_at"),
                name="jobs_status_arrival_idx",
            ),
            models.Index(
                fields=("customer", "status"),
                name="jobs_customer_status_idx",
            ),
            models.Index(
                fields=("vehicle", "status"),
                name="jobs_vehicle_status_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("vehicle",),
                condition=Q(status__in=ACTIVE_JOB_STATUSES),
                name="jobs_one_active_vehicle",
            ),
        )

    def clean(self) -> None:
        """Validate cancellation-state consistency."""

        super().clean()

        self.cancellation_reason = self.cancellation_reason.strip()

        if self.status == JobStatus.CANCELLED and not self.cancellation_reason:
            raise ValidationError(
                {"cancellation_reason": ("A cancellation reason is required.")}
            )

        if self.status != JobStatus.CANCELLED and self.cancellation_reason:
            raise ValidationError(
                {
                    "cancellation_reason": (
                        "A cancellation reason is only valid for a cancelled job."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the job number and visit vehicle."""

        return f"{self.job_number} — {self.vehicle_registration_snapshot}"


class VehicleRelease(TimeStampedModel):
    """Preserve the final vehicle handover record."""

    if TYPE_CHECKING:
        job_card_id: int
        payment_override_by_id: int | None
        released_by_id: int

    release_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    job_card = models.OneToOneField(
        JobCard,
        on_delete=models.PROTECT,
        related_name="vehicle_release",
    )

    released_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    final_mileage = models.PositiveBigIntegerField()
    final_condition = models.TextField()
    received_by_name = models.CharField(
        max_length=200,
    )
    received_by_contact = models.CharField(
        max_length=100,
        blank=True,
    )
    handover_notes = models.TextField(
        blank=True,
    )

    # Frozen billing snapshots at the moment of release.
    invoice_number_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    invoice_status_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    invoice_currency_snapshot = models.CharField(
        max_length=3,
        editable=False,
    )
    invoice_total_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        editable=False,
    )
    paid_amount_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        editable=False,
    )
    outstanding_amount_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        editable=False,
    )

    payment_override = models.BooleanField(
        default=False,
        editable=False,
    )
    payment_override_reason = models.TextField(
        blank=True,
        editable=False,
    )
    payment_override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_release_payment_overrides",
        null=True,
        blank=True,
        editable=False,
    )
    payment_override_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_releases_recorded",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure release ordering, permissions, and constraints."""

        ordering = (
            "-released_at",
            "-pk",
        )
        permissions = (
            (
                "release_vehicle",
                "Can release a completed vehicle",
            ),
            (
                "override_vehicle_release_payment",
                "Can release a vehicle with an unpaid balance",
            ),
        )
        indexes = (
            models.Index(
                fields=("released_at", "job_card"),
                name="jobs_release_date_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(invoice_total_snapshot__gte=0),
                name="jobs_release_total_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount_snapshot__gte=0),
                name="jobs_release_paid_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(outstanding_amount_snapshot__gte=0),
                name="jobs_release_balance_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(
                    invoice_total_snapshot=(
                        models.F("paid_amount_snapshot")
                        + models.F("outstanding_amount_snapshot")
                    )
                ),
                name="jobs_release_balance_consistent",
            ),
        )

    def clean(self) -> None:
        """Validate handover, mileage, and override consistency."""

        super().clean()

        self.release_number = self.release_number.strip().upper()
        self.final_condition = self.final_condition.strip()
        self.received_by_name = self.received_by_name.strip()
        self.received_by_contact = self.received_by_contact.strip()
        self.handover_notes = self.handover_notes.strip()
        self.invoice_number_snapshot = self.invoice_number_snapshot.strip().upper()
        self.invoice_status_snapshot = self.invoice_status_snapshot.strip().upper()
        self.invoice_currency_snapshot = self.invoice_currency_snapshot.strip().upper()
        self.payment_override_reason = self.payment_override_reason.strip()

        errors: dict[str, str] = {}

        if not self.final_condition:
            errors["final_condition"] = "Record the vehicle condition at handover."

        if not self.received_by_name:
            errors["received_by_name"] = "Record the person receiving the vehicle."

        try:
            job_card = self.job_card
        except ObjectDoesNotExist:
            job_card = None

        if job_card is not None:
            if job_card.status != JobStatus.RELEASED:
                errors["job_card"] = "A vehicle release requires a released job card."

            if self.final_mileage < job_card.arrival_mileage:
                errors["final_mileage"] = (
                    "Final mileage cannot be lower than the arrival mileage."
                )

            current_mileage = job_card.vehicle.current_mileage

            if current_mileage is not None and self.final_mileage < current_mileage:
                errors["final_mileage"] = (
                    "Final mileage cannot be lower than the vehicle's current mileage."
                )

        expected_total = self.paid_amount_snapshot + self.outstanding_amount_snapshot

        if self.invoice_total_snapshot != expected_total:
            errors["outstanding_amount_snapshot"] = (
                "Paid and outstanding amounts must equal the invoice total."
            )

        if (
            self.outstanding_amount_snapshot > Decimal("0.00")
            and not self.payment_override
        ):
            errors["payment_override"] = (
                "An unpaid balance requires an authorised payment override."
            )

        if (
            self.outstanding_amount_snapshot == Decimal("0.00")
            and self.payment_override
        ):
            errors["payment_override"] = (
                "A fully paid invoice does not require a payment override."
            )

        if self.payment_override:
            if not self.payment_override_reason:
                errors["payment_override_reason"] = "Record why payment was overridden."

            if self.payment_override_by_id is None:
                errors["payment_override_by"] = "Record who authorised the override."

            if self.payment_override_at is None:
                errors["payment_override_at"] = (
                    "Record when the override was authorised."
                )
        elif (
            self.payment_override_reason
            or self.payment_override_by_id is not None
            or self.payment_override_at is not None
        ):
            errors["payment_override"] = (
                "Override audit information is only valid "
                "when payment override is enabled."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        """Return the release and job numbers."""

        return f"{self.release_number} — {self.job_card.job_number}"


class Inspection(TimeStampedModel):
    """Preserve an append-only vehicle inspection record."""

    job_card = models.ForeignKey(
        JobCard,
        on_delete=models.PROTECT,
        related_name="inspections",
    )
    inspection_type = models.CharField(
        max_length=30,
        choices=InspectionType.choices,
        default=InspectionType.INITIAL,
    )
    findings = models.TextField()
    safety_observations = models.TextField(
        blank=True,
    )
    recommended_action = models.TextField(
        blank=True,
    )
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="job_inspections",
    )
    inspected_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure inspection ordering."""

        ordering = (
            "-inspected_at",
            "-created_at",
        )
        indexes = (
            models.Index(
                fields=("job_card", "inspected_at"),
                name="jobs_inspection_date_idx",
            ),
        )

    def __str__(self) -> str:
        """Return the job number and inspection type."""

        inspection_label = InspectionType(self.inspection_type).label

        return f"{self.job_card.job_number} — {inspection_label}"


class JobNote(TimeStampedModel):
    """Preserve an append-only note attached to a job card."""

    job_card = models.ForeignKey(
        JobCard,
        on_delete=models.PROTECT,
        related_name="notes",
    )
    note_type = models.CharField(
        max_length=30,
        choices=JobNoteType.choices,
        default=JobNoteType.GENERAL,
    )
    content = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="job_notes_created",
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure note ordering."""

        ordering = (
            "-created_at",
            "-pk",
        )
        indexes = (
            models.Index(
                fields=("job_card", "created_at"),
                name="jobs_note_date_idx",
            ),
        )

    def __str__(self) -> str:
        """Return the job number and note type."""

        note_label = JobNoteType(self.note_type).label

        return f"{self.job_card.job_number} — {note_label}"
