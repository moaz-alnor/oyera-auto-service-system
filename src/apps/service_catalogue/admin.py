"""Read-only Django admin configuration for the service catalogue."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
    ServicePrice,
)


@admin.register(Service)
class ServiceAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Allow administrators to inspect catalogue services."""

    list_display = (
        "code",
        "name",
        "estimated_duration_minutes",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "code",
        "normalized_code",
        "name",
        "description",
    )
    ordering = (
        "name",
        "code",
    )


@admin.register(ServiceApplicability)
class ServiceApplicabilityAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow inspection of vehicle-category applicability."""

    list_display = (
        "service",
        "vehicle_category",
        "created_at",
    )
    list_filter = ("vehicle_category",)
    search_fields = (
        "service__code",
        "service__name",
    )
    ordering = (
        "service",
        "vehicle_category",
    )


@admin.register(ServicePrice)
class ServicePriceAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow inspection of historical catalogue prices."""

    list_display = (
        "service",
        "currency",
        "amount",
        "effective_from",
        "effective_until",
        "changed_by",
    )
    list_filter = (
        "currency",
        "effective_from",
        "effective_until",
    )
    search_fields = (
        "service__code",
        "service__name",
        "notes",
    )
    ordering = (
        "-effective_from",
        "-created_at",
    )
