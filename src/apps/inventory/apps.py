"""Application configuration for inventory control."""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Configure inventory and stock-ledger records."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    verbose_name = "Inventory"
