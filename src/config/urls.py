"""Root URL configuration for the Oyera Auto Service system."""

from django.contrib import admin
from django.urls import include, path

handler403 = "apps.core.errors.permission_denied"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
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
        "workshop/",
        include("apps.workshop.urls"),
    ),
]
