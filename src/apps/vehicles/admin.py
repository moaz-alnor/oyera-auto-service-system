"""Read-only Django admin configuration for vehicle records."""

from django.contrib import admin
from django.http import HttpRequest

from apps.vehicles.models import Vehicle, VehicleOwnership


class ReadOnlyAdminMixin:
    """Prevent admin changes that bypass application services."""

    def has_add_permission(
        self,
        request: HttpRequest,
    ) -> bool:
        """Prevent creation through Django admin."""

        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Prevent changes through Django admin."""

        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Prevent deletion through Django admin."""

        return False


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
