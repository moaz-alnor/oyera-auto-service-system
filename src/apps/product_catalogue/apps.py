"""Application configuration for the product catalogue."""

from django.apps import AppConfig


class ProductCatalogueConfig(AppConfig):
    """Configure product-catalogue functionality."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.product_catalogue"
    verbose_name = "Product catalogue"
