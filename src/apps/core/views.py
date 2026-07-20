"""HTTP views for shared application pages."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Display the authenticated employee dashboard."""

    return render(
        request,
        "core/dashboard.html",
    )
