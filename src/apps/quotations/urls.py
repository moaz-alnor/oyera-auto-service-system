"""URL routes for quotation workflows."""

from django.urls import path

from apps.quotations import views

app_name = "quotations"

urlpatterns = [
    path(
        "",
        views.quotation_list,
        name="list",
    ),
    path(
        "new/",
        views.quotation_create,
        name="create",
    ),
    path(
        "<int:quotation_id>/services/new/",
        views.service_line_create,
        name="service_line_create",
    ),
    path(
        "<int:quotation_id>/products/new/",
        views.product_line_create,
        name="product_line_create",
    ),
    path(
        "<int:quotation_id>/submit/",
        views.quotation_submit,
        name="submit",
    ),
    path(
        "<int:quotation_id>/approve/",
        views.quotation_approve,
        name="approve",
    ),
    path(
        "<int:quotation_id>/reject/",
        views.quotation_reject,
        name="reject",
    ),
    path(
        "<int:quotation_id>/revise/",
        views.quotation_revise,
        name="revise",
    ),
    path(
        "<int:quotation_id>/",
        views.quotation_detail,
        name="detail",
    ),
]
