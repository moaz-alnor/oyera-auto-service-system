"""Authorization policy for employee roles."""

from apps.accounts.constants import PermissionName, RoleName
from apps.customers.constants import CustomerPermissionName

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
        }
    ),
    RoleName.RECEPTIONIST: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
            CustomerPermissionName.ADD_CUSTOMER.value,
            CustomerPermissionName.CHANGE_CUSTOMER.value,
        }
    ),
    RoleName.SENIOR_TECHNICIAN: frozenset(),
    RoleName.TECHNICIAN: frozenset(),
    RoleName.CASHIER: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
            CustomerPermissionName.ADD_CUSTOMER.value,
            CustomerPermissionName.CHANGE_CUSTOMER.value,
        }
    ),
    RoleName.MANAGER: frozenset(
        {
            CustomerPermissionName.VIEW_CUSTOMER.value,
        }
    ),
}
