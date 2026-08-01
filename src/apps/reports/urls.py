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
]
