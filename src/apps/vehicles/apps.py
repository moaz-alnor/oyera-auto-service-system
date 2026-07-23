"""Application configuration for the vehicle module."""

from django.apps import AppConfig


class VehiclesConfig(AppConfig):
    """Configure vehicle-management functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vehicles"
    verbose_name = "Vehicles"
