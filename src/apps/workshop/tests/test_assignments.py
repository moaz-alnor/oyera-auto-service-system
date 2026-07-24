"""Tests for workshop technician assignments."""

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.workshop.constants import (
    TechnicianAssignmentStatus,
    WorkOrderStatus,
    WorkTaskStatus,
)
from apps.workshop.models import TechnicianAssignment
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    RemoveTechnicianCommand,
    assign_technician,
    remove_technician,
)
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


@pytest.mark.django_db
def test_manager_assigns_technician_and_marks_order_ready(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Assign a technician and make the work order ready."""

    task = workshop_execution_context.work_order.tasks.get()

    assignment = assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    task.refresh_from_db()
    workshop_execution_context.work_order.refresh_from_db()

    assert assignment.is_active
    assert assignment.status == TechnicianAssignmentStatus.ASSIGNED
    assert assignment.technician == workshop_execution_context.technician
    assert task.status == WorkTaskStatus.ASSIGNED
    assert workshop_execution_context.work_order.status == WorkOrderStatus.READY


@pytest.mark.django_db
def test_task_can_have_multiple_active_technicians(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Allow collaborative technician assignments."""

    task = workshop_execution_context.work_order.tasks.get()

    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )
    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.second_technician.pk),
        ),
    )

    assert (
        TechnicianAssignment.objects.filter(
            work_task=task,
            is_active=True,
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_non_technician_employee_cannot_be_assigned(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Reject employees without a technician role."""

    task = workshop_execution_context.work_order.tasks.get()

    with pytest.raises(
        ValidationError,
        match="Technician or Senior Technician",
    ):
        assign_technician(
            actor=workshop_execution_context.manager,
            command=AssignTechnicianCommand(
                work_task_id=task.pk,
                technician_id=(workshop_execution_context.receptionist.pk),
            ),
        )

    assert not TechnicianAssignment.objects.exists()


@pytest.mark.django_db
def test_duplicate_active_assignment_is_rejected(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Prevent duplicate active technician assignments."""

    task = workshop_execution_context.work_order.tasks.get()

    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    with pytest.raises(
        ValidationError,
        match="already actively assigned",
    ):
        assign_technician(
            actor=workshop_execution_context.manager,
            command=AssignTechnicianCommand(
                work_task_id=task.pk,
                technician_id=(workshop_execution_context.technician.pk),
            ),
        )

    assert TechnicianAssignment.objects.count() == 1


@pytest.mark.django_db
def test_removal_preserves_history_and_allows_reassignment(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Keep removed history and permit a later assignment."""

    task = workshop_execution_context.work_order.tasks.get()

    original = assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    removed = remove_technician(
        actor=workshop_execution_context.manager,
        command=RemoveTechnicianCommand(
            assignment_id=original.pk,
            reason="Technician moved to an urgent repair.",
        ),
    )

    task.refresh_from_db()
    workshop_execution_context.work_order.refresh_from_db()

    assert not removed.is_active
    assert removed.status == TechnicianAssignmentStatus.REMOVED
    assert removed.removed_at is not None
    assert removed.removal_reason == "Technician moved to an urgent repair."
    assert task.status == WorkTaskStatus.PENDING
    assert workshop_execution_context.work_order.status == WorkOrderStatus.PLANNED

    replacement = assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    workshop_execution_context.work_order.refresh_from_db()

    assert replacement.pk != removed.pk
    assert TechnicianAssignment.objects.count() == 2
    assert (
        TechnicianAssignment.objects.filter(
            work_task=task,
            is_active=True,
        ).count()
        == 1
    )
    assert workshop_execution_context.work_order.status == WorkOrderStatus.READY


@pytest.mark.django_db
def test_technician_cannot_coordinate_assignments(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Prevent technicians from assigning other employees."""

    task = workshop_execution_context.work_order.tasks.get()

    with pytest.raises(PermissionDenied):
        assign_technician(
            actor=workshop_execution_context.technician,
            command=AssignTechnicianCommand(
                work_task_id=task.pk,
                technician_id=(workshop_execution_context.second_technician.pk),
            ),
        )

    assert not TechnicianAssignment.objects.exists()
