"""Reusable Django admin protections."""

from django.http import HttpRequest


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
