"""Constants and permission identifiers for inventory control."""

from enum import StrEnum

from django.db import models


class ReservationStatus(models.TextChoices):
    """Identify the lifecycle of a stock reservation."""

    ACTIVE = "ACTIVE", "Active"
    PARTIALLY_ISSUED = (
        "PARTIALLY_ISSUED",
        "Partially issued",
    )
    FULFILLED = "FULFILLED", "Fulfilled"
    RELEASED = "RELEASED", "Released"
    CANCELLED = "CANCELLED", "Cancelled"


class StockMovementType(models.TextChoices):
    """Identify why physical inventory changed."""

    RECEIPT = "RECEIPT", "Stock receipt"
    ISSUE = "ISSUE", "Workshop issue"
    RETURN = "RETURN", "Workshop return"
    ADJUSTMENT_IN = (
        "ADJUSTMENT_IN",
        "Positive adjustment",
    )
    ADJUSTMENT_OUT = (
        "ADJUSTMENT_OUT",
        "Negative adjustment",
    )


class InventoryPermissionName(StrEnum):
    """Identify inventory permissions used by the application."""

    VIEW_STOCK_LOCATION = "inventory.view_stocklocation"
    ADD_STOCK_LOCATION = "inventory.add_stocklocation"
    CHANGE_STOCK_LOCATION = "inventory.change_stocklocation"

    VIEW_INVENTORY_ITEM = "inventory.view_inventoryitem"
    ADD_INVENTORY_ITEM = "inventory.add_inventoryitem"
    CHANGE_INVENTORY_ITEM = "inventory.change_inventoryitem"

    VIEW_RESERVATION = "inventory.view_stockreservation"
    VIEW_MOVEMENT = "inventory.view_stockmovement"

    RECEIVE_STOCK = "inventory.receive_stock"
    RESERVE_STOCK = "inventory.reserve_stock"
    RELEASE_RESERVATION = "inventory.release_stock_reservation"
    ISSUE_STOCK = "inventory.issue_stock"
    RETURN_STOCK = "inventory.return_stock"
    ADJUST_STOCK = "inventory.adjust_stock"
