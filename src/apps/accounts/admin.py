"""Django admin configuration for employee accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Provide administrative management for employee accounts."""

    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
    )
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )
    ordering = ("username",)

    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        (
            "Additional information",
            {
                "fields": ("phone_number",),
            },
        ),
    )

    add_fieldsets = (
        *DjangoUserAdmin.add_fieldsets,
        (
            "Additional information",
            {
                "fields": ("phone_number",),
            },
        ),
    )
