"""URL routes for customer-management workflows."""

from django.urls import path

from apps.customers import views

app_name = "customers"

urlpatterns = [
    path(
        "",
        views.customer_list,
        name="list",
    ),
    path(
        "new/",
        views.customer_create,
        name="create",
    ),
    path(
        "<int:customer_id>/",
        views.customer_detail,
        name="detail",
    ),
]
