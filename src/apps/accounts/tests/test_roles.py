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


@pytest.mark.django_db
def test_administrator_receives_account_permissions() -> None:
    """Assign approved account-management permissions to administrators."""

    ensure_default_roles()

    administrator = Group.objects.get(name=RoleName.ADMINISTRATOR.value)

    stored_permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            administrator.permissions.filter(
                content_type__app_label="accounts"
            ).values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert stored_permissions == {
        "accounts.view_user",
        "accounts.add_user",
        "accounts.change_user",
    }


@pytest.mark.django_db
def test_other_roles_receive_no_account_permissions() -> None:
    """Avoid granting account management to operational roles."""

    ensure_default_roles()

    operational_roles = Group.objects.exclude(name=RoleName.ADMINISTRATOR.value)

    assert not operational_roles.filter(
        permissions__content_type__app_label="accounts"
    ).exists()
