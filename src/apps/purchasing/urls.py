"""URL routes for supplier-finance workflows."""

from django.urls import path

from apps.purchasing import views

app_name = "purchasing"

urlpatterns = [
    path(
        "suppliers/",
        views.supplier_list,
        name="supplier_list",
    ),
    path(
        "suppliers/new/",
        views.supplier_create,
        name="supplier_create",
    ),
    path(
        "suppliers/<int:supplier_id>/",
        views.supplier_detail,
        name="supplier_detail",
    ),
    path(
        "suppliers/<int:supplier_id>/edit/",
        views.supplier_update,
        name="supplier_update",
    ),
    path(
        "suppliers/<int:supplier_id>/deactivate/",
        views.supplier_deactivate,
        name="supplier_deactivate",
    ),
    path(
        "suppliers/<int:supplier_id>/reactivate/",
        views.supplier_reactivate,
        name="supplier_reactivate",
    ),
    path(
        "purchase-orders/",
        views.purchase_order_list,
        name="purchase_order_list",
    ),
    path(
        "purchase-orders/new/",
        views.purchase_order_create,
        name="purchase_order_create",
    ),
    path(
        "purchase-orders/<int:purchase_order_id>/",
        views.purchase_order_detail,
        name="purchase_order_detail",
    ),
    path(
        "purchase-orders/<int:purchase_order_id>/edit/",
        views.purchase_order_update,
        name="purchase_order_update",
    ),
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
