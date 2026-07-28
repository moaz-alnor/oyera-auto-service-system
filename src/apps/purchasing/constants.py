"""Constants and permission identifiers for purchasing."""

from enum import StrEnum

from django.db import models


class PurchaseOrderStatus(models.TextChoices):
    """Identify the lifecycle of a purchase order."""

    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted for approval"
    APPROVED = "APPROVED", "Approved"
    PARTIALLY_RECEIVED = (
        "PARTIALLY_RECEIVED",
        "Partially received",
    )
    RECEIVED = "RECEIVED", "Fully received"
    CANCELLED = "CANCELLED", "Cancelled"


class PurchasingPermissionName(StrEnum):
    """Identify purchasing permissions used by the application."""

    VIEW_SUPPLIER = "purchasing.view_supplier"
    ADD_SUPPLIER = "purchasing.add_supplier"
    CHANGE_SUPPLIER = "purchasing.change_supplier"
    DEACTIVATE_SUPPLIER = "purchasing.deactivate_supplier"
    REACTIVATE_SUPPLIER = "purchasing.reactivate_supplier"

    VIEW_PURCHASE_ORDER = "purchasing.view_purchaseorder"
    ADD_PURCHASE_ORDER = "purchasing.add_purchaseorder"
    CHANGE_PURCHASE_ORDER = "purchasing.change_purchaseorder"
    SUBMIT_PURCHASE_ORDER = "purchasing.submit_purchase_order"
    APPROVE_PURCHASE_ORDER = "purchasing.approve_purchase_order"
    CANCEL_PURCHASE_ORDER = "purchasing.cancel_purchase_order"

    VIEW_GOODS_RECEIPT = "purchasing.view_goodsreceipt"
    RECEIVE_PURCHASE_ORDER = "purchasing.receive_purchase_order"
