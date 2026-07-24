"""Application services for workshop task execution."""

from dataclasses import dataclass

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.workshop.constants import (
    TechnicianAssignmentStatus,
    WorkOrderStatus,
    WorkshopPermissionName,
    WorkTaskNoteType,
    WorkTaskStatus,
)
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkTask,
    WorkTaskNote,
)


@dataclass(frozen=True, slots=True)
class StartWorkOrderCommand:
    """Identify the work order that should begin."""

    work_order_id: int


@dataclass(frozen=True, slots=True)
class HoldWorkOrderCommand:
    """Contain a work-order hold request."""

    work_order_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class ResumeWorkOrderCommand:
    """Identify the work order that should resume."""

    work_order_id: int


@dataclass(frozen=True, slots=True)
class StartWorkTaskCommand:
    """Identify the work task that should begin or resume."""

    work_task_id: int


@dataclass(frozen=True, slots=True)
class BlockWorkTaskCommand:
    """Contain a task-blocking request."""

    work_task_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class SubmitWorkTaskForReviewCommand:
    """Contain completed technical work awaiting review."""

    work_task_id: int
    completion_notes: str


@dataclass(frozen=True, slots=True)
class CompleteWorkTaskCommand:
    """Identify a reviewed task that should be approved."""

    work_task_id: int


@dataclass(frozen=True, slots=True)
class CompleteWorkOrderCommand:
    """Identify the reviewed work order to complete."""

    work_order_id: int


@dataclass(frozen=True, slots=True)
class AddWorkTaskNoteCommand:
    """Contain an append-only workshop note."""

    work_task_id: int
    note_type: WorkTaskNoteType
    content: str


def _require_permission(
    *,
    actor: User,
    permission: WorkshopPermissionName,
) -> None:
    """Require one workshop permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied("Your account cannot perform this workshop action.")


def _get_locked_work_order(
    *,
    work_order_id: int,
) -> WorkOrder:
    """Return a locked work order or raise a validation error."""

    try:
        return WorkOrder.objects.select_for_update().get(pk=work_order_id)
    except WorkOrder.DoesNotExist as exc:
        raise ValidationError(
            {"work_order": ("The selected work order does not exist.")}
        ) from exc


def _get_locked_task_and_order(
    *,
    work_task_id: int,
) -> tuple[WorkTask, WorkOrder]:
    """Return a locked task and its locked work order."""

    try:
        work_task = WorkTask.objects.select_for_update().get(pk=work_task_id)
    except WorkTask.DoesNotExist as exc:
        raise ValidationError(
            {"work_task": ("The selected work task does not exist.")}
        ) from exc

    work_order = _get_locked_work_order(work_order_id=work_task.work_order_id)

    return work_task, work_order


def _require_task_access(
    *,
    actor: User,
    work_task: WorkTask,
) -> None:
    """Allow coordinators or an actively assigned technician."""

    can_coordinate = actor.has_perm(WorkshopPermissionName.ASSIGN_TECHNICIAN.value)

    if can_coordinate:
        return

    is_assigned = TechnicianAssignment.objects.filter(
        work_task_id=work_task.pk,
        technician_id=actor.pk,
        is_active=True,
    ).exists()

    if not is_assigned:
        raise PermissionDenied("You may only operate workshop tasks assigned to you.")


def _get_actor_assignment(
    *,
    actor: User,
    work_task: WorkTask,
) -> TechnicianAssignment | None:
    """Return the actor's active assignment when available."""

    return (
        TechnicianAssignment.objects.select_for_update()
        .filter(
            work_task_id=work_task.pk,
            technician_id=actor.pk,
            is_active=True,
        )
        .first()
    )


def _mark_actor_assignment_started(
    *,
    actor: User,
    work_task: WorkTask,
) -> None:
    """Record when an assigned technician begins work."""

    assignment = _get_actor_assignment(
        actor=actor,
        work_task=work_task,
    )

    if assignment is None:
        return

    if assignment.status == TechnicianAssignmentStatus.IN_PROGRESS:
        return

    if assignment.status != TechnicianAssignmentStatus.ASSIGNED:
        raise ValidationError(
            {
                "assignment": (
                    "This technician assignment cannot be started in its current state."
                )
            }
        )

    assignment.status = TechnicianAssignmentStatus.IN_PROGRESS

    if assignment.started_at is None:
        assignment.started_at = timezone.now()

    assignment.full_clean()
    assignment.save(
        update_fields=(
            "status",
            "started_at",
            "updated_at",
        )
    )


