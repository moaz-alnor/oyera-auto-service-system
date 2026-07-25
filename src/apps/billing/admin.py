"""Read-only Django administration for billing records."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.billing.models import (
    Invoice,
    InvoiceProductLine,
    InvoiceServiceLine,
    Payment,
)


class ReadOnlyBillingAdmin(admin.ModelAdmin):
    """Prevent billing records from being edited in admin."""

    actions = None

    def has_add_permission(
        self,
        request: HttpRequest,
    ) -> bool:
        """Disable direct billing-record creation."""

        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        """Disable direct billing-record changes."""

        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Any | None = None,
    ) -> bool:
        """Disable direct billing-record deletion."""

        return False


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyBillingAdmin):
    """Display frozen invoices and lifecycle information."""

    list_display = (
        "invoice_number",
        "work_order_number_snapshot",
        "customer_name_snapshot",
        "vehicle_registration_snapshot",
        "status",
        "currency",
        "total",
        "issued_at",
        "due_date",
    )
    list_filter = (
        "status",
        "currency",
        "issued_at",
        "due_date",
    )
    search_fields = (
        "invoice_number",
        "work_order_number_snapshot",
        "job_number_snapshot",
        "quotation_number_snapshot",
        "customer_name_snapshot",
        "customer_phone_snapshot",
        "vehicle_registration_snapshot",
    )
    ordering = (
        "-created_at",
        "-pk",
    )


@admin.register(InvoiceServiceLine)
class InvoiceServiceLineAdmin(ReadOnlyBillingAdmin):
    """Display frozen invoice service lines."""

    list_display = (
        "invoice",
        "position",
        "service_code_snapshot",
        "service_name_snapshot",
        "quantity",
        "unit_price",
    )
    search_fields = (
        "invoice__invoice_number",
        "service_code_snapshot",
        "service_name_snapshot",
    )
    ordering = (
        "invoice",
        "position",
        "pk",
    )


@admin.register(InvoiceProductLine)
class InvoiceProductLineAdmin(ReadOnlyBillingAdmin):
    """Display frozen invoice product lines."""

    list_display = (
        "invoice",
        "position",
        "product_sku_snapshot",
        "product_name_snapshot",
        "quantity",
        "unit_price",
    )
    search_fields = (
        "invoice__invoice_number",
        "product_sku_snapshot",
        "product_name_snapshot",
    )
    ordering = (
        "invoice",
        "position",
        "pk",
    )


@admin.register(Payment)
class PaymentAdmin(ReadOnlyBillingAdmin):
    """Display append-only invoice payment records."""

    list_display = (
        "payment_number",
        "invoice",
        "status",
        "amount",
        "currency",
        "payment_method",
        "paid_at",
        "received_by",
    )
    list_filter = (
        "status",
        "currency",
        "payment_method",
        "paid_at",
    )
    search_fields = (
        "payment_number",
        "invoice__invoice_number",
        "external_reference",
        "invoice__customer_name_snapshot",
    )
    ordering = (
        "-paid_at",
        "-pk",
    )
