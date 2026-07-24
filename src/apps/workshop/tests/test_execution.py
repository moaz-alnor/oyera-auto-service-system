"""Tests for workshop execution transitions."""

import pytest
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

from apps.workshop.constants import (
    TechnicianAssignmentStatus,
    WorkOrderStatus,
    WorkTaskNoteType,
    WorkTaskStatus,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)
from apps.workshop.services.execution import (
    AddWorkTaskNoteCommand,
    BlockWorkTaskCommand,
    CompleteWorkOrderCommand,
    CompleteWorkTaskCommand,
    HoldWorkOrderCommand,
    ResumeWorkOrderCommand,
    StartWorkOrderCommand,
    StartWorkTaskCommand,
    SubmitWorkTaskForReviewCommand,
    add_work_task_note,
    block_work_task,
    complete_work_order,
    complete_work_task,
    hold_work_order,
    resume_work_order,
    start_work_order,
    start_work_task,
    submit_work_task_for_review,
)
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


def _assign_and_start_order(
    *,
    context: WorkshopExecutionContext,
) -> None:
    """Assign the technician and start workshop execution."""

    task = context.work_order.tasks.get()

    assign_technician(
        actor=context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=context.technician.pk,
        ),
    )

    start_work_order(
        actor=context.manager,
        command=StartWorkOrderCommand(work_order_id=context.work_order.pk),
    )