def _all_tasks_have_assignments(
    *,
    work_order: WorkOrder,
) -> bool:
    """Return whether every active task has a technician."""

    tasks = list(
        WorkTask.objects.select_for_update()
        .filter(work_order_id=work_order.pk)
        .exclude(status=WorkTaskStatus.CANCELLED)
    )

    return bool(tasks) and all(
        TechnicianAssignment.objects.filter(
            work_task_id=task.pk,
            is_active=True,
        ).exists()
        for task in tasks
    )


def _all_tasks_are_ready_for_review(
    *,
    work_order: WorkOrder,
) -> bool:
    """Return whether every task awaits review or is complete."""

    tasks = list(
        WorkTask.objects.select_for_update()
        .filter(work_order_id=work_order.pk)
        .exclude(status=WorkTaskStatus.CANCELLED)
    )

    review_states = {
        WorkTaskStatus.AWAITING_REVIEW,
        WorkTaskStatus.COMPLETED,
    }

    return bool(tasks) and all(task.status in review_states for task in tasks)


def _all_tasks_are_completed(
    *,
    work_order: WorkOrder,
) -> bool:
    """Return whether every active task is complete."""

    tasks = list(
        WorkTask.objects.select_for_update()
        .filter(work_order_id=work_order.pk)
        .exclude(status=WorkTaskStatus.CANCELLED)
    )

    return bool(tasks) and all(
        task.status == WorkTaskStatus.COMPLETED for task in tasks
    )


def _move_order_to_review_if_ready(
    *,
    actor: User,
    work_order: WorkOrder,
) -> None:
    """Move the order to review after all tasks finish work."""

    if not _all_tasks_are_ready_for_review(work_order=work_order):
        return

    if work_order.status == WorkOrderStatus.AWAITING_REVIEW:
        return

    work_order.status = WorkOrderStatus.AWAITING_REVIEW
    work_order.updated_by = actor
    work_order.full_clean()
    work_order.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )


@transaction.atomic
def start_work_order(
    *,
    actor: User,
    command: StartWorkOrderCommand,
) -> WorkOrder:
    """Start a ready workshop work order."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.START_WORK_ORDER,
    )

    work_order = _get_locked_work_order(work_order_id=command.work_order_id)

    if work_order.status != WorkOrderStatus.READY:
        raise ValidationError(
            {"work_order": ("Only a ready work order can be started.")}
        )

    if not _all_tasks_have_assignments(work_order=work_order):
        raise ValidationError(
            {
                "work_order": (
                    "Every active task requires at least one "
                    "technician before work can start."
                )
            }
        )

    work_order.status = WorkOrderStatus.IN_PROGRESS
    work_order.started_at = timezone.now()
    work_order.hold_reason = ""
    work_order.updated_by = actor
    work_order.full_clean()
    work_order.save(
        update_fields=(
            "status",
            "started_at",
            "hold_reason",
            "updated_by",
            "updated_at",
        )
    )

    return work_order


@transaction.atomic
def hold_work_order(
    *,
    actor: User,
    command: HoldWorkOrderCommand,
) -> WorkOrder:
    """Place an in-progress work order on hold."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.HOLD_WORK_ORDER,
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("Record why the work order is being held.")})

    work_order = _get_locked_work_order(work_order_id=command.work_order_id)

    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        raise ValidationError(
            {"work_order": ("Only an in-progress work order can be placed on hold.")}
        )

    work_order.status = WorkOrderStatus.ON_HOLD
    work_order.hold_reason = reason
    work_order.updated_by = actor
    work_order.full_clean()
    work_order.save(
        update_fields=(
            "status",
            "hold_reason",
            "updated_by",
            "updated_at",
        )
    )

    return work_order


