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
        "<int:vehicle_id>/edit/",
        views.vehicle_update,
        name="update",
    ),
    path(
        "<int:vehicle_id>/transfer-owner/",
        views.vehicle_transfer_owner,
        name="transfer_owner",
    ),
    path(
        "<int:vehicle_id>/deactivate/",
        views.vehicle_deactivate,
        name="deactivate",
    ),
    path(
        "<int:vehicle_id>/reactivate/",
        views.vehicle_reactivate,
        name="reactivate",
    ),
    path(
        "<int:vehicle_id>/",
        views.vehicle_detail,
        name="detail",
    ),
]
