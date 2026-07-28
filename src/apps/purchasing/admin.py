"""Read-only Django administration for purchasing records."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect suppliers."""

    list_display = (
        "supplier_number",
        "code",
        "name",
        "contact_name",
        "phone_number",
        "preferred_currency",
        "payment_terms_days",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "preferred_currency",
        "created_at",
    )
    search_fields = (
        "supplier_number",
        "code",
        "normalized_code",
        "name",
        "normalized_name",
        "contact_name",
        "phone_number",
        "email",
        "tax_identifier",
    )
    ordering = (
        "name",
        "supplier_number",
    )
    list_select_related = (
        "created_by",
        "updated_by",
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect purchase orders."""

    list_display = (
        "purchase_order_number",
        "supplier_name_snapshot",
        "status",
        "currency",
        "discount_percentage",
        "tax_percentage",
        "delivery_cost",
        "expected_delivery_date",
        "created_at",
    )
    list_filter = (
        "status",
        "currency",
        "expected_delivery_date",
        "created_at",
    )
    search_fields = (
        "purchase_order_number",
        "supplier_number_snapshot",
        "supplier_code_snapshot",
        "supplier_name_snapshot",
        "supplier_reference",
        "lines__product_sku_snapshot",
        "lines__product_name_snapshot",
    )
    ordering = (
        "-created_at",
        "-pk",
    )
    list_select_related = (
        "supplier",
        "created_by",
        "updated_by",
        "submitted_by",
        "approved_by",
        "cancelled_by",
    )


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect ordered products."""

    list_display = (
        "purchase_order",
        "position",
        "product_sku_snapshot",
        "product_name_snapshot",
        "quantity_ordered",
        "unit_cost",
        "line_total",
        "created_at",
    )
    list_filter = (
        "purchase_order__status",
        "unit_snapshot",
        "created_at",
    )
    search_fields = (
        "purchase_order__purchase_order_number",
        "purchase_order__supplier_name_snapshot",
        "product_sku_snapshot",
        "product_name_snapshot",
        "description_snapshot",
    )
    ordering = (
        "purchase_order",
        "position",
        "pk",
    )
    list_select_related = (
        "purchase_order",
        "product",
        "created_by",
        "updated_by",
    )


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect supplier deliveries."""

    list_display = (
        "goods_receipt_number",
        "purchase_order_number_snapshot",
        "supplier_name_snapshot",
        "supplier_delivery_reference",
        "received_at",
        "received_by",
    )
    list_filter = (
        "received_at",
        "purchase_order__status",
    )
    search_fields = (
        "goods_receipt_number",
        "purchase_order_number_snapshot",
        "supplier_number_snapshot",
        "supplier_name_snapshot",
        "supplier_delivery_reference",
        "lines__product_sku_snapshot",
        "lines__product_name_snapshot",
        "lines__stock_movement__movement_number",
    )
    ordering = (
        "-received_at",
        "-pk",
    )
    list_select_related = (
        "purchase_order",
        "purchase_order__supplier",
        "received_by",
    )


@admin.register(GoodsReceiptLine)
class GoodsReceiptLineAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect delivered products."""

    list_display = (
        "goods_receipt",
        "product_sku_snapshot",
        "product_name_snapshot",
        "quantity_received",
        "unit_cost_snapshot",
        "currency_snapshot",
        "inventory_item",
        "stock_movement",
        "created_at",
    )
    list_filter = (
        "currency_snapshot",
        "inventory_item__location",
        "created_at",
    )
    search_fields = (
        "goods_receipt__goods_receipt_number",
        "goods_receipt__purchase_order_number_snapshot",
        "product_sku_snapshot",
        "product_name_snapshot",
        "stock_movement__movement_number",
        "inventory_item__location__code",
    )
    ordering = (
        "goods_receipt",
        "purchase_order_line__position",
        "pk",
    )
    list_select_related = (
        "goods_receipt",
        "purchase_order_line",
        "inventory_item",
        "inventory_item__product",
        "inventory_item__location",
        "stock_movement",
        "created_by",
    )
