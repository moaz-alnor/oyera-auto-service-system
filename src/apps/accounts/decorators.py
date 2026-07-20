"""Reusable authorization decorators for employee-facing views."""

from collections.abc import Callable

from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.http.response import HttpResponseBase

ViewFunction = Callable[..., HttpResponseBase]


def employee_permission_required(
    permission: str,
) -> Callable[[ViewFunction], ViewFunction]:
    """Require authentication and a named Django permission.

    Anonymous users are redirected to the login page. Authenticated users
    without the required permission receive an HTTP 403 response.

    Args:
        permission: Fully qualified Django permission identifier.

    Returns:
        A decorator that protects an employee-facing view.
    """

    def decorator(view_function: ViewFunction) -> ViewFunction:
        permission_checked_view = permission_required(
            permission,
            raise_exception=True,
        )(view_function)

        return login_required(permission_checked_view)

    return decorator
