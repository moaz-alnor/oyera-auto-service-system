"""Constants used by the accounts and access-management module."""

from enum import StrEnum


class RoleName(StrEnum):
    """Identify the supported employee roles."""

    ADMINISTRATOR = "Administrator"
    RECEPTIONIST = "Receptionist"
    SENIOR_TECHNICIAN = "Senior Technician"
    TECHNICIAN = "Technician"
    CASHIER = "Cashier"
    MANAGER = "Manager"


class PermissionName(StrEnum):
    """Identify account-management permissions used by the application."""

    VIEW_USER = "accounts.view_user"
    ADD_USER = "accounts.add_user"
    CHANGE_USER = "accounts.change_user"
