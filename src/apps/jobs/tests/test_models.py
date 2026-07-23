"""Tests for job-card models."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.constants import JobStatus
from apps.jobs.models import JobCard
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


@pytest.mark.django_db
def test_cancelled_job_requires_reason() -> None:
    """Reject a cancelled job without a cancellation reason."""

    actor = User.objects.create_user(
        username="job.model.employee",
        password="Strong-Test-Password-2026",
    )
    customer = Customer(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        created_by=actor,
        updated_by=actor,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        created_by=actor,
        updated_by=actor,
    )
    vehicle.full_clean()
    vehicle.save()

    job_card = JobCard(
        job_number="JOB-000001",
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
        customer_complaint="Engine noise.",
        status=JobStatus.CANCELLED,
        created_by=actor,
        updated_by=actor,
    )

    with pytest.raises(ValidationError):
        job_card.full_clean()
