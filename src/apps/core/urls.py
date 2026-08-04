"""URL routes for shared application pages."""

from django.urls import path

from apps.core import health, views

app_name = "core"

urlpatterns = [
    path(
        "health/live/",
        health.liveness,
        name="health_live",
    ),
    path(
        "health/ready/",
        health.readiness,
        name="health_ready",
    ),
    path("", views.dashboard, name="dashboard"),
]
