"""Constants and enumerations for vehicle management."""

from enum import StrEnum

from django.db import models


class VehicleCategory(models.TextChoices):
    """Identify the business vehicle categories."""

    SMALL = "SMALL", "Small vehicle"
    COMMERCIAL = "COMMERCIAL", "Commercial vehicle"
    HEAVY = "HEAVY", "Heavy vehicle"


class FuelType(models.TextChoices):
    """Identify common vehicle fuel and power types."""

    PETROL = "PETROL", "Petrol"
    DIESEL = "DIESEL", "Diesel"
    HYBRID = "HYBRID", "Hybrid"
    ELECTRIC = "ELECTRIC", "Electric"
    OTHER = "OTHER", "Other"


class VehiclePermissionName(StrEnum):
    """Identify vehicle-management permissions."""

    VIEW_VEHICLE = "vehicles.view_vehicle"
    ADD_VEHICLE = "vehicles.add_vehicle"
    CHANGE_VEHICLE = "vehicles.change_vehicle"
    TRANSFER_VEHICLE_OWNER = "vehicles.transfer_vehicle_owner"
    DEACTIVATE_VEHICLE = "vehicles.deactivate_vehicle"
    REACTIVATE_VEHICLE = "vehicles.reactivate_vehicle"
