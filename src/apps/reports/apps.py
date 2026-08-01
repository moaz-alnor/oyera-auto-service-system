"""Django application configuration for reporting."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configure the operational reporting application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Operational Reports"