@pytest.mark.django_db
def test_manager_starts_ready_work_order(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Start a ready order after assigning every task."""

    task = workshop_execution_context.work_order.tasks.get()

    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    work_order = start_work_order(
        actor=workshop_execution_context.manager,
        command=StartWorkOrderCommand(
            work_order_id=(workshop_execution_context.work_order.pk)
        ),
    )

    assert work_order.status == WorkOrderStatus.IN_PROGRESS
    assert work_order.started_at is not None


@pytest.mark.django_db
def test_unassigned_order_cannot_start(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Reject an order that has not reached the ready state."""

    with pytest.raises(
        ValidationError,
        match="Only a ready work order",
    ):
        start_work_order(
            actor=workshop_execution_context.manager,
            command=StartWorkOrderCommand(
                work_order_id=(workshop_execution_context.work_order.pk)
            ),
        )


@pytest.mark.django_db
def test_assigned_technician_starts_task(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Record task and technician start times."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    started_task = start_work_task(
        actor=workshop_execution_context.technician,
        command=StartWorkTaskCommand(work_task_id=task.pk),
    )

    assignment = started_task.assignments.get(
        technician=workshop_execution_context.technician
    )

    assert started_task.status == WorkTaskStatus.IN_PROGRESS
    assert started_task.actual_started_at is not None
    assert assignment.status == TechnicianAssignmentStatus.IN_PROGRESS
    assert assignment.started_at is not None


@pytest.mark.django_db
def test_unassigned_technician_cannot_operate_task(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Restrict task actions to assigned technicians."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    with pytest.raises(
        PermissionDenied,
        match="assigned to you",
    ):
        start_work_task(
            actor=(workshop_execution_context.second_technician),
            command=StartWorkTaskCommand(work_task_id=task.pk),
        )


@pytest.mark.django_db
def test_task_can_be_blocked_and_resumed(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Preserve a blocker and resume the task later."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    start_work_task(
        actor=workshop_execution_context.technician,
        command=StartWorkTaskCommand(work_task_id=task.pk),
    )

    blocked = block_work_task(
        actor=workshop_execution_context.technician,
        command=BlockWorkTaskCommand(
            work_task_id=task.pk,
            reason="Replacement part has not arrived.",
        ),
    )

    assert blocked.status == WorkTaskStatus.BLOCKED
    assert blocked.blocked_reason == "Replacement part has not arrived."

    resumed = start_work_task(
        actor=workshop_execution_context.technician,
        command=StartWorkTaskCommand(work_task_id=task.pk),
    )

    assert resumed.status == WorkTaskStatus.IN_PROGRESS
    assert resumed.blocked_reason == ""


@pytest.mark.django_db
def test_work_order_can_be_held_and_resumed(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Pause and resume the full workshop order."""

    _assign_and_start_order(context=workshop_execution_context)

    held = hold_work_order(
        actor=workshop_execution_context.manager,
        command=HoldWorkOrderCommand(
            work_order_id=(workshop_execution_context.work_order.pk),
            reason="Waiting for customer clarification.",
        ),
    )

    assert held.status == WorkOrderStatus.ON_HOLD
    assert held.hold_reason == "Waiting for customer clarification."

    resumed = resume_work_order(
        actor=workshop_execution_context.manager,
        command=ResumeWorkOrderCommand(
            work_order_id=(workshop_execution_context.work_order.pk)
        ),
    )

    assert resumed.status == WorkOrderStatus.IN_PROGRESS
    assert resumed.hold_reason == ""


@pytest.mark.django_db
def test_task_review_and_supervisor_completion(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Submit technical work and approve it as complete."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    start_work_task(
        actor=workshop_execution_context.technician,
        command=StartWorkTaskCommand(work_task_id=task.pk),
    )

    submitted = submit_work_task_for_review(
        actor=workshop_execution_context.technician,
        command=SubmitWorkTaskForReviewCommand(
            work_task_id=task.pk,
            completion_notes=("Brake components inspected and replaced."),
        ),
    )

    workshop_execution_context.work_order.refresh_from_db()

    assert submitted.status == WorkTaskStatus.AWAITING_REVIEW
    assert (
        workshop_execution_context.work_order.status == WorkOrderStatus.AWAITING_REVIEW
    )

    completed = complete_work_task(
        actor=workshop_execution_context.manager,
        command=CompleteWorkTaskCommand(work_task_id=task.pk),
    )

    assignment = completed.assignments.get(
        technician=workshop_execution_context.technician
    )

    assert completed.status == WorkTaskStatus.COMPLETED
    assert completed.actual_completed_at is not None
    assert assignment.status == TechnicianAssignmentStatus.COMPLETED
    assert assignment.completed_at is not None


@pytest.mark.django_db
def test_manager_completes_reviewed_work_order(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Complete the order after every task passes review."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    start_work_task(
        actor=workshop_execution_context.technician,
        command=StartWorkTaskCommand(work_task_id=task.pk),
    )
    submit_work_task_for_review(
        actor=workshop_execution_context.technician,
        command=SubmitWorkTaskForReviewCommand(
            work_task_id=task.pk,
            completion_notes="Repair completed and tested.",
        ),
    )
    complete_work_task(
        actor=workshop_execution_context.manager,
        command=CompleteWorkTaskCommand(work_task_id=task.pk),
    )

    completed_order = complete_work_order(
        actor=workshop_execution_context.manager,
        command=CompleteWorkOrderCommand(
            work_order_id=(workshop_execution_context.work_order.pk)
        ),
    )

    assert completed_order.status == WorkOrderStatus.COMPLETED
    assert completed_order.completed_at is not None


@pytest.mark.django_db
def test_assigned_technician_adds_append_only_note(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Allow assigned technicians to record technical notes."""

    _assign_and_start_order(context=workshop_execution_context)
    task = workshop_execution_context.work_order.tasks.get()

    note = add_work_task_note(
        actor=workshop_execution_context.technician,
        command=AddWorkTaskNoteCommand(
            work_task_id=task.pk,
            note_type=WorkTaskNoteType.TECHNICAL,
            content=("Front-left brake pad showed uneven wear."),
        ),
    )

    assert note.work_task == task
    assert note.note_type == WorkTaskNoteType.TECHNICAL
    assert note.content == "Front-left brake pad showed uneven wear."
    assert note.created_by == workshop_execution_context.technician
