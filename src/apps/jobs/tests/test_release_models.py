"""Tests for vehicle-release model validation."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.constants import JobStatus
from apps.jobs.models import (
    JobCard,
    VehicleRelease,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


@dataclass(frozen=True, slots=True)
class ReleaseModelContext:
    """Contain records used by release-model tests."""

    actor: User
    job_card: JobCard


@pytest.fixture
def release_model_context() -> ReleaseModelContext:
    """Create one released job and vehicle."""

    actor = User.objects.create_user(
        username="release.model.manager",
        password="Strong-Test-Password-2026",
    )

    customer = Customer(
        customer_number="CUS-REL-001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Release Model Customer",
        phone_number="0700111222",
        email="release@example.com",
        created_by=actor,
        updated_by=actor,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-REL-001",
        registration_number="UBR 100R",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        year=2022,
        color="Silver",
        current_mileage=45000,
        created_by=actor,
        updated_by=actor,
    )
    vehicle.full_clean()
    vehicle.save()

    job_card = JobCard(
        job_number="JOB-REL-001",
        customer=customer,
        vehicle=vehicle,
        customer_name_snapshot=customer.name,
        customer_phone_snapshot=customer.phone_number,
        customer_email_snapshot=customer.email,
        vehicle_registration_snapshot=(vehicle.registration_number),
        vehicle_make_snapshot=vehicle.make,
        vehicle_model_snapshot=vehicle.model,
        vehicle_year_snapshot=vehicle.year,
        vehicle_color_snapshot=vehicle.color,
        arrival_mileage=45000,
        customer_complaint="Release model test.",
        status=JobStatus.RELEASED,
        created_by=actor,
        updated_by=actor,
    )
    job_card.full_clean()
    job_card.save()

    return ReleaseModelContext(
        actor=actor,
        job_card=job_card,
    )


def _paid_release(
    *,
    context: ReleaseModelContext,
) -> VehicleRelease:
    """Build one valid fully paid vehicle release."""

    return VehicleRelease(
        release_number="REL-TEST-001",
        job_card=context.job_card,
        final_mileage=45100,
        final_condition=("Vehicle clean and operating normally."),
        received_by_name="Amina Musa",
        received_by_contact="0700222333",
        handover_notes="Keys and documents handed over.",
        invoice_number_snapshot="INV-000001",
        invoice_status_snapshot="PAID",
        invoice_currency_snapshot="UGX",
        invoice_total_snapshot=Decimal("80000.00"),
        paid_amount_snapshot=Decimal("80000.00"),
        outstanding_amount_snapshot=Decimal("0.00"),
        released_by=context.actor,
    )


@pytest.mark.django_db
def test_valid_paid_release_normalizes_text(
    release_model_context: ReleaseModelContext,
) -> None:
    """Validate and normalize a paid vehicle handover."""

    release = _paid_release(context=release_model_context)
    release.received_by_name = "  Amina Musa  "
    release.handover_notes = "  Keys handed over.  "
    release.invoice_currency_snapshot = "ugx"

    release.full_clean()
    release.save()

    assert release.received_by_name == "Amina Musa"
    assert release.handover_notes == "Keys handed over."
    assert release.invoice_currency_snapshot == "UGX"
    assert str(release).startswith("REL-TEST-001")


@pytest.mark.django_db
def test_release_rejects_lower_final_mileage(
    release_model_context: ReleaseModelContext,
) -> None:
    """Reject mileage below intake or current mileage."""

    release = _paid_release(context=release_model_context)
    release.final_mileage = 44999

    with pytest.raises(ValidationError) as exc_info:
        release.full_clean()

    assert "final_mileage" in exc_info.value.message_dict


@pytest.mark.django_db
def test_unpaid_release_requires_override(
    release_model_context: ReleaseModelContext,
) -> None:
    """Require explicit authorisation for unpaid release."""

    release = _paid_release(context=release_model_context)
    release.invoice_status_snapshot = "PARTIALLY_PAID"
    release.paid_amount_snapshot = Decimal("30000.00")
    release.outstanding_amount_snapshot = Decimal("50000.00")

    with pytest.raises(ValidationError) as exc_info:
        release.full_clean()

    assert "payment_override" in (exc_info.value.message_dict)


@pytest.mark.django_db
def test_override_requires_complete_audit_metadata(
    release_model_context: ReleaseModelContext,
) -> None:
    """Require reason, actor, and time for an override."""

    release = _paid_release(context=release_model_context)
    release.invoice_status_snapshot = "PARTIALLY_PAID"
    release.paid_amount_snapshot = Decimal("30000.00")
    release.outstanding_amount_snapshot = Decimal("50000.00")
    release.payment_override = True

    with pytest.raises(ValidationError) as exc_info:
        release.full_clean()

    assert "payment_override_reason" in (exc_info.value.message_dict)
    assert "payment_override_by" in (exc_info.value.message_dict)
    assert "payment_override_at" in (exc_info.value.message_dict)

    release.payment_override_reason = "Manager approved corporate credit."
    release.payment_override_by = release_model_context.actor
    release.payment_override_at = timezone.now()

    release.full_clean()