@transaction.atomic
def resume_work_order(
    *,
    actor: User,
    command: ResumeWorkOrderCommand,
) -> WorkOrder:
    """Resume a work order that is on hold."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.RESUME_WORK_ORDER,
    )

    work_order = _get_locked_work_order(work_order_id=command.work_order_id)

    if work_order.status != WorkOrderStatus.ON_HOLD:
        raise ValidationError(
            {"work_order": ("Only a held work order can be resumed.")}
        )

    work_order.status = WorkOrderStatus.IN_PROGRESS
    work_order.hold_reason = ""
    work_order.updated_by = actor
    work_order.full_clean()
    work_order.save(
        update_fields=(
            "status",
            "hold_reason",
            "updated_by",
            "updated_at",
        )
    )

    return work_order


@transaction.atomic
def start_work_task(
    *,
    actor: User,
    command: StartWorkTaskCommand,
) -> WorkTask:
    """Start or resume an assigned workshop task."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.START_WORK_TASK,
    )

    work_task, work_order = _get_locked_task_and_order(
        work_task_id=command.work_task_id
    )

    _require_task_access(
        actor=actor,
        work_task=work_task,
    )

    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        raise ValidationError(
            {
                "work_order": (
                    "Tasks can only operate while the work order is in progress."
                )
            }
        )

    allowed_statuses = {
        WorkTaskStatus.ASSIGNED,
        WorkTaskStatus.BLOCKED,
    }

    if work_task.status not in allowed_statuses:
        raise ValidationError(
            {"work_task": ("This task cannot be started in its current state.")}
        )

    now = timezone.now()

    work_task.status = WorkTaskStatus.IN_PROGRESS
    work_task.blocked_reason = ""

    if work_task.actual_started_at is None:
        work_task.actual_started_at = now

    work_task.updated_by = actor
    work_task.full_clean()
    work_task.save(
        update_fields=(
            "status",
            "blocked_reason",
            "actual_started_at",
            "updated_by",
            "updated_at",
        )
    )

    _mark_actor_assignment_started(
        actor=actor,
        work_task=work_task,
    )

    return work_task


@transaction.atomic
def block_work_task(
    *,
    actor: User,
    command: BlockWorkTaskCommand,
) -> WorkTask:
    """Block an in-progress task with a recorded reason."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.BLOCK_WORK_TASK,
    )

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("Record why the workshop task is blocked.")})

    work_task, work_order = _get_locked_task_and_order(
        work_task_id=command.work_task_id
    )

    _require_task_access(
        actor=actor,
        work_task=work_task,
    )

    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        raise ValidationError(
            {
                "work_order": (
                    "Tasks can only be blocked while the work order is in progress."
                )
            }
        )

    if work_task.status != WorkTaskStatus.IN_PROGRESS:
        raise ValidationError(
            {"work_task": ("Only an in-progress task can be blocked.")}
        )

    work_task.status = WorkTaskStatus.BLOCKED
    work_task.blocked_reason = reason
    work_task.updated_by = actor
    work_task.full_clean()
    work_task.save(
        update_fields=(
            "status",
            "blocked_reason",
            "updated_by",
            "updated_at",
        )
    )

    return work_task


@transaction.atomic
def submit_work_task_for_review(
    *,
    actor: User,
    command: SubmitWorkTaskForReviewCommand,
) -> WorkTask:
    """Submit completed technical work for supervisor review."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.COMPLETE_WORK_TASK,
    )

    completion_notes = command.completion_notes.strip()

    if not completion_notes:
        raise ValidationError(
            {
                "completion_notes": (
                    "Record what was completed before submitting the task for review."
                )
            }
        )

    work_task, work_order = _get_locked_task_and_order(
        work_task_id=command.work_task_id
    )

    _require_task_access(
        actor=actor,
        work_task=work_task,
    )

    if work_order.status != WorkOrderStatus.IN_PROGRESS:
        raise ValidationError(
            {
                "work_order": (
                    "Tasks can only be submitted while the work order is in progress."
                )
            }
        )

    if work_task.status != WorkTaskStatus.IN_PROGRESS:
        raise ValidationError(
            {"work_task": ("Only an in-progress task can be submitted for review.")}
        )

    work_task.status = WorkTaskStatus.AWAITING_REVIEW
    work_task.completion_notes = completion_notes
    work_task.blocked_reason = ""
    work_task.updated_by = actor
    work_task.full_clean()
    work_task.save(
        update_fields=(
            "status",
            "completion_notes",
            "blocked_reason",
            "updated_by",
            "updated_at",
        )
    )

    _move_order_to_review_if_ready(
        actor=actor,
        work_order=work_order,
    )

    return work_task


