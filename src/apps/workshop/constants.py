"""Constants and permission identifiers for workshop execution."""

from enum import StrEnum

from django.db import models


class WorkOrderStatus(models.TextChoices):
    """Identify the operational state of a work order."""

    PLANNED = "PLANNED", "Planned"
    READY = "READY", "Ready for work"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    ON_HOLD = "ON_HOLD", "On hold"
    AWAITING_REVIEW = (
        "AWAITING_REVIEW",
        "Awaiting quality review",
    )
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class WorkTaskStatus(models.TextChoices):
    """Identify the execution state of one service task."""

    PENDING = "PENDING", "Pending"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    BLOCKED = "BLOCKED", "Blocked"
    AWAITING_REVIEW = (
        "AWAITING_REVIEW",
        "Awaiting review",
    )
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class TechnicianAssignmentStatus(models.TextChoices):
    """Identify one technician's assignment state."""

    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    REMOVED = "REMOVED", "Removed"


class ProductRequirementStatus(models.TextChoices):
    """Identify the inventory state of an approved product demand."""

    NOT_RESERVED = "NOT_RESERVED", "Not reserved"
    PARTIALLY_RESERVED = (
        "PARTIALLY_RESERVED",
        "Partially reserved",
    )
    RESERVED = "RESERVED", "Reserved"
    PARTIALLY_ISSUED = (
        "PARTIALLY_ISSUED",
        "Partially issued",
    )
    ISSUED = "ISSUED", "Issued"
    CANCELLED = "CANCELLED", "Cancelled"


class WorkTaskNoteType(models.TextChoices):
    """Identify the purpose of an append-only task note."""

    GENERAL = "GENERAL", "General"
    TECHNICAL = "TECHNICAL", "Technical"
    BLOCKER = "BLOCKER", "Blocker"
    COMPLETION = "COMPLETION", "Completion"


class WorkshopPermissionName(StrEnum):
    """Identify workshop permissions used by the application."""

    VIEW_WORK_ORDER = "workshop.view_workorder"
    ADD_WORK_ORDER = "workshop.add_workorder"
    CHANGE_WORK_ORDER = "workshop.change_workorder"

    VIEW_WORK_TASK = "workshop.view_worktask"
    CHANGE_WORK_TASK = "workshop.change_worktask"

    VIEW_ASSIGNMENT = "workshop.view_technicianassignment"
    ADD_ASSIGNMENT = "workshop.add_technicianassignment"
    CHANGE_ASSIGNMENT = "workshop.change_technicianassignment"

    VIEW_PRODUCT_REQUIREMENT = "workshop.view_workproductrequirement"

    VIEW_TASK_NOTE = "workshop.view_worktasknote"
    ADD_TASK_NOTE = "workshop.add_worktasknote"

    ASSIGN_TECHNICIAN = "workshop.assign_technician"
    START_WORK_ORDER = "workshop.start_work_order"
    HOLD_WORK_ORDER = "workshop.hold_work_order"
    RESUME_WORK_ORDER = "workshop.resume_work_order"
    COMPLETE_WORK_ORDER = "workshop.complete_work_order"

    START_WORK_TASK = "workshop.start_work_task"
    BLOCK_WORK_TASK = "workshop.block_work_task"
    COMPLETE_WORK_TASK = "workshop.complete_work_task"
