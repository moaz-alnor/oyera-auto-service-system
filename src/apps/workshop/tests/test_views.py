"""Browser-level tests for workshop workflows."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.workshop.constants import (
    WorkOrderStatus,
    WorkTaskNoteType,
    WorkTaskStatus,
)
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkTask,
    WorkTaskNote,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)
from apps.workshop.services.execution import (
    StartWorkOrderCommand,
    StartWorkTaskCommand,
    SubmitWorkTaskForReviewCommand,
    start_work_order,
    start_work_task,
    submit_work_task_for_review,
)
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)

pytestmark = pytest.mark.django_db


def _get_task(
    *,
    context: WorkshopExecutionContext,
) -> WorkTask:
    """Return the single task created by the shared fixture."""

    return context.work_order.tasks.get()


def _assign_primary_technician(
    *,
    context: WorkshopExecutionContext,
) -> TechnicianAssignment:
    """Assign the fixture's primary technician."""

    task = _get_task(context=context)

    return assign_technician(
        actor=context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=context.technician.pk,
        ),
    )


def _prepare_started_order(
    *,
    context: WorkshopExecutionContext,
) -> WorkTask:
    """Assign the technician and start the work order."""

    task = _get_task(context=context)

    _assign_primary_technician(context=context)

    start_work_order(
        actor=context.manager,
        command=StartWorkOrderCommand(
            work_order_id=context.work_order.pk,
        ),
    )

    return task


def _prepare_started_task(
    *,
    context: WorkshopExecutionContext,
) -> WorkTask:
    """Prepare one task in the in-progress state."""

    task = _prepare_started_order(context=context)

    return start_work_task(
        actor=context.technician,
        command=StartWorkTaskCommand(
            work_task_id=task.pk,
        ),
    )


def _prepare_task_for_review(
    *,
    context: WorkshopExecutionContext,
) -> WorkTask:
    """Prepare one task awaiting supervisor review."""

    task = _prepare_started_task(context=context)

    return submit_work_task_for_review(
        actor=context.technician,
        command=SubmitWorkTaskForReviewCommand(
            work_task_id=task.pk,
            completion_notes=("Repair completed and operational checks passed."),
        ),
    )


