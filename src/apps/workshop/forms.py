"""Forms for workshop planning and execution workflows."""

from typing import Any

from django import forms

from apps.accounts.models import User
from apps.quotations.models import Quotation
from apps.workshop.constants import WorkTaskNoteType
from apps.workshop.models import WorkTask
from apps.workshop.selectors import (
    get_approved_quotations_available_for_work_order,
    get_available_technicians_for_task,
)


class WorkOrderCreateForm(forms.Form):
    """Select an approved quotation for workshop execution."""

    approved_quotation = forms.ModelChoiceField(
        queryset=Quotation.objects.none(),
        label="Approved quotation",
        empty_label="Select an approved quotation",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load quotations currently eligible for execution."""

        super().__init__(*args, **kwargs)

        field = self.fields["approved_quotation"]

        if isinstance(field, forms.ModelChoiceField):
            field.queryset = get_approved_quotations_available_for_work_order()


class TechnicianAssignmentForm(forms.Form):
    """Select an eligible technician for one work task."""

    technician = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label="Select a technician",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def configure_for_task(
        self,
        *,
        work_task: WorkTask,
    ) -> None:
        """Restrict choices to technicians not already assigned."""

        technician_field = self.fields["technician"]

        if isinstance(
            technician_field,
            forms.ModelChoiceField,
        ):
            technician_field.queryset = get_available_technicians_for_task(
                work_task_id=work_task.pk,
            )


class TechnicianRemovalForm(forms.Form):
    """Collect the reason for removing an assignment."""

    reason = forms.CharField(
        label="Removal reason",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explain why this technician is being removed from the task"
                ),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalize and require the removal reason."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the technician is being removed.")

        return reason


class WorkOrderHoldForm(forms.Form):
    """Collect the reason for placing a work order on hold."""

    reason = forms.CharField(
        label="Hold reason",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why workshop execution must pause"),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalize and require the hold reason."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the work order is being held.")

        return reason


class WorkTaskBlockForm(forms.Form):
    """Collect the reason an active task cannot continue."""

    reason = forms.CharField(
        label="Blocked reason",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Describe the technical, parts, or customer "
                    "issue blocking this task"
                ),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalize and require the blocked reason."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the workshop task is blocked.")

        return reason


class WorkTaskReviewForm(forms.Form):
    """Collect completion evidence before supervisor review."""

    completion_notes = forms.CharField(
        label="Completion notes",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": (
                    "Describe the work completed, checks made, and relevant findings"
                ),
            }
        ),
    )

    def clean_completion_notes(self) -> str:
        """Normalize and require completion evidence."""

        completion_notes = self.cleaned_data["completion_notes"].strip()

        if not completion_notes:
            raise forms.ValidationError("Record what was completed before review.")

        return completion_notes


class WorkTaskNoteForm(forms.Form):
    """Collect an append-only workshop task note."""

    note_type = forms.TypedChoiceField(
        choices=WorkTaskNoteType.choices,
        coerce=WorkTaskNoteType,
        initial=WorkTaskNoteType.GENERAL,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    content = forms.CharField(
        label="Note",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Record a technical observation, blocker, or general workshop note"
                ),
            }
        ),
    )

    def clean_content(self) -> str:
        """Normalize and require note content."""

        content = self.cleaned_data["content"].strip()

        if not content:
            raise forms.ValidationError("A workshop task note cannot be empty.")

        return content
