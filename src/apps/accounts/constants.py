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
