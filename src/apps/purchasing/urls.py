"""URL routes for supplier-finance workflows."""

from django.urls import path

from apps.purchasing import views

app_name = "purchasing"

urlpatterns = [
    path(
        "supplier-invoices/",
        views.supplier_invoice_list,
        name="supplier_invoice_list",
    ),
    path(
        "supplier-invoices/new/",
        views.supplier_invoice_create,
        name="supplier_invoice_create",
    ),
    path(
        "supplier-invoices/<int:supplier_invoice_id>/",
        views.supplier_invoice_detail,
        name="supplier_invoice_detail",
    ),
    path(
        "supplier-invoices/<int:supplier_invoice_id>/post/",
        views.supplier_invoice_post,
        name="supplier_invoice_post",
    ),
    path(
        "supplier-invoices/<int:supplier_invoice_id>/void/",
        views.supplier_invoice_void,
        name="supplier_invoice_void",
    ),
    path(
        "supplier-invoices/<int:supplier_invoice_id>/payments/new/",
        views.supplier_payment_record,
        name="supplier_payment_record",
    ),
    path(
        "supplier-payments/<int:payment_id>/void/",
        views.supplier_payment_void,
        name="supplier_payment_void",
    ),
]
