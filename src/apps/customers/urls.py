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
        "<int:customer_id>/edit/",
        views.customer_update,
        name="update",
    ),
    path(
        "<int:customer_id>/deactivate/",
        views.customer_deactivate,
        name="deactivate",
    ),
    path(
        "<int:customer_id>/reactivate/",
        views.customer_reactivate,
        name="reactivate",
    ),
    path(
        "<int:customer_id>/",
        views.customer_detail,
        name="detail",
    ),
]
