"""Application services for vehicle-management operations."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.constants import (
    FuelType,
    VehicleCategory,
    VehiclePermissionName,
)
from apps.vehicles.models import Vehicle, VehicleOwnership


@dataclass(frozen=True, slots=True)
class RegisterVehicleCommand:
    """Contain validated input for vehicle registration."""

    owner_id: int
    registration_number: str
    category: VehicleCategory
    make: str
    model: str
    year: int | None = None
    color: str = ""
    current_mileage: int | None = None
    fuel_type: FuelType | str = ""
    engine_number: str = ""
    chassis_number: str = ""
    vin: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class TransferVehicleOwnershipCommand:
    """Contain information for a vehicle ownership transfer."""

    new_owner_id: int
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: VehiclePermissionName,
) -> None:
    """Require an employee to hold a vehicle permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this vehicle action."
        )


def _get_active_customer(
    *,
    customer_id: int,
) -> Customer:
    """Return an active customer or raise a validation error."""

    customer = Customer.objects.select_for_update().get(pk=customer_id)

    if not customer.is_active:
        raise ValidationError(
            {
                "owner": (
                    "An inactive customer cannot become the current owner of a vehicle."
                )
            }
        )

    return customer


@transaction.atomic
def register_vehicle(
    *,
    actor: User,
    command: RegisterVehicleCommand,
) -> Vehicle:
    """Register a vehicle and create its initial ownership record.

    Args:
        actor: Authenticated employee registering the vehicle.
        command: Vehicle information supplied by the employee.

    Returns:
        The registered vehicle.

    Raises:
        PermissionDenied: If the employee cannot register vehicles.
        ValidationError: If vehicle or owner information is invalid.
    """

    _require_permission(
        actor=actor,
        permission=VehiclePermissionName.ADD_VEHICLE,
    )

    owner = _get_active_customer(customer_id=command.owner_id)

    vehicle = Vehicle(
        current_owner=owner,
        registration_number=command.registration_number,
        category=command.category,
        make=command.make,
        model=command.model,
        year=command.year,
        color=command.color,
        current_mileage=command.current_mileage,
        fuel_type=command.fuel_type,
        engine_number=command.engine_number,
        chassis_number=command.chassis_number,
        vin=command.vin,
        notes=command.notes.strip(),
        created_by=actor,
        updated_by=actor,
    )

    vehicle.full_clean()
    vehicle.save()

    if vehicle.pk is None:
        raise RuntimeError("Vehicle registration completed without a primary key.")

    vehicle.vehicle_number = f"VEH-{vehicle.pk:06d}"
    vehicle.save(
        update_fields=(
            "vehicle_number",
            "updated_at",
        )
    )

    ownership = VehicleOwnership(
        vehicle=vehicle,
        owner=owner,
        changed_by=actor,
        notes="Initial vehicle registration.",
    )
    ownership.full_clean()
    ownership.save()

    return vehicle


@transaction.atomic
def transfer_vehicle_ownership(
    *,
    actor: User,
    vehicle_id: int,
    command: TransferVehicleOwnershipCommand,
) -> Vehicle:
    """Transfer a vehicle to another active customer.

    Args:
        actor: Authenticated employee performing the transfer.
        vehicle_id: Primary key of the vehicle being transferred.
        command: New-owner and transfer-note information.

    Returns:
        The updated vehicle.

    Raises:
        PermissionDenied: If the employee cannot transfer vehicles.
        Vehicle.DoesNotExist: If the vehicle does not exist.
        Customer.DoesNotExist: If the new owner does not exist.
        ValidationError: If the new owner is inactive.
    """

    _require_permission(
        actor=actor,
        permission=VehiclePermissionName.TRANSFER_VEHICLE_OWNER,
    )

    vehicle = Vehicle.objects.select_for_update().get(pk=vehicle_id)
    new_owner = _get_active_customer(customer_id=command.new_owner_id)

    if vehicle.current_owner_id == new_owner.pk:
        return vehicle

    try:
        current_ownership = VehicleOwnership.objects.select_for_update().get(
            vehicle=vehicle,
            ended_at__isnull=True,
        )
    except VehicleOwnership.DoesNotExist as exc:
        raise RuntimeError("The vehicle has no active ownership record.") from exc

    transfer_time = timezone.now()

    current_ownership.ended_at = transfer_time
    current_ownership.save(
        update_fields=(
            "ended_at",
            "updated_at",
        )
    )

    vehicle.current_owner = new_owner
    vehicle.updated_by = actor
    vehicle.save(
        update_fields=(
            "current_owner",
            "updated_by",
            "updated_at",
        )
    )

    new_ownership = VehicleOwnership(
        vehicle=vehicle,
        owner=new_owner,
        started_at=transfer_time,
        changed_by=actor,
        notes=command.notes.strip(),
    )
    new_ownership.full_clean()
    new_ownership.save()

    return vehicle
