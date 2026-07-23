"""Application configuration for job-card workflows."""

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Configure vehicle-service job-card functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    verbose_name = "Job cards"
