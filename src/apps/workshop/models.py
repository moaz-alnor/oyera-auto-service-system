"""Database models for workshop planning and execution."""

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
    TechnicianAssignmentStatus,
    WorkOrderStatus,
    WorkTaskNoteType,
    WorkTaskStatus,
)


class WorkOrder(TimeStampedModel):
    """Represent workshop execution for one vehicle job."""

    if TYPE_CHECKING:
        job_card_id: int
        approved_quotation_id: int
        tasks: models.Manager["WorkTask"]
        product_requirements: models.Manager["WorkProductRequirement"]

    work_order_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    job_card = models.OneToOneField(
        JobCard,
        on_delete=models.PROTECT,
        related_name="work_order",
    )
    approved_quotation = models.OneToOneField(
        Quotation,
        on_delete=models.PROTECT,
        related_name="work_order",
    )
    status = models.CharField(
        max_length=30,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.PLANNED,
        db_index=True,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    hold_reason = models.TextField(
        blank=True,
    )
    cancellation_reason = models.TextField(
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_orders_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_orders_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure work-order permissions and ordering."""

        ordering = (
            "-created_at",
            "-pk",
        )
        permissions = (
            (
                "start_work_order",
                "Can start a work order",
            ),
            (
                "hold_work_order",
                "Can place a work order on hold",
            ),
            (
                "resume_work_order",
                "Can resume a work order",
            ),
            (
                "complete_work_order",
                "Can complete a work order",
            ),
        )
        indexes = (
            models.Index(
                fields=("status", "created_at"),
                name="work_order_status_idx",
            ),
        )

    def clean(self) -> None:
        """Validate the job, quotation, state, and timestamps."""

        super().clean()

        self.hold_reason = self.hold_reason.strip()
        self.cancellation_reason = self.cancellation_reason.strip()

        try:
            quotation = self.approved_quotation
        except ObjectDoesNotExist:
            return

        if quotation.status != QuotationStatus.APPROVED:
            raise ValidationError(
                {"approved_quotation": ("A work order requires an approved quotation.")}
            )

        if not quotation.is_current:
            raise ValidationError(
                {
                    "approved_quotation": (
                        "The approved quotation must be the current revision."
                    )
                }
            )

        if quotation.job_card_id != self.job_card_id:
            raise ValidationError(
                {
                    "approved_quotation": (
                        "The quotation and work order must belong to the same job card."
                    )
                }
            )

        if self.job_card.status == JobStatus.CANCELLED:
            raise ValidationError(
                {"job_card": ("A cancelled job cannot enter workshop execution.")}
            )

        started_statuses = {
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.ON_HOLD,
            WorkOrderStatus.AWAITING_REVIEW,
            WorkOrderStatus.COMPLETED,
        }

        if self.status in started_statuses and self.started_at is None:
            raise ValidationError(
                {"started_at": ("This work-order status requires a start time.")}
            )

        if self.status == WorkOrderStatus.ON_HOLD and not self.hold_reason:
            raise ValidationError(
                {"hold_reason": ("Record why the work order is on hold.")}
            )

        if self.status == WorkOrderStatus.COMPLETED and self.completed_at is None:
            raise ValidationError(
                {"completed_at": ("A completed work order requires a completion time.")}
            )

        if self.completed_at is not None and self.status != WorkOrderStatus.COMPLETED:
            raise ValidationError(
                {
                    "completed_at": (
                        "Only a completed work order may have a completion time."
                    )
                }
            )

        if self.status == WorkOrderStatus.CANCELLED and not self.cancellation_reason:
            raise ValidationError(
                {"cancellation_reason": ("Record why the work order was cancelled.")}
            )

    def __str__(self) -> str:
        """Return the work-order and job-card numbers."""

        return f"{self.work_order_number} — {self.job_card.job_number}"


class WorkTask(TimeStampedModel):
    """Represent one approved service to be performed."""

    if TYPE_CHECKING:
        work_order_id: int
        source_service_line_id: int
        assignments: models.Manager["TechnicianAssignment"]
        notes: models.Manager["WorkTaskNote"]

    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    source_service_line = models.OneToOneField(
        QuotationServiceLine,
        on_delete=models.PROTECT,
        related_name="work_task",
    )
    position = models.PositiveSmallIntegerField()
    service_code_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    service_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )
    description_snapshot = models.TextField(
        blank=True,
        editable=False,
    )
    approved_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        editable=False,
    )
    approved_unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )
    status = models.CharField(
        max_length=30,
        choices=WorkTaskStatus.choices,
        default=WorkTaskStatus.PENDING,
        db_index=True,
    )
    planned_start_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    planned_completion_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    actual_started_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    actual_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    blocked_reason = models.TextField(
        blank=True,
    )
    completion_notes = models.TextField(
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_tasks_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_tasks_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure work-task permissions and constraints."""

        ordering = (
            "position",
            "pk",
        )
        permissions = (
            (
                "assign_technician",
                "Can assign technicians to work tasks",
            ),
            (
                "start_work_task",
                "Can start a work task",
            ),
            (
                "block_work_task",
                "Can block a work task",
            ),
            (
                "complete_work_task",
                "Can complete a work task",
            ),
        )
        indexes = (
            models.Index(
                fields=("work_order", "status"),
                name="work_task_status_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("work_order", "position"),
                name="work_unique_task_position",
            ),
            models.CheckConstraint(
                condition=Q(approved_quantity__gt=0),
                name="work_task_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(approved_unit_price__gt=0),
                name="work_task_price_positive",
            ),
        )

    def clean(self) -> None:
        """Validate quotation origin and execution state."""

        super().clean()

        self.description_snapshot = self.description_snapshot.strip()
        self.blocked_reason = self.blocked_reason.strip()
        self.completion_notes = self.completion_notes.strip()

        try:
            source_line = self.source_service_line
            work_order = self.work_order
        except ObjectDoesNotExist:
            return

        source_quotation = source_line.quotation

        if source_quotation.status != QuotationStatus.APPROVED:
            raise ValidationError(
                {
                    "source_service_line": (
                        "A work task must originate from an approved quotation."
                    )
                }
            )

        if source_quotation.job_card_id != work_order.job_card_id:
            raise ValidationError(
                {
                    "source_service_line": (
                        "The service line must belong to the "
                        "same job as the work order."
                    )
                }
            )

        started_statuses = {
            WorkTaskStatus.IN_PROGRESS,
            WorkTaskStatus.BLOCKED,
            WorkTaskStatus.AWAITING_REVIEW,
            WorkTaskStatus.COMPLETED,
        }

        if self.status in started_statuses and self.actual_started_at is None:
            raise ValidationError(
                {
                    "actual_started_at": (
                        "This task status requires an actual start time."
                    )
                }
            )

        if self.status == WorkTaskStatus.BLOCKED and not self.blocked_reason:
            raise ValidationError(
                {"blocked_reason": ("Record why the work task is blocked.")}
            )

        if self.status == WorkTaskStatus.COMPLETED and self.actual_completed_at is None:
            raise ValidationError(
                {
                    "actual_completed_at": (
                        "A completed task requires a completion time."
                    )
                }
            )

        if (
            self.actual_completed_at is not None
            and self.status != WorkTaskStatus.COMPLETED
        ):
            raise ValidationError(
                {
                    "actual_completed_at": (
                        "Only a completed task may have an actual completion time."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the work order and service name."""

        return f"{self.work_order.work_order_number} — {self.service_name_snapshot}"


class TechnicianAssignment(TimeStampedModel):
    """Preserve one technician's assignment history."""

    if TYPE_CHECKING:
        work_task_id: int
        technician_id: int

    work_task = models.ForeignKey(
        WorkTask,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workshop_assignments",
    )
    status = models.CharField(
        max_length=20,
        choices=TechnicianAssignmentStatus.choices,
        default=TechnicianAssignmentStatus.ASSIGNED,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="technician_assignments_created",
        editable=False,
    )
    assigned_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    removal_reason = models.TextField(
        blank=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure assignment history and constraints."""

        ordering = (
            "-is_active",
            "-assigned_at",
            "-pk",
        )
        indexes = (
            models.Index(
                fields=("technician", "is_active"),
                name="work_assign_tech_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("work_task", "technician"),
                condition=Q(is_active=True),
                name="work_unique_active_assignment",
            ),
        )

    def clean(self) -> None:
        """Validate technician and assignment state."""

        super().clean()

        self.removal_reason = self.removal_reason.strip()

        try:
            technician = self.technician
        except ObjectDoesNotExist:
            return

        if not technician.is_active:
            raise ValidationError(
                {
                    "technician": (
                        "An inactive employee cannot be assigned to workshop work."
                    )
                }
            )

        if (
            self.status == TechnicianAssignmentStatus.IN_PROGRESS
            and self.started_at is None
        ):
            raise ValidationError(
                {"started_at": ("An in-progress assignment requires a start time.")}
            )

        if (
            self.status == TechnicianAssignmentStatus.COMPLETED
            and self.completed_at is None
        ):
            raise ValidationError(
                {"completed_at": ("A completed assignment requires a completion time.")}
            )

        if self.status == TechnicianAssignmentStatus.REMOVED:
            if self.is_active:
                raise ValidationError(
                    {"is_active": ("A removed assignment cannot remain active.")}
                )

            if self.removed_at is None:
                raise ValidationError(
                    {"removed_at": ("A removed assignment requires a removal time.")}
                )

            if not self.removal_reason:
                raise ValidationError(
                    {"removal_reason": ("Record why the technician was removed.")}
                )

    def __str__(self) -> str:
        """Return technician and work-task details."""

        return f"{self.technician} — {self.work_task.service_name_snapshot}"


class WorkProductRequirement(TimeStampedModel):
    """Preserve approved product demand without changing stock."""

    if TYPE_CHECKING:
        work_order_id: int
        source_product_line_id: int

    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="product_requirements",
    )
    source_product_line = models.OneToOneField(
        QuotationProductLine,
        on_delete=models.PROTECT,
        related_name="work_requirement",
    )
    position = models.PositiveSmallIntegerField()
    product_sku_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )
    product_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )
    unit_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )
    description_snapshot = models.TextField(
        blank=True,
        editable=False,
    )
    approved_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        editable=False,
    )
    approved_unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )
    inventory_status = models.CharField(
        max_length=30,
        choices=ProductRequirementStatus.choices,
        default=ProductRequirementStatus.NOT_RESERVED,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_product_requirements_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure approved product requirements."""

        ordering = (
            "position",
            "pk",
        )
        indexes = (
            models.Index(
                fields=("work_order", "inventory_status"),
                name="work_product_state_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("work_order", "position"),
                name="work_unique_product_position",
            ),
            models.CheckConstraint(
                condition=Q(approved_quantity__gt=0),
                name="work_product_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(approved_unit_price__gt=0),
                name="work_product_price_positive",
            ),
        )

    def clean(self) -> None:
        """Validate the approved quotation origin."""

        super().clean()

        self.description_snapshot = self.description_snapshot.strip()

        try:
            source_line = self.source_product_line
            work_order = self.work_order
        except ObjectDoesNotExist:
            return

        source_quotation = source_line.quotation

        if source_quotation.status != QuotationStatus.APPROVED:
            raise ValidationError(
                {
                    "source_product_line": (
                        "A product requirement must originate "
                        "from an approved quotation."
                    )
                }
            )

        if source_quotation.job_card_id != work_order.job_card_id:
            raise ValidationError(
                {
                    "source_product_line": (
                        "The product line must belong to the "
                        "same job as the work order."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the work order and product name."""

        return f"{self.work_order.work_order_number} — {self.product_name_snapshot}"


class WorkTaskNote(TimeStampedModel):
    """Represent an append-only workshop task note."""

    if TYPE_CHECKING:
        work_task_id: int

        def get_note_type_display(self) -> str:
            """Return the human-readable note-type label."""
            ...

    work_task = models.ForeignKey(
        WorkTask,
        on_delete=models.PROTECT,
        related_name="notes",
    )
    note_type = models.CharField(
        max_length=20,
        choices=WorkTaskNoteType.choices,
        default=WorkTaskNoteType.GENERAL,
    )
    content = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_task_notes_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure append-only note ordering."""

        ordering = (
            "-created_at",
            "-pk",
        )

    def clean(self) -> None:
        """Normalize and validate note content."""

        super().clean()

        self.content = self.content.strip()

        if not self.content:
            raise ValidationError(
                {"content": ("A workshop task note cannot be empty.")}
            )

    def __str__(self) -> str:
        """Return task and note-type information."""

        return f"{self.work_task} — {self.get_note_type_display()}"
