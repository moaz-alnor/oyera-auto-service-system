"""Root URL configuration for the Oyera Auto Service system."""

from django.contrib import admin
from django.urls import include, path

handler400 = "apps.core.errors.bad_request"
handler403 = "apps.core.errors.permission_denied"
handler404 = "apps.core.errors.page_not_found"
handler500 = "apps.core.errors.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
    path(
        "reports/",
        include("apps.reports.urls"),
    ),
    path("customers/", include("apps.customers.urls")),
    path(
        "vehicles/",
        include("apps.vehicles.urls"),
    ),
    path(
        "services/",
        include("apps.service_catalogue.urls"),
    ),
    path(
        "products/",
        include("apps.product_catalogue.urls"),
    ),
    path(
        "quotations/",
        include("apps.quotations.urls"),
    ),
    path(
        "jobs/",
        include("apps.jobs.urls"),
    ),
    path(
        "inventory/",
        include("apps.inventory.urls"),
    ),
    path(
        "purchasing/",
        include("apps.purchasing.urls"),
    ),
    path(
        "billing/",
        include("apps.billing.urls"),
    ),
    path(
        "workshop/",
        include("apps.workshop.urls"),
    ),
]
