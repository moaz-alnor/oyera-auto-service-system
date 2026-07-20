"""Read-only Django admin configuration for customer records."""

from django.contrib import admin
from django.http import HttpRequest

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Allow administrators to inspect customer records."""

    list_display = (
        "customer_number",
        "name",
        "customer_type",
        "phone_number",
        "is_active",
        "created_at",
    )
    list_filter = (
        "customer_type",
        "is_active",
    )
    search_fields = (
        "customer_number",
        "name",
        "phone_number",
        "normalized_phone_number",
        "email",
    )
    ordering = (
        "name",
        "customer_number",
    )

    def has_add_permission(
        self,
        request: HttpRequest,
    ) -> bool:
        """Require customer creation through the application service."""

        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Customer | None = None,
    ) -> bool:
        """Prevent bypassing customer workflow services."""

        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Customer | None = None,
    ) -> bool:
        """Prevent permanent deletion of customer history."""

        return False
