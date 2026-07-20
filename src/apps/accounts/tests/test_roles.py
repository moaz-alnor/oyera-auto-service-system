"""Tests for employee-role configuration."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_default_roles_are_created() -> None:
    """Create every supported employee role."""

    result = ensure_default_roles()

    expected_roles = {role.value for role in RoleName}
    stored_roles = set(
        Group.objects.filter(name__in=expected_roles).values_list(
            "name",
            flat=True,
        )
    )

    assert stored_roles == expected_roles
    assert set(result.created_roles) == expected_roles
    assert result.existing_roles == ()


@pytest.mark.django_db
def test_role_creation_is_idempotent() -> None:
    """Avoid creating duplicate roles when setup runs repeatedly."""

    ensure_default_roles()
    second_result = ensure_default_roles()

    assert second_result.created_roles == ()
    assert set(second_result.existing_roles) == {role.value for role in RoleName}
    assert Group.objects.count() == len(RoleName)
