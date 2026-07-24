"""Application services for workshop technician assignments."""

from dataclasses import dataclass

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.workshop.constants import (
    TechnicianAssignmentStatus,
    WorkOrderStatus,
    WorkshopPermissionName,
    WorkTaskStatus,
)
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkTask,
)


@dataclass(frozen=True, slots=True)
class AssignTechnicianCommand:
    """Contain a task and technician assignment request."""

    work_task_id: int
    technician_id: int


@dataclass(frozen=True, slots=True)
class RemoveTechnicianCommand:
    """Contain an assignment-removal request."""

    assignment_id: int
    reason: str


_ASSIGNABLE_WORK_ORDER_STATUSES = {
    WorkOrderStatus.PLANNED,
    WorkOrderStatus.READY,
}

_ASSIGNABLE_TASK_STATUSES = {
    WorkTaskStatus.PENDING,
    WorkTaskStatus.ASSIGNED,
}

_TECHNICIAN_ROLES = {
    RoleName.TECHNICIAN.value,
    RoleName.SENIOR_TECHNICIAN.value,
}


def _require_assignment_permission(
    *,
    actor: User,
) -> None:
    """Require permission to coordinate technicians."""

    if not actor.has_perm(WorkshopPermissionName.ASSIGN_TECHNICIAN.value):
        raise PermissionDenied("Your account cannot assign workshop technicians.")


def _validate_assignment_window(
    *,
    work_order: WorkOrder,
    work_task: WorkTask,
) -> None:
    """Require a task that has not entered execution."""

    if work_order.status not in _ASSIGNABLE_WORK_ORDER_STATUSES:
        raise ValidationError(
            {
                "work_order": (
                    "Technician assignments can only be changed "
                    "before workshop execution starts."
                )
            }
        )

    if work_task.status not in _ASSIGNABLE_TASK_STATUSES:
        raise ValidationError(
            {
                "work_task": (
                    "Technicians cannot be assigned to this task in its current state."
                )
            }
        )


def _validate_technician(
    *,
    technician: User,
) -> None:
    """Require an active technician or senior technician."""

    if not technician.is_active:
        raise ValidationError(
            {
                "technician": (
                    "An inactive employee cannot be assigned to workshop work."
                )
            }
        )

    has_technician_role = technician.groups.filter(name__in=_TECHNICIAN_ROLES).exists()

    if not has_technician_role:
        raise ValidationError(
            {
                "technician": (
                    "Select an employee with the Technician or Senior Technician role."
                )
            }
        )


def _update_task_assignment_state(
    *,
    actor: User,
    work_task: WorkTask,
) -> None:
    """Synchronize the task state with active assignments."""

    has_active_assignment = TechnicianAssignment.objects.filter(
        work_task_id=work_task.pk,
        is_active=True,
    ).exists()

    expected_status = (
        WorkTaskStatus.ASSIGNED if has_active_assignment else WorkTaskStatus.PENDING
    )

    if work_task.status == expected_status:
        return

    work_task.status = expected_status
    work_task.updated_by = actor
    work_task.full_clean()
    work_task.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )


def _update_work_order_readiness(
    *,
    actor: User,
    work_order: WorkOrder,
) -> None:
    """Mark the order ready when every task has a technician."""

    tasks = list(
        WorkTask.objects.select_for_update()
        .filter(work_order_id=work_order.pk)
        .exclude(status=WorkTaskStatus.CANCELLED)
        .order_by("position", "pk")
    )

    every_task_is_assigned = bool(tasks) and all(
        TechnicianAssignment.objects.filter(
            work_task_id=task.pk,
            is_active=True,
        ).exists()
        for task in tasks
    )

    expected_status = (
        WorkOrderStatus.READY if every_task_is_assigned else WorkOrderStatus.PLANNED
    )

    if work_order.status == expected_status:
        return

    work_order.status = expected_status
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
def assign_technician(
    *,
    actor: User,
    command: AssignTechnicianCommand,
) -> TechnicianAssignment:
    """Assign an active technician to a workshop task."""

    _require_assignment_permission(actor=actor)

    try:
        work_task = WorkTask.objects.select_for_update().get(pk=command.work_task_id)
    except WorkTask.DoesNotExist as exc:
        raise ValidationError(
            {"work_task": ("The selected workshop task does not exist.")}
        ) from exc

    work_order = WorkOrder.objects.select_for_update().get(pk=work_task.work_order_id)

    _validate_assignment_window(
        work_order=work_order,
        work_task=work_task,
    )

    try:
        technician = User.objects.select_for_update().get(pk=command.technician_id)
    except User.DoesNotExist as exc:
        raise ValidationError(
            {"technician": ("The selected employee does not exist.")}
        ) from exc

    _validate_technician(technician=technician)

    if TechnicianAssignment.objects.filter(
        work_task_id=work_task.pk,
        technician_id=technician.pk,
        is_active=True,
    ).exists():
        raise ValidationError(
            {
                "technician": (
                    "This technician is already actively assigned to the task."
                )
            }
        )

    assignment = TechnicianAssignment(
        work_task=work_task,
        technician=technician,
        status=TechnicianAssignmentStatus.ASSIGNED,
        is_active=True,
        assigned_by=actor,
    )
    assignment.full_clean()
    assignment.save()

    _update_task_assignment_state(
        actor=actor,
        work_task=work_task,
    )
    _update_work_order_readiness(
        actor=actor,
        work_order=work_order,
    )

    return assignment


@transaction.atomic
def remove_technician(
    *,
    actor: User,
    command: RemoveTechnicianCommand,
) -> TechnicianAssignment:
    """Remove an assignment while preserving its history."""

    _require_assignment_permission(actor=actor)

    reason = command.reason.strip()

    if not reason:
        raise ValidationError({"reason": ("Record why the technician was removed.")})

    try:
        assignment = (
            TechnicianAssignment.objects.select_for_update()
            .select_related(
                "work_task",
                "work_task__work_order",
                "technician",
            )
            .get(pk=command.assignment_id)
        )
    except TechnicianAssignment.DoesNotExist as exc:
        raise ValidationError(
            {"assignment": ("The selected technician assignment does not exist.")}
        ) from exc

    if not assignment.is_active:
        raise ValidationError(
            {"assignment": ("This technician assignment is already inactive.")}
        )

    if assignment.status != TechnicianAssignmentStatus.ASSIGNED:
        raise ValidationError(
            {"assignment": ("Only an assignment that has not started can be removed.")}
        )

    work_task = WorkTask.objects.select_for_update().get(pk=assignment.work_task_id)
    work_order = WorkOrder.objects.select_for_update().get(pk=work_task.work_order_id)

    _validate_assignment_window(
        work_order=work_order,
        work_task=work_task,
    )

    assignment.status = TechnicianAssignmentStatus.REMOVED
    assignment.is_active = False
    assignment.removed_at = timezone.now()
    assignment.removal_reason = reason
    assignment.full_clean()
    assignment.save(
        update_fields=(
            "status",
            "is_active",
            "removed_at",
            "removal_reason",
            "updated_at",
        )
    )

    _update_task_assignment_state(
        actor=actor,
        work_task=work_task,
    )
    _update_work_order_readiness(
        actor=actor,
        work_order=work_order,
    )

    return assignment
