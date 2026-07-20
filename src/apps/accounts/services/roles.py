"""Application services for managing employee roles."""

from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.accounts.constants import RoleName


@dataclass(frozen=True)
class RoleSeedResult:
    """Describe the result of ensuring that default roles exist."""

    created_roles: tuple[str, ...]
    existing_roles: tuple[str, ...]


@transaction.atomic
def ensure_default_roles() -> RoleSeedResult:
    """Create any missing default employee roles.

    Returns:
        A result containing the role names that were created and those
        that already existed.
    """

    created_roles: list[str] = []
    existing_roles: list[str] = []

    for role_name in RoleName:
        _, created = Group.objects.get_or_create(name=role_name.value)

        if created:
            created_roles.append(role_name.value)
        else:
            existing_roles.append(role_name.value)

    return RoleSeedResult(
        created_roles=tuple(created_roles),
        existing_roles=tuple(existing_roles),
    )
