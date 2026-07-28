"""Django configuration for purchasing workflows."""

from django.apps import AppConfig


class PurchasingConfig(AppConfig):
    """Configure the purchasing application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.purchasing"
    verbose_name = "Purchasing"
