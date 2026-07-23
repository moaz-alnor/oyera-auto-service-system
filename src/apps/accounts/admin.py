"""Django admin configuration for employee accounts."""

from collections.abc import Callable

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpRequest

from apps.accounts.models import User

type AdminAction = tuple[Callable[..., str], str, str] | None


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
        *(DjangoUserAdmin.fieldsets or ()),
        (
            "Additional information",
            {
                "fields": ("phone_number",),
            },
        ),
    )

    add_fieldsets = (
        *(DjangoUserAdmin.add_fieldsets or ()),
        (
            "Additional information",
            {
                "fields": ("phone_number",),
            },
        ),
    )

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> bool:
        """Prevent deletion of employee accounts with historical activity."""

        return False

    def get_actions(
        self,
        request: HttpRequest,
    ) -> dict[str, AdminAction]:
        """Remove Django's bulk-delete action."""

        actions = super().get_actions(request)
        actions.pop("delete_selected", None)

        return actions
