"""Read-only Django admin configuration for quotations."""

from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)


@admin.register(Quotation)
class QuotationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    """Allow administrators to inspect quotation revisions."""

    list_display = (
        "quotation_number",
        "job_card",
        "revision_number",
        "status",
        "is_current",
        "currency",
        "created_at",
    )
    list_filter = (
        "status",
        "is_current",
        "currency",
        "created_at",
    )
    search_fields = (
        "quotation_number",
        "job_card__job_number",
        "job_card__customer_name_snapshot",
        "job_card__customer_phone_snapshot",
        "job_card__vehicle_registration_snapshot",
    )
    ordering = (
        "-created_at",
        "-revision_number",
    )
    list_select_related = (
        "job_card",
        "created_by",
        "updated_by",
    )


@admin.register(QuotationServiceLine)
class QuotationServiceLineAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect service snapshots."""

    list_display = (
        "quotation",
        "position",
        "service_code_snapshot",
        "service_name_snapshot",
        "quantity",
        "unit_price",
        "line_total_display",
    )
    list_filter = (
        "quotation__status",
        "quotation__currency",
        "created_at",
    )
    search_fields = (
        "quotation__quotation_number",
        "service_code_snapshot",
        "service_name_snapshot",
    )
    ordering = (
        "-quotation__created_at",
        "position",
    )
    list_select_related = (
        "quotation",
        "service",
        "created_by",
    )

    @admin.display(description="Line total")
    def line_total_display(
        self,
        obj: QuotationServiceLine,
    ) -> str:
        """Return the monetary line total for display."""

        return f"{obj.quotation.currency} {obj.line_total:,.2f}"


@admin.register(QuotationProductLine)
class QuotationProductLineAdmin(
    ReadOnlyAdminMixin,
    admin.ModelAdmin,
):
    """Allow administrators to inspect product snapshots."""

    list_display = (
        "quotation",
        "position",
        "product_sku_snapshot",
        "product_name_snapshot",
        "unit_snapshot",
        "quantity",
        "unit_price",
        "line_total_display",
    )
    list_filter = (
        "quotation__status",
        "quotation__currency",
        "unit_snapshot",
        "created_at",
    )
    search_fields = (
        "quotation__quotation_number",
        "product_sku_snapshot",
        "product_name_snapshot",
    )
    ordering = (
        "-quotation__created_at",
        "position",
    )
    list_select_related = (
        "quotation",
        "product",
        "created_by",
    )

    @admin.display(description="Line total")
    def line_total_display(
        self,
        obj: QuotationProductLine,
    ) -> str:
        """Return the monetary line total for display."""

        return f"{obj.quotation.currency} {obj.line_total:,.2f}"
