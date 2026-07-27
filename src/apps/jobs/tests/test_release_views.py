"""Tests for vehicle-release browser workflows."""

import pytest
from django.urls import reverse

from apps.jobs.constants import JobStatus
from apps.jobs.models import VehicleRelease
from apps.jobs.services.releases import (
    ReleaseVehicleCommand,
    release_vehicle,
)
from apps.jobs.tests.conftest import ReleaseTestContext
from apps.jobs.tests.test_releases import (
    _issue_invoice,
    _pay_invoice,
)


@pytest.mark.django_db
def test_release_page_requires_authentication(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Redirect anonymous users to employee login."""

    response = client.get(
        reverse(
            "jobs:release_create",
            args=(release_context.job_card.pk,),
        )
    )

    assert response.status_code == 302
    assert reverse("accounts:login") in (response.headers["Location"])


@pytest.mark.django_db
def test_technician_cannot_open_release_page(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Return HTTP 403 without release permission."""

    client.force_login(release_context.technician)

    response = client.get(
        reverse(
            "jobs:release_create",
            args=(release_context.job_card.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_paid_release_page_displays_invoice(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Display workshop and billing handover context."""

    invoice = _pay_invoice(context=release_context)
    client.force_login(release_context.receptionist)

    response = client.get(
        reverse(
            "jobs:release_create",
            args=(release_context.job_card.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert invoice.invoice_number in content
    assert "80000.00" in content
    assert "Release vehicle" in content


@pytest.mark.django_db
def test_receptionist_releases_paid_vehicle(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Release a fully paid vehicle from the browser."""

    _pay_invoice(context=release_context)
    client.force_login(release_context.receptionist)

    response = client.post(
        reverse(
            "jobs:release_create",
            args=(release_context.job_card.pk,),
        ),
        {
            "final_mileage": 45100,
            "final_condition": ("Vehicle clean and operating normally."),
            "received_by_name": "Amina Musa",
            "received_by_contact": "0700222333",
            "handover_notes": ("Keys and documents handed over."),
        },
    )

    vehicle_release = VehicleRelease.objects.get(job_card=release_context.job_card)
    release_context.job_card.refresh_from_db()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "jobs:release_detail",
        args=(vehicle_release.pk,),
    )
    assert release_context.job_card.status == (JobStatus.RELEASED)


@pytest.mark.django_db
def test_manager_authorises_unpaid_release(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Record payment override through the browser."""

    _issue_invoice(context=release_context)
    client.force_login(release_context.manager)

    response = client.post(
        reverse(
            "jobs:release_create",
            args=(release_context.job_card.pk,),
        ),
        {
            "final_mileage": 45100,
            "final_condition": ("Vehicle clean and operating normally."),
            "received_by_name": "Amina Musa",
            "received_by_contact": "",
            "handover_notes": "",
            "payment_override": "on",
            "payment_override_reason": ("Manager approved corporate credit."),
        },
    )

    vehicle_release = VehicleRelease.objects.get(job_card=release_context.job_card)

    assert response.status_code == 302
    assert vehicle_release.payment_override is True
    assert vehicle_release.payment_override_by == (release_context.manager)


@pytest.mark.django_db
def test_release_detail_displays_audit_record(
    client,
    release_context: ReleaseTestContext,
) -> None:
    """Display the permanent handover record."""

    _pay_invoice(context=release_context)

    vehicle_release = release_vehicle(
        actor=release_context.receptionist,
        command=ReleaseVehicleCommand(
            job_card_id=(release_context.job_card.pk),
            final_mileage=45100,
            final_condition=("Vehicle clean and operating normally."),
            received_by_name="Amina Musa",
            received_by_contact="0700222333",
            handover_notes="Keys handed over.",
        ),
    )

    client.force_login(release_context.manager)

    response = client.get(
        reverse(
            "jobs:release_detail",
            args=(vehicle_release.pk,),
        )
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert vehicle_release.release_number in content
    assert "Amina Musa" in content
    assert "Vehicle released" in content
    assert "80000.00" in content
