"""URL routes for product-catalogue workflows."""

from django.urls import path

from apps.product_catalogue import views

app_name = "product_catalogue"

urlpatterns = [
    path(
        "",
        views.product_list,
        name="list",
    ),
    path(
        "new/",
        views.product_create,
        name="create",
    ),
    path(
        "categories/",
        views.product_category_list,
        name="category_list",
    ),
    path(
        "categories/new/",
        views.product_category_create,
        name="category_create",
    ),
    path(
        "<int:product_id>/change-price/",
        views.product_change_price,
        name="change_price",
    ),
    path(
        "<int:product_id>/",
        views.product_detail,
        name="detail",
    ),
]
