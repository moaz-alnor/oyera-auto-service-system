"""URL routes for operational reports."""

from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path(
        "",
        views.report_index,
        name="index",
    ),
    path(
        "customer-finance/",
        views.customer_finance_report,
        name="customer_finance",
    ),
    path(
        "customer-finance/export.csv",
        views.customer_finance_export,
        name="customer_finance_export",
    ),
    path(
        "workshop-operations/",
        views.workshop_operations_report,
        name="workshop_operations",
    ),
    path(
        "workshop-operations/export.csv",
        views.workshop_operations_export,
        name="workshop_operations_export",
    ),
    path(
        "inventory-activity/",
        views.inventory_activity_report,
        name="inventory_activity",
    ),
    path(
        "inventory-activity/export.csv",
        views.inventory_activity_export,
        name="inventory_activity_export",
    ),
    path(
        "purchasing-activity/",
        views.purchasing_activity_report,
        name="purchasing_activity",
    ),
]
