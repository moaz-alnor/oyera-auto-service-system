"""Constants and permission identifiers for job-card workflows."""

from enum import StrEnum

from django.db import models


class JobStatus(models.TextChoices):
    """Identify the operational state of a job card."""

    OPEN = "OPEN", "Open"
    INSPECTED = "INSPECTED", "Inspected"
    CANCELLED = "CANCELLED", "Cancelled"


ACTIVE_JOB_STATUSES = (
    JobStatus.OPEN,
    JobStatus.INSPECTED,
)


class JobPriority(models.TextChoices):
    """Identify job-card operating priority."""

    NORMAL = "NORMAL", "Normal"
    URGENT = "URGENT", "Urgent"


class FuelLevel(models.TextChoices):
    """Describe the observed vehicle fuel level."""

    UNKNOWN = "UNKNOWN", "Unknown"
    EMPTY = "EMPTY", "Empty"
    QUARTER = "QUARTER", "Quarter"
    HALF = "HALF", "Half"
    THREE_QUARTERS = "THREE_QUARTERS", "Three quarters"
    FULL = "FULL", "Full"


class InspectionType(models.TextChoices):
    """Identify the purpose of an inspection record."""

    INITIAL = "INITIAL", "Initial inspection"
    DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic inspection"
    SAFETY = "SAFETY", "Safety inspection"
    QUALITY_CONTROL = (
        "QUALITY_CONTROL",
        "Quality-control inspection",
    )


class JobNoteType(models.TextChoices):
    """Identify the purpose of an append-only job note."""

    GENERAL = "GENERAL", "General"
    CUSTOMER_COMMUNICATION = (
        "CUSTOMER_COMMUNICATION",
        "Customer communication",
    )
    INTERNAL = "INTERNAL", "Internal"
    CANCELLATION = "CANCELLATION", "Cancellation"


class JobPermissionName(StrEnum):
    """Identify job-card permissions used by the application."""

    VIEW_JOB_CARD = "jobs.view_jobcard"
    ADD_JOB_CARD = "jobs.add_jobcard"
    CHANGE_JOB_CARD = "jobs.change_jobcard"
    CANCEL_JOB_CARD = "jobs.cancel_jobcard"

    VIEW_INSPECTION = "jobs.view_inspection"
    ADD_INSPECTION = "jobs.add_inspection"

    VIEW_JOB_NOTE = "jobs.view_jobnote"
    ADD_JOB_NOTE = "jobs.add_jobnote"
