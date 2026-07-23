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
]
