"""URL routes for vehicle-management workflows."""

from django.urls import path

from apps.vehicles import views

app_name = "vehicles"

urlpatterns = [
    path(
        "",
        views.vehicle_list,
        name="list",
    ),
    path(
        "new/",
        views.vehicle_create,
        name="create",
    ),
    path(
        "<int:vehicle_id>/transfer-owner/",
        views.vehicle_transfer_owner,
        name="transfer_owner",
    ),
    path(
        "<int:vehicle_id>/",
        views.vehicle_detail,
        name="detail",
    ),
]
