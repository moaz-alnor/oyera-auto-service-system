"""Application configuration for quotation workflows."""

from django.apps import AppConfig


class QuotationsConfig(AppConfig):
    """Configure quotation and customer-approval functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quotations"
    verbose_name = "Quotations"
