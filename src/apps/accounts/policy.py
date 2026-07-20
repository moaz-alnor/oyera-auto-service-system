"""Authorization policy for employee roles."""

from apps.accounts.constants import PermissionName, RoleName

ROLE_PERMISSION_POLICY: dict[
    RoleName,
    frozenset[PermissionName],
] = {
    RoleName.ADMINISTRATOR: frozenset(
        {
            PermissionName.VIEW_USER,
            PermissionName.ADD_USER,
            PermissionName.CHANGE_USER,
        }
    ),
    RoleName.RECEPTIONIST: frozenset(),
    RoleName.SENIOR_TECHNICIAN: frozenset(),
    RoleName.TECHNICIAN: frozenset(),
    RoleName.CASHIER: frozenset(),
    RoleName.MANAGER: frozenset(),
}
