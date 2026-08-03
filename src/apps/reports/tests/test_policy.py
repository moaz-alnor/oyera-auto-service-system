"""Tests for operational-report permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import (
    ensure_default_roles,
)
from apps.reports.constants import (
    ReportPermissionName,
)

_EXPECTED_REPORT_PERMISSIONS = {
    RoleName.ADMINISTRATOR: frozenset(
        permission.value for permission in ReportPermissionName
    ),
    RoleName.RECEPTIONIST: frozenset(
        {
            ReportPermissionName.ACCESS_REPORTS.value,
            ReportPermissionName.VIEW_WORKSHOP_REPORT.value,
        }
    ),
    RoleName.SENIOR_TECHNICIAN: frozenset(
        {
            ReportPermissionName.ACCESS_REPORTS.value,
            ReportPermissionName.VIEW_WORKSHOP_REPORT.value,
        }
    ),
    RoleName.TECHNICIAN: frozenset(),
    RoleName.CASHIER: frozenset(
        {
            ReportPermissionName.ACCESS_REPORTS.value,
            ReportPermissionName.VIEW_CUSTOMER_FINANCE_REPORT.value,
            ReportPermissionName.VIEW_PURCHASING_REPORT.value,
            ReportPermissionName.EXPORT_REPORTS.value,
        }
    ),
    RoleName.MANAGER: frozenset(
        permission.value for permission in ReportPermissionName
    ),
}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "expected_permissions"),
    tuple(_EXPECTED_REPORT_PERMISSIONS.items()),
)
def test_report_permissions_follow_role_policy(
    role: RoleName,
    expected_permissions: frozenset[str],
) -> None:
    """Assign only approved reporting permissions."""

    ensure_default_roles()

    group = Group.objects.get(name=role.value)

    stored_permissions = frozenset(
        f"{app_label}.{codename}"
        for app_label, codename in (
            group.permissions.filter(content_type__app_label="reports").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    )

    assert stored_permissions == expected_permissions
