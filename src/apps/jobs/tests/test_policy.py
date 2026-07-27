"""Tests for job-card role permissions."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.services.roles import ensure_default_roles


@pytest.mark.django_db
def test_manager_receives_complete_job_permissions() -> None:
    """Allow managers to supervise all job-card workflows."""

    ensure_default_roles()

    manager = Group.objects.get(name=RoleName.MANAGER.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            manager.permissions.filter(content_type__app_label="jobs").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "jobs.view_jobcard",
        "jobs.add_jobcard",
        "jobs.change_jobcard",
        "jobs.cancel_jobcard",
        "jobs.view_inspection",
        "jobs.add_inspection",
        "jobs.view_jobnote",
        "jobs.add_jobnote",
        "jobs.view_vehiclerelease",
        "jobs.release_vehicle",
        "jobs.override_vehicle_release_payment",
    }


@pytest.mark.django_db
def test_technician_receives_operational_job_permissions() -> None:
    """Allow technicians to inspect jobs and append notes."""

    ensure_default_roles()

    technician = Group.objects.get(name=RoleName.TECHNICIAN.value)

    permissions = {
        f"{app_label}.{codename}"
        for app_label, codename in (
            technician.permissions.filter(content_type__app_label="jobs").values_list(
                "content_type__app_label",
                "codename",
            )
        )
    }

    assert permissions == {
        "jobs.view_jobcard",
        "jobs.view_inspection",
        "jobs.add_inspection",
        "jobs.view_jobnote",
        "jobs.add_jobnote",
    }
