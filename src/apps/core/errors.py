"""Custom HTTP error handlers for the application."""

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def bad_request(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    """Render a safe application HTTP 400 page."""
    return render(
        request,
        "errors/400.html",
        status=400,
    )


def permission_denied(
    request: HttpRequest,
    exception: PermissionDenied,
) -> HttpResponse:
    """Render the application access-denied page."""
    return render(
        request,
        "accounts/access_denied.html",
        status=403,
    )


def page_not_found(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    """Render the application HTTP 404 page."""
    return render(
        request,
        "errors/404.html",
        status=404,
    )


def server_error(request: HttpRequest) -> HttpResponse:
    """Render a safe application HTTP 500 page."""
    return render(
        request,
        "errors/500.html",
        status=500,
    )