def test_employee_can_view_work_order_list_and_detail(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Display workshop records to an authorised employee."""

    client.force_login(workshop_execution_context.technician)

    list_response = client.get(reverse("workshop:list"))
    detail_response = client.get(
        reverse(
            "workshop:detail",
            args=(workshop_execution_context.work_order.pk,),
        )
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200

    assert workshop_execution_context.work_order.work_order_number in (
        list_response.content.decode()
    )
    assert workshop_execution_context.work_order.work_order_number in (
        detail_response.content.decode()
    )


def test_technician_cannot_open_work_order_creation_page(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Prevent ordinary technicians from creating work orders."""

    client.force_login(workshop_execution_context.technician)

    response = client.get(reverse("workshop:create"))

    assert response.status_code == 403


def test_manager_creates_work_order_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Create execution from an available approved quotation."""

    quotation_id = workshop_execution_context.work_order.approved_quotation_id

    existing_work_order = workshop_execution_context.work_order

    existing_work_order.product_requirements.all().delete()
    existing_work_order.tasks.all().delete()
    existing_work_order.delete()

    client.force_login(workshop_execution_context.manager)

    response = client.post(
        reverse("workshop:create"),
        {
            "approved_quotation": quotation_id,
        },
    )

    created_work_order = WorkOrder.objects.get(approved_quotation_id=quotation_id)

    assert response.status_code == 302
    assert response["Location"] == reverse(
        "workshop:detail",
        args=(created_work_order.pk,),
    )
    assert created_work_order.status == WorkOrderStatus.PLANNED
    assert created_work_order.tasks.count() == 1


def test_manager_assigns_technician_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Assign a technician through the workshop form."""

    task = _get_task(context=workshop_execution_context)

    client.force_login(workshop_execution_context.manager)

    response = client.post(
        reverse(
            "workshop:assign_technician",
            args=(task.pk,),
        ),
        {
            "technician": (workshop_execution_context.technician.pk),
        },
    )

    task.refresh_from_db()
    workshop_execution_context.work_order.refresh_from_db()

    assert response.status_code == 302
    assert TechnicianAssignment.objects.filter(
        work_task=task,
        technician=(workshop_execution_context.technician),
        is_active=True,
    ).exists()
    assert task.status == WorkTaskStatus.ASSIGNED
    assert workshop_execution_context.work_order.status == WorkOrderStatus.READY


def test_manager_starts_ready_work_order_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Start an assigned work order through a POST action."""

    _assign_primary_technician(context=workshop_execution_context)

    client.force_login(workshop_execution_context.manager)

    response = client.post(
        reverse(
            "workshop:start",
            args=(workshop_execution_context.work_order.pk,),
        )
    )

    workshop_execution_context.work_order.refresh_from_db()

    assert response.status_code == 302
    assert workshop_execution_context.work_order.status == WorkOrderStatus.IN_PROGRESS
    assert workshop_execution_context.work_order.started_at is not None


def test_assigned_technician_starts_task_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Allow an assigned technician to begin technical work."""

    task = _prepare_started_order(context=workshop_execution_context)

    client.force_login(workshop_execution_context.technician)

    response = client.post(
        reverse(
            "workshop:start_task",
            args=(task.pk,),
        )
    )

    task.refresh_from_db()

    assert response.status_code == 302
    assert task.status == WorkTaskStatus.IN_PROGRESS
    assert task.actual_started_at is not None


def test_unassigned_technician_cannot_start_task_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Reject task execution by an unassigned technician."""

    task = _prepare_started_order(context=workshop_execution_context)

    client.force_login(workshop_execution_context.second_technician)

    response = client.post(
        reverse(
            "workshop:start_task",
            args=(task.pk,),
        )
    )

    task.refresh_from_db()

    assert response.status_code == 403
    assert task.status == WorkTaskStatus.ASSIGNED


def test_technician_blocks_task_from_browser(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Record a blocker through the workshop form."""

    task = _prepare_started_task(context=workshop_execution_context)

    client.force_login(workshop_execution_context.technician)

    get_response = client.get(
        reverse(
            "workshop:block_task",
            args=(task.pk,),
        )
    )
    post_response = client.post(
        reverse(
            "workshop:block_task",
            args=(task.pk,),
        ),
        {
            "reason": ("Replacement part has not arrived."),
        },
    )

    task.refresh_from_db()

    assert get_response.status_code == 200
    assert post_response.status_code == 302
    assert task.status == WorkTaskStatus.BLOCKED
    assert task.blocked_reason == ("Replacement part has not arrived.")


def test_manager_holds_and_resumes_work_order(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Pause and resume workshop execution through HTTP."""

    _prepare_started_order(context=workshop_execution_context)

    work_order = workshop_execution_context.work_order

    client.force_login(workshop_execution_context.manager)

    hold_page = client.get(
        reverse(
            "workshop:hold",
            args=(work_order.pk,),
        )
    )
    hold_response = client.post(
        reverse(
            "workshop:hold",
            args=(work_order.pk,),
        ),
        {
            "reason": ("Waiting for customer clarification."),
        },
    )

    work_order.refresh_from_db()

    assert hold_page.status_code == 200
    assert hold_response.status_code == 302
    assert work_order.status == WorkOrderStatus.ON_HOLD
    assert work_order.hold_reason == ("Waiting for customer clarification.")

    resume_response = client.post(
        reverse(
            "workshop:resume",
            args=(work_order.pk,),
        )
    )

    work_order.refresh_from_db()

    assert resume_response.status_code == 302
    assert work_order.status == WorkOrderStatus.IN_PROGRESS
    assert work_order.hold_reason == ""


def test_technician_submits_task_for_review(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Submit completed technical work through the review form."""

    task = _prepare_started_task(context=workshop_execution_context)

    client.force_login(workshop_execution_context.technician)

    response = client.post(
        reverse(
            "workshop:submit_task_review",
            args=(task.pk,),
        ),
        {
            "completion_notes": ("Brake repair completed and road-tested."),
        },
    )

    task.refresh_from_db()
    workshop_execution_context.work_order.refresh_from_db()

    assert response.status_code == 302
    assert task.status == WorkTaskStatus.AWAITING_REVIEW
    assert task.completion_notes == ("Brake repair completed and road-tested.")
    assert (
        workshop_execution_context.work_order.status == WorkOrderStatus.AWAITING_REVIEW
    )


def test_assigned_technician_adds_task_note(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Append a workshop note through the browser."""

    task = _prepare_started_task(context=workshop_execution_context)

    client.force_login(workshop_execution_context.technician)

    response = client.post(
        reverse(
            "workshop:add_task_note",
            args=(task.pk,),
        ),
        {
            "note_type": WorkTaskNoteType.TECHNICAL.value,
            "content": ("Front-left pad showed uneven wear."),
        },
    )

    note = WorkTaskNote.objects.get(work_task=task)

    assert response.status_code == 302
    assert note.note_type == WorkTaskNoteType.TECHNICAL
    assert note.content == ("Front-left pad showed uneven wear.")
    assert note.created_by == workshop_execution_context.technician


def test_manager_approves_task_and_completes_order(
    client: Client,
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Finish the supervisor review and work-order lifecycle."""

    task = _prepare_task_for_review(context=workshop_execution_context)
    work_order = workshop_execution_context.work_order

    client.force_login(workshop_execution_context.manager)

    approval_response = client.post(
        reverse(
            "workshop:approve_task",
            args=(task.pk,),
        )
    )

    task.refresh_from_db()

    assert approval_response.status_code == 302
    assert task.status == WorkTaskStatus.COMPLETED
    assert task.actual_completed_at is not None

    completion_response = client.post(
        reverse(
            "workshop:complete",
            args=(work_order.pk,),
        )
    )

    work_order.refresh_from_db()

    assert completion_response.status_code == 302
    assert work_order.status == WorkOrderStatus.COMPLETED
    assert work_order.completed_at is not None
