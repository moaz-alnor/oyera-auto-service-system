"""Read-only Django admin configuration for workshop records."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.workshop.models import (
    TechnicianAssignment,
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
    WorkTaskNote,
)


@admin.register(WorkOrder)
class WorkOrderAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect work orders."""

    list_display = (
        "work_order_number",
        "job_card",
        "approved_quotation",
        "status",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = (
        "status",
        "created_at",
        "started_at",
        "completed_at",
    )
    search_fields = (
        "work_order_number",
        "job_card__job_number",
        "job_card__customer_name_snapshot",
        "job_card__customer_phone_snapshot",
        "job_card__vehicle_registration_snapshot",
        "approved_quotation__quotation_number",
    )
    ordering = (
        "-created_at",
        "-pk",
    )
    list_select_related = (
        "job_card",
        "approved_quotation",
        "created_by",
        "updated_by",
    )


@admin.register(WorkTask)
class WorkTaskAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect service execution."""

    list_display = (
        "work_order",
        "position",
        "service_code_snapshot",
        "service_name_snapshot",
        "status",
        "actual_started_at",
        "actual_completed_at",
    )
    list_filter = (
        "status",
        "created_at",
        "actual_started_at",
        "actual_completed_at",
    )
    search_fields = (
        "work_order__work_order_number",
        "service_code_snapshot",
        "service_name_snapshot",
    )
    ordering = (
        "-work_order__created_at",
        "position",
    )
    list_select_related = (
        "work_order",
        "source_service_line",
        "created_by",
        "updated_by",
    )


@admin.register(TechnicianAssignment)
class TechnicianAssignmentAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect assignment history."""

    list_display = (
        "work_task",
        "technician",
        "status",
        "is_active",
        "assigned_by",
        "assigned_at",
        "started_at",
        "completed_at",
        "removed_at",
    )
    list_filter = (
        "status",
        "is_active",
        "assigned_at",
    )
    search_fields = (
        "work_task__work_order__work_order_number",
        "work_task__service_name_snapshot",
        "technician__username",
        "technician__first_name",
        "technician__last_name",
    )
    ordering = (
        "-assigned_at",
        "-pk",
    )
    list_select_related = (
        "work_task",
        "work_task__work_order",
        "technician",
        "assigned_by",
    )


@admin.register(WorkProductRequirement)
class WorkProductRequirementAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect product demand."""

    list_display = (
        "work_order",
        "position",
        "product_sku_snapshot",
        "product_name_snapshot",
        "approved_quantity",
        "unit_snapshot",
        "inventory_status",
    )
    list_filter = (
        "inventory_status",
        "unit_snapshot",
        "created_at",
    )
    search_fields = (
        "work_order__work_order_number",
        "product_sku_snapshot",
        "product_name_snapshot",
    )
    ordering = (
        "-work_order__created_at",
        "position",
    )
    list_select_related = (
        "work_order",
        "source_product_line",
        "created_by",
    )


@admin.register(WorkTaskNote)
class WorkTaskNoteAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect workshop notes."""

    list_display = (
        "work_task",
        "note_type",
        "created_by",
        "created_at",
    )
    list_filter = (
        "note_type",
        "created_at",
    )
    search_fields = (
        "work_task__work_order__work_order_number",
        "work_task__service_name_snapshot",
        "content",
        "created_by__username",
    )
    ordering = (
        "-created_at",
        "-pk",
    )
    list_select_related = (
        "work_task",
        "work_task__work_order",
        "created_by",
    )
