"""Application services for append-only job history."""

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.jobs.constants import (
    InspectionType,
    JobNoteType,
    JobPermissionName,
    JobStatus,
)
from apps.jobs.models import Inspection, JobCard, JobNote


@dataclass(frozen=True, slots=True)
class AddInspectionCommand:
    """Contain one append-only inspection result."""

    inspection_type: InspectionType
    findings: str
    safety_observations: str = ""
    recommended_action: str = ""
    inspected_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AddJobNoteCommand:
    """Contain one append-only job note."""

    note_type: JobNoteType
    content: str


def _require_permission(
    *,
    actor: User,
    permission: JobPermissionName,
) -> None:
    """Require an employee to hold a job-history permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this job-history action."
        )


@transaction.atomic
def add_inspection(
    *,
    actor: User,
    job_card_id: int,
    command: AddInspectionCommand,
) -> Inspection:
    """Append an inspection and mark an open job as inspected."""

    _require_permission(
        actor=actor,
        permission=JobPermissionName.ADD_INSPECTION,
    )

    job_card = JobCard.objects.select_for_update().get(pk=job_card_id)

    if job_card.status == JobStatus.CANCELLED:
        raise ValidationError(
            {"job_card": ("An inspection cannot be added to a cancelled job.")}
        )

    inspection = Inspection(
        job_card=job_card,
        inspection_type=command.inspection_type,
        findings=command.findings.strip(),
        safety_observations=(command.safety_observations.strip()),
        recommended_action=(command.recommended_action.strip()),
        inspected_by=actor,
        inspected_at=command.inspected_at or timezone.now(),
    )

    inspection.full_clean()
    inspection.save()

    if job_card.status == JobStatus.OPEN:
        job_card.status = JobStatus.INSPECTED
        job_card.updated_by = actor
        job_card.save(
            update_fields=(
                "status",
                "updated_by",
                "updated_at",
            )
        )

    return inspection


@transaction.atomic
def add_job_note(
    *,
    actor: User,
    job_card_id: int,
    command: AddJobNoteCommand,
) -> JobNote:
    """Append a note without modifying earlier job history."""

    _require_permission(
        actor=actor,
        permission=JobPermissionName.ADD_JOB_NOTE,
    )

    job_card = JobCard.objects.select_for_update().get(pk=job_card_id)

    note = JobNote(
        job_card=job_card,
        note_type=command.note_type,
        content=command.content.strip(),
        created_by=actor,
    )

    note.full_clean()
    note.save()

    return note
