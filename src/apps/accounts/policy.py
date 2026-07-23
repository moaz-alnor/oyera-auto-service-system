"""Authorization policy for employee roles."""

from apps.accounts.constants import PermissionName, RoleName
from apps.customers.constants import CustomerPermissionName
from apps.vehicles.constants import VehiclePermissionName

ROLE_PERMISSION_POLICY: dict[
    RoleName,
    frozenset[str],
] = {
    RoleName.ADMINISTRATOR: frozenset(
        {
            PermissionName.VIEW_USER.value,
            PermissionName.ADD_USER.value,
            PermissionName.CHANGE_USER.value,
            CustomerPermissionName.VIEW_CUSTOMER.value,
            CustomerPermissionName.ADD_CUSTOMER.value,
            CustomerPermissionName.CHANGE_CUSTOMER.value,
            CustomerPermissionName.DEACTIVATE_CUSTOMER.value,
            CustomerPermissionName.REACTIVATE_CUSTOMER.value,
            VehiclePermissionName.VIEW_VEHICLE.value,
            VehiclePermissionName.ADD_VEHICLE.value,
            VehiclePermissionName.CHANGE_VEHICLE.value,
            VehiclePermissionName.TRANSFER_VEHICLE_OWNER.value,
            VehiclePermissionName.DEACTIVATE_VEHICLE.value,
            VehiclePermissionName.REACTIVATE_VEHICLE.value,
        }
    ),
    RoleName.RECEPTIONIST: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
            CustomerPermissionName.ADD_CUSTOMER.value,
            CustomerPermissionName.CHANGE_CUSTOMER.value,
            VehiclePermissionName.VIEW_VEHICLE.value,
            VehiclePermissionName.ADD_VEHICLE.value,
            VehiclePermissionName.CHANGE_VEHICLE.value,
            VehiclePermissionName.TRANSFER_VEHICLE_OWNER.value,
        }
    ),
    RoleName.SENIOR_TECHNICIAN: frozenset(
        {
            VehiclePermissionName.VIEW_VEHICLE.value,
        }
    ),
    RoleName.TECHNICIAN: frozenset(
        {
            VehiclePermissionName.VIEW_VEHICLE.value,
        }
    ),
    RoleName.CASHIER: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
            CustomerPermissionName.ADD_CUSTOMER.value,
            CustomerPermissionName.CHANGE_CUSTOMER.value,
            VehiclePermissionName.VIEW_VEHICLE.value,
        }
    ),
    RoleName.MANAGER: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
            VehiclePermissionName.VIEW_VEHICLE.value,
        }
    ),
}
