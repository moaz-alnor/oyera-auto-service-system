"""Read-only Django administration for release records."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.jobs.models import VehicleRelease


@admin.register(VehicleRelease)
class VehicleReleaseAdmin(admin.ModelAdmin):
    """Display vehicle handovers without direct editing."""

    actions = None

    list_display = (
        "release_number",
        "job_card",
        "received_by_name",
        "final_mileage",
        "invoice_number_snapshot",
        "invoice_status_snapshot",
        "outstanding_amount_snapshot",
        "payment_override",
        "released_at",
        "released_by",
    )
    list_filter = (
        "invoice_status_snapshot",
        "payment_override",
        "released_at",
    )
    search_fields = (
        "release_number",
        "job_card__job_number",
        "job_card__customer_name_snapshot",
        "job_card__vehicle_registration_snapshot",
        "received_by_name",
        "received_by_contact",
        "invoice_number_snapshot",
    )
    ordering = (
        "-released_at",
        "-pk",
    )
    list_select_related = (
        "job_card",
        "released_by",
        "payment_override_by",
    )

    def has_add_permission(
        self,
        request: HttpRequest,
    ) -> bool:
        """Prevent direct release creation in Admin."""

        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        """Prevent changes outside the release service."""

        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        """Preserve vehicle-release audit history."""

        return False
