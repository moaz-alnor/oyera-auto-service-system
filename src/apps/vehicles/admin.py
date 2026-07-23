"""Read-only Django admin configuration for vehicle records."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.vehicles.models import Vehicle, VehicleOwnership


@admin.register(Vehicle)
class VehicleAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Allow administrators to inspect registered vehicles."""

    list_display = (
        "vehicle_number",
        "registration_number",
        "make",
        "model",
        "current_owner",
        "category",
        "is_active",
    )
    list_filter = (
        "category",
        "fuel_type",
        "is_active",
    )
    search_fields = (
        "vehicle_number",
        "registration_number",
        "normalized_registration_number",
        "make",
        "model",
        "current_owner__name",
    )
    ordering = ("registration_number",)


@admin.register(VehicleOwnership)
class VehicleOwnershipAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect ownership history."""

    list_display = (
        "vehicle",
        "owner",
        "started_at",
        "ended_at",
        "changed_by",
    )
    list_filter = ("started_at", "ended_at")
    search_fields = (
        "vehicle__registration_number",
        "owner__name",
        "owner__customer_number",
    )
    ordering = ("-started_at",)
