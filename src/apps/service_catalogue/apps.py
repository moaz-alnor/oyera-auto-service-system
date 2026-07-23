"""Application configuration for the service catalogue."""

from django.apps import AppConfig


class ServiceCatalogueConfig(AppConfig):
    """Configure service-catalogue functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service_catalogue"
    verbose_name = "Service catalogue"
