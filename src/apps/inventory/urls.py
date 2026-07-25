"""URL routes for inventory-management workflows."""

from django.urls import path

from apps.inventory import views

app_name = "inventory"

urlpatterns = [
    path(
        "",
        views.inventory_list,
        name="list",
    ),
    path(
        "locations/new/",
        views.stock_location_create,
        name="location_create",
    ),
    path(
        "items/new/",
        views.inventory_item_create,
        name="item_create",
    ),
    path(
        "movements/",
        views.movement_list,
        name="movement_list",
    ),
    path(
        "movements/<int:movement_id>/return/",
        views.stock_return,
        name="return",
    ),
    path(
        "requirements/<int:requirement_id>/reserve/",
        views.stock_reserve,
        name="reserve",
    ),
    path(
        "reservations/<int:reservation_id>/release/",
        views.reservation_release,
        name="release",
    ),
    path(
        "reservations/<int:reservation_id>/issue/",
        views.stock_issue,
        name="issue",
    ),
    path(
        "<int:inventory_item_id>/receive/",
        views.stock_receive,
        name="receive",
    ),
    path(
        "<int:inventory_item_id>/adjust/",
        views.stock_adjust,
        name="adjust",
    ),
    path(
        "<int:inventory_item_id>/",
        views.inventory_detail,
        name="detail",
    ),
]
