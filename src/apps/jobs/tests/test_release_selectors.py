"""Tests for vehicle-release selectors."""

from decimal import Decimal

import pytest

from apps.jobs.constants import JobStatus
from apps.jobs.models import VehicleRelease
from apps.jobs.selectors import (
    get_vehicle_release_by_id,
    get_vehicle_release_for_job,
    vehicle_release_list_queryset,
)
from apps.jobs.tests.conftest import ReleaseTestContext


def _create_release(
    *,
    context: ReleaseTestContext,
) -> VehicleRelease:
    """Create one valid release record for selector tests."""

    context.job_card.status = JobStatus.RELEASED
    context.job_card.updated_by = context.manager
    context.job_card.full_clean()
    context.job_card.save(
        update_fields=(
            "status",
            "updated_by",
            "updated_at",
        )
    )

    release = VehicleRelease(
        release_number="REL-SELECTOR-001",
        job_card=context.job_card,
        final_mileage=45100,
        final_condition=("Vehicle clean and ready for collection."),
        received_by_name="Amina Musa",
        received_by_contact="0700222333",
        handover_notes="Keys handed over.",
        invoice_number_snapshot="INV-SELECTOR-001",
        invoice_status_snapshot="PAID",
        invoice_currency_snapshot="UGX",
        invoice_total_snapshot=Decimal("80000.00"),
        paid_amount_snapshot=Decimal("80000.00"),
        outstanding_amount_snapshot=Decimal("0.00"),
        released_by=context.manager,
    )
    release.full_clean()
    release.save()

    return release


@pytest.mark.django_db
def test_release_list_returns_related_handover_records(
    release_context: ReleaseTestContext,
) -> None:
    """Return releases with their job and actors."""

    release = _create_release(context=release_context)

    releases = list(vehicle_release_list_queryset())

    assert releases == [release]
    assert releases[0].job_card == (release_context.job_card)
    assert releases[0].released_by == (release_context.manager)


@pytest.mark.django_db
def test_get_vehicle_release_by_id(
    release_context: ReleaseTestContext,
) -> None:
    """Return one handover by release identifier."""

    release = _create_release(context=release_context)

    selected = get_vehicle_release_by_id(release_id=release.pk)

    assert selected == release


@pytest.mark.django_db
def test_get_vehicle_release_for_job(
    release_context: ReleaseTestContext,
) -> None:
    """Return the handover attached to a job card."""

    release = _create_release(context=release_context)

    selected = get_vehicle_release_for_job(job_card_id=release_context.job_card.pk)

    assert selected == release
