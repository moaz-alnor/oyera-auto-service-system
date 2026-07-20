"""Constants and enumerations for customer management."""

from enum import StrEnum

from django.db import models


class CustomerType(models.TextChoices):
    """Identify the supported customer categories."""

    INDIVIDUAL = "INDIVIDUAL", "Individual"
    COMPANY = "COMPANY", "Company"


class CustomerPermissionName(StrEnum):
    """Identify customer-management permissions."""

    VIEW_CUSTOMER = "customers.view_customer"
    ADD_CUSTOMER = "customers.add_customer"
    CHANGE_CUSTOMER = "customers.change_customer"
    DEACTIVATE_CUSTOMER = "customers.deactivate_customer"
    REACTIVATE_CUSTOMER = "customers.reactivate_customer"
