"""Application configuration for workshop execution."""

from django.apps import AppConfig


class WorkshopConfig(AppConfig):
    """Configure technician assignments and work execution."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workshop"
    verbose_name = "Workshop Execution"
