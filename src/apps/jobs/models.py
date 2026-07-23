"""Database models for vehicle-service job cards."""

from django.conf import settings
from django.core.exceptions import ValidationError
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
