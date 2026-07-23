"""URL routes for service-catalogue workflows."""

from django.urls import path

from apps.service_catalogue import views

app_name = "service_catalogue"

urlpatterns = [
    path(
        "",
        views.service_list,
        name="list",
    ),
    path(
        "new/",
        views.service_create,
        name="create",
    ),
    path(
        "<int:service_id>/change-price/",
        views.service_change_price,
        name="change_price",
    ),
    path(
        "<int:service_id>/",
        views.service_detail,
        name="detail",
    ),
]
