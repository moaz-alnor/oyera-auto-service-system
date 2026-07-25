"""URL routes for invoice and payment workflows."""

from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path(
        "",
        views.invoice_list,
        name="list",
    ),
    path(
        "new/",
        views.invoice_create,
        name="create",
    ),
    path(
        "<int:invoice_id>/issue/",
        views.invoice_issue,
        name="issue",
    ),
    path(
        "<int:invoice_id>/void/",
        views.invoice_void,
        name="void",
    ),
    path(
        "<int:invoice_id>/payments/new/",
        views.payment_record,
        name="payment_create",
    ),
    path(
        "payments/<int:payment_id>/void/",
        views.payment_void,
        name="payment_void",
    ),
    path(
        "<int:invoice_id>/",
        views.invoice_detail,
        name="detail",
    ),
]
