"""Application configuration for the core module."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configure shared project functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
