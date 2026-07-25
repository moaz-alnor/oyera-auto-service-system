"""Application configuration for billing and payments."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Configure invoices and customer payments."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
    verbose_name = "Billing and payments"
