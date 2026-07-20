"""Application services for managing employee roles."""

from dataclasses import dataclass

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from apps.accounts.constants import PermissionName, RoleName
from apps.accounts.policy import ROLE_PERMISSION_POLICY


@dataclass(frozen=True)
class RoleSeedResult:
    """Describe the result of synchronizing default roles."""

    created_roles: tuple[str, ...]
    existing_roles: tuple[str, ...]


def _resolve_permissions(
    permission_names: frozenset[PermissionName],
) -> tuple[Permission, ...]:
    """Resolve permission identifiers into database records.

    Args:
        permission_names: Fully qualified permission identifiers.

    Returns:
        Permission records matching the supplied identifiers.

    Raises:
        ImproperlyConfigured: If the policy references a permission that
            does not exist in the database.
    """

    permissions: list[Permission] = []

    for permission_name in permission_names:
        app_label, codename = permission_name.value.split(
            ".",
            maxsplit=1,
        )

        try:
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
        except Permission.DoesNotExist as exc:
            raise ImproperlyConfigured(
                "The authorization policy references a missing "
                f"permission: {permission_name.value}. Run migrations "
                "before synchronizing roles."
            ) from exc

        permissions.append(permission)

    return tuple(permissions)


@transaction.atomic
def ensure_default_roles() -> RoleSeedResult:
    """Create default roles and synchronize their permissions.

    The policy is treated as the source of truth. Running this service
    repeatedly produces the same role and permission configuration.

    Returns:
        A result containing newly created and previously existing roles.
    """

    created_roles: list[str] = []
    existing_roles: list[str] = []

    for role_name in RoleName:
        group, created = Group.objects.get_or_create(
            name=role_name.value,
        )

        permissions = _resolve_permissions(ROLE_PERMISSION_POLICY[role_name])

        # Replace the group's permissions with the approved policy so old
        # or accidentally assigned permissions do not remain active.
        group.permissions.set(permissions)

        if created:
            created_roles.append(role_name.value)
        else:
            existing_roles.append(role_name.value)

    return RoleSeedResult(
        created_roles=tuple(created_roles),
        existing_roles=tuple(existing_roles),
    )
