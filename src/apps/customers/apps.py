"""Application configuration for the customer module."""

from django.apps import AppConfig


class CustomersConfig(AppConfig):
    """Configure customer-management functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.customers"
    verbose_name = "Customers"
