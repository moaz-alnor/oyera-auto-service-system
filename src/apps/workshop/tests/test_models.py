"""Tests for workshop model validation and display."""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.quotations.constants import QuotationStatus
from apps.quotations.models import Quotation
from apps.workshop.constants import (
    WorkTaskNoteType,
    WorkTaskStatus,
)
from apps.workshop.models import WorkTaskNote
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


@pytest.mark.django_db
def test_work_order_displays_order_and_job_numbers(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Display traceable workshop identifiers."""

    work_order = workshop_execution_context.work_order

    assert str(work_order) == (
        f"{work_order.work_order_number} — {work_order.job_card.job_number}"
    )


@pytest.mark.django_db
def test_work_order_requires_approved_quotation(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Reject a work order whose quotation loses approval."""

    work_order = workshop_execution_context.work_order

    Quotation.objects.filter(pk=work_order.approved_quotation_id).update(
        status=QuotationStatus.SENT
    )

    work_order.refresh_from_db()

    with pytest.raises(
        ValidationError,
        match="requires an approved quotation",
    ):
        work_order.full_clean()


@pytest.mark.django_db
def test_blocked_task_requires_reason(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Require an explanation for blocked technical work."""

    task = workshop_execution_context.work_order.tasks.get()
    task.status = WorkTaskStatus.BLOCKED
    task.actual_started_at = timezone.now()
    task.blocked_reason = "   "

    with pytest.raises(
        ValidationError,
        match="Record why the work task is blocked",
    ):
        task.full_clean()


@pytest.mark.django_db
def test_task_note_cannot_be_empty(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Reject empty append-only workshop notes."""

    task = workshop_execution_context.work_order.tasks.get()

    note = WorkTaskNote(
        work_task=task,
        note_type=WorkTaskNoteType.TECHNICAL,
        content="   ",
        created_by=workshop_execution_context.technician,
    )

    with pytest.raises(
        ValidationError,
        match="cannot be empty",
    ):
        note.full_clean()
