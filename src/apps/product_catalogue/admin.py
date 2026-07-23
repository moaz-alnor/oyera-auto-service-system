"""Read-only Django admin configuration for product records."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect product categories."""

    list_display = (
        "code",
        "name",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "code",
        "normalized_code",
        "name",
        "description",
    )
    ordering = (
        "name",
        "code",
    )


@admin.register(Product)
class ProductAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect products."""

    list_display = (
        "sku",
        "name",
        "category",
        "manufacturer",
        "unit",
        "is_active",
    )
    list_filter = (
        "category",
        "unit",
        "is_active",
    )
    search_fields = (
        "sku",
        "normalized_sku",
        "name",
        "manufacturer",
        "manufacturer_part_number",
    )
    ordering = (
        "name",
        "sku",
    )


@admin.register(ProductPrice)
class ProductPriceAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow inspection of historical product prices."""

    list_display = (
        "product",
        "currency",
        "amount",
        "effective_from",
        "effective_until",
        "changed_by",
    )
    list_filter = (
        "currency",
        "effective_from",
        "effective_until",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "notes",
    )
    ordering = (
        "-effective_from",
        "-created_at",
    )
