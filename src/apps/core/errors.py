"""Custom HTTP error handlers for the application."""

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def permission_denied(
    request: HttpRequest,
    exception: PermissionDenied,
) -> HttpResponse:
    """Render the application access-denied page.

    Args:
        request: Current HTTP request.
        exception: Permission exception raised by the protected view.

    Returns:
        A rendered HTTP 403 response.
    """

    return render(
        request,
        "accounts/access_denied.html",
        status=403,
    )
