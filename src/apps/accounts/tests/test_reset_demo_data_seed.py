"""Integration tests for generated OYERA demonstration data."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.constants import RoleName

EXPECTED_DEMO_ACCOUNTS = {
    RoleName.ADMINISTRATOR: (
        "admin",
        "AdminDemo123!",
    ),
    RoleName.MANAGER: (
        "manager",
        "ManagerDemo123!",
    ),
    RoleName.RECEPTIONIST: (
        "receptionist",
        "ReceptionDemo123!",
    ),
    RoleName.SENIOR_TECHNICIAN: (
        "senior_technician",
        "SeniorTechDemo123!",
    ),
    RoleName.TECHNICIAN: (
        "technician",
        "TechnicianDemo123!",
    ),
    RoleName.CASHIER: (
        "cashier",
        "CashierDemo123!",
    ),
}


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_reset_demo_data_creates_all_role_accounts() -> None:
    """Create one usable active account for every UAT role."""
    output = StringIO()

    call_command(
        "reset_demo_data",
        yes=True,
        verbosity=0,
        stdout=output,
    )

    command_output = output.getvalue()
    user_model = get_user_model()

    assert user_model.objects.count() == len(EXPECTED_DEMO_ACCOUNTS)

    for role, credentials in EXPECTED_DEMO_ACCOUNTS.items():
        username, password = credentials
        user = user_model.objects.get(
            username=username,
        )

        assert user.is_active is True
        assert user.check_password(password) is True
        assert username in command_output
        assert password in command_output
        assert list(
            user.groups.values_list(
                "name",
                flat=True,
            )
        ) == [role.value]

    expected_output_lines = (
        "admin / AdminDemo123! — Django administrator",
        "manager / ManagerDemo123! — operational manager",
        "cashier / CashierDemo123! — cashier",
        ("senior_technician / SeniorTechDemo123! — senior technician"),
        "technician / TechnicianDemo123! — technician",
        "receptionist / ReceptionDemo123! — receptionist",
    )

    for expected_line in expected_output_lines:
        assert expected_line in command_output

    administrator = user_model.objects.get(
        username="admin",
    )

    assert administrator.is_staff is True
    assert administrator.is_superuser is True
