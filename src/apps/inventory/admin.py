"""Read-only Django admin configuration for inventory records."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
    StockReservation,
)


@admin.register(StockLocation)
class StockLocationAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect stock locations."""

    list_display = (
        "code",
        "name",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "created_at",
    )
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
    list_select_related = (
        "created_by",
        "updated_by",
    )


@admin.register(InventoryItem)
class InventoryItemAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect inventory items."""

    list_display = (
        "product",
        "location",
        "reorder_level",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "location",
        "created_at",
    )
    search_fields = (
        "product__sku",
        "product__normalized_sku",
        "product__name",
        "location__code",
        "location__name",
    )
    ordering = (
        "product__name",
        "location__name",
    )
    list_select_related = (
        "product",
        "location",
        "created_by",
        "updated_by",
    )


@admin.register(StockReservation)
class StockReservationAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect reservation history."""

    list_display = (
        "inventory_item",
        "work_product_requirement",
        "status",
        "quantity_reserved",
        "quantity_issued",
        "quantity_released",
        "remaining_quantity",
        "created_at",
    )
    list_filter = (
        "status",
        "created_at",
        "released_at",
    )
    search_fields = (
        "inventory_item__product__sku",
        "inventory_item__product__name",
        ("work_product_requirement__work_order__work_order_number"),
        ("work_product_requirement__product_sku_snapshot"),
        ("work_product_requirement__product_name_snapshot"),
    )
    ordering = (
        "-created_at",
        "-pk",
    )
    list_select_related = (
        "inventory_item",
        "inventory_item__product",
        "inventory_item__location",
        "work_product_requirement",
        "work_product_requirement__work_order",
        "reserved_by",
        "released_by",
    )


@admin.register(StockMovement)
class StockMovementAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect the stock ledger."""

    list_display = (
        "movement_number",
        "movement_type",
        "inventory_item",
        "quantity",
        "reservation",
        "external_reference",
        "occurred_at",
        "created_by",
    )
    list_filter = (
        "movement_type",
        "occurred_at",
        "currency",
    )
    search_fields = (
        "movement_number",
        "inventory_item__product__sku",
        "inventory_item__product__name",
        "inventory_item__location__code",
        "external_reference",
        "notes",
    )
    ordering = (
        "-occurred_at",
        "-pk",
    )
    list_select_related = (
        "inventory_item",
        "inventory_item__product",
        "inventory_item__location",
        "reservation",
        "source_movement",
        "created_by",
    )
