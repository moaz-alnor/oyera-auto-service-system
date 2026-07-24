"""Tests for workshop workflow forms."""

from typing import cast

import pytest
from django import forms
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.quotations.models import Quotation
from apps.workshop.constants import WorkTaskNoteType
from apps.workshop.forms import (
    TechnicianAssignmentForm,
    TechnicianRemovalForm,
    WorkOrderCreateForm,
    WorkOrderHoldForm,
    WorkTaskBlockForm,
    WorkTaskNoteForm,
    WorkTaskReviewForm,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)
from apps.workshop.tests.conftest import (
    WorkshopExecutionContext,
)


@pytest.mark.django_db
def test_work_order_form_excludes_used_quotation(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """Exclude a quotation already linked to a work order."""

    form = WorkOrderCreateForm()

    field = cast(
        forms.ModelChoiceField,
        form.fields["approved_quotation"],
    )
    approved_quotations = cast(
        QuerySet[Quotation],
        field.queryset,
    )

    assert (
        workshop_execution_context.work_order.approved_quotation
        not in approved_quotations
    )


@pytest.mark.django_db
def test_assignment_form_lists_only_unassigned_technicians(
    workshop_execution_context: WorkshopExecutionContext,
) -> None:
    """List eligible employees and exclude active assignments."""

    task = workshop_execution_context.work_order.tasks.get()

    assign_technician(
        actor=workshop_execution_context.manager,
        command=AssignTechnicianCommand(
            work_task_id=task.pk,
            technician_id=(workshop_execution_context.technician.pk),
        ),
    )

    form = TechnicianAssignmentForm()
    form.configure_for_task(work_task=task)

    field = cast(
        forms.ModelChoiceField,
        form.fields["technician"],
    )
    technicians = cast(
        QuerySet[User],
        field.queryset,
    )

    assert workshop_execution_context.technician not in technicians
    assert workshop_execution_context.second_technician in technicians
    assert workshop_execution_context.receptionist not in technicians


@pytest.mark.django_db
def test_technician_removal_form_requires_reason() -> None:
    """Reject an empty assignment-removal explanation."""

    form = TechnicianRemovalForm({"reason": "   "})

    assert not form.is_valid()
    assert "reason" in form.errors


@pytest.mark.django_db
def test_work_order_hold_form_normalizes_reason() -> None:
    """Strip unnecessary whitespace from a hold reason."""

    form = WorkOrderHoldForm({"reason": ("  Waiting for customer clarification.  ")})

    assert form.is_valid()
    assert form.cleaned_data["reason"] == ("Waiting for customer clarification.")


@pytest.mark.django_db
def test_task_block_form_requires_reason() -> None:
    """Reject a task blocker without an explanation."""

    form = WorkTaskBlockForm({"reason": ""})

    assert not form.is_valid()
    assert "reason" in form.errors


@pytest.mark.django_db
def test_task_review_form_requires_completion_notes() -> None:
    """Require evidence before submitting work for review."""

    form = WorkTaskReviewForm({"completion_notes": "   "})

    assert not form.is_valid()
    assert "completion_notes" in form.errors


@pytest.mark.django_db
def test_task_note_form_normalizes_and_coerces_values() -> None:
    """Return a note enum and normalized content."""

    form = WorkTaskNoteForm(
        {
            "note_type": WorkTaskNoteType.TECHNICAL,
            "content": ("  Front-left pad showed uneven wear.  "),
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["note_type"] == WorkTaskNoteType.TECHNICAL
    assert form.cleaned_data["content"] == ("Front-left pad showed uneven wear.")