@transaction.atomic
def complete_work_task(
    *,
    actor: User,
    command: CompleteWorkTaskCommand,
) -> WorkTask:
    """Approve a reviewed task as completed."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.COMPLETE_WORK_TASK,
    )

    if not actor.has_perm(WorkshopPermissionName.ASSIGN_TECHNICIAN.value):
        raise PermissionDenied(
            "Only a workshop coordinator can approve a completed task."
        )

    work_task, work_order = _get_locked_task_and_order(
        work_task_id=command.work_task_id
    )

    if work_order.status not in {
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.AWAITING_REVIEW,
    }:
        raise ValidationError(
            {"work_order": ("This work order is not available for task review.")}
        )

    if work_task.status != WorkTaskStatus.AWAITING_REVIEW:
        raise ValidationError(
            {"work_task": ("Only a task awaiting review can be marked complete.")}
        )

    now = timezone.now()

    work_task.status = WorkTaskStatus.COMPLETED
    work_task.actual_completed_at = now
    work_task.updated_by = actor
    work_task.full_clean()
    work_task.save(
        update_fields=(
            "status",
            "actual_completed_at",
            "updated_by",
            "updated_at",
        )
    )

    assignments = list(
        TechnicianAssignment.objects.select_for_update().filter(
            work_task_id=work_task.pk,
            is_active=True,
        )
    )

    for assignment in assignments:
        assignment.status = TechnicianAssignmentStatus.COMPLETED
        assignment.completed_at = now
        assignment.full_clean()
        assignment.save(
            update_fields=(
                "status",
                "completed_at",
                "updated_at",
            )
        )

    _move_order_to_review_if_ready(
        actor=actor,
        work_order=work_order,
    )

    return work_task


@transaction.atomic
def complete_work_order(
    *,
    actor: User,
    command: CompleteWorkOrderCommand,
) -> WorkOrder:
    """Complete a reviewed work order after every task passes."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.COMPLETE_WORK_ORDER,
    )

    work_order = _get_locked_work_order(work_order_id=command.work_order_id)

    if work_order.status != WorkOrderStatus.AWAITING_REVIEW:
        raise ValidationError(
            {"work_order": ("Only a work order awaiting review can be completed.")}
        )

    if not _all_tasks_are_completed(work_order=work_order):
        raise ValidationError(
            {"work_order": ("Every active task must be approved as complete first.")}
        )

    work_order.status = WorkOrderStatus.COMPLETED
    work_order.completed_at = timezone.now()
    work_order.hold_reason = ""
    work_order.updated_by = actor
    work_order.full_clean()
    work_order.save(
        update_fields=(
            "status",
            "completed_at",
            "hold_reason",
            "updated_by",
            "updated_at",
        )
    )

    return work_order


@transaction.atomic
def add_work_task_note(
    *,
    actor: User,
    command: AddWorkTaskNoteCommand,
) -> WorkTaskNote:
    """Append a note to a workshop task."""

    _require_permission(
        actor=actor,
        permission=WorkshopPermissionName.ADD_TASK_NOTE,
    )

    try:
        work_task = WorkTask.objects.select_for_update().get(pk=command.work_task_id)
    except WorkTask.DoesNotExist as exc:
        raise ValidationError(
            {"work_task": ("The selected work task does not exist.")}
        ) from exc

    _require_task_access(
        actor=actor,
        work_task=work_task,
    )

    note = WorkTaskNote(
        work_task=work_task,
        note_type=command.note_type,
        content=command.content,
        created_by=actor,
    )
    note.full_clean()
    note.save()

    return note
