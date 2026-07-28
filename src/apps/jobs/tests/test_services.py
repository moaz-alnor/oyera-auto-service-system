"""Tests for job-card application services."""

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.constants import (
    InspectionType,
    JobNoteType,
    JobStatus,
)
from apps.jobs.models import JobCard, JobNote
from apps.jobs.services.inspections import (
    AddInspectionCommand,
    AddJobNoteCommand,
    add_inspection,
    add_job_note,
)
from apps.jobs.services.intake import (
    CancelJobCardCommand,
    OpenJobCardCommand,
    cancel_job_card,
    open_job_card,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


def _create_receptionist() -> User:
    """Create a receptionist with job-intake permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.intake.receptionist",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    return employee


def _create_technician() -> User:
    """Create a technician with inspection permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.inspection.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


def _create_customer_and_vehicle(
    *,
    actor: User,
    mileage: int = 45000,
) -> tuple[Customer, Vehicle]:
    """Create active visit participants."""

    customer = Customer(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        email="daniel@example.com",
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
        year=2018,
        color="Silver",
        current_mileage=mileage,
        created_by=actor,
        updated_by=actor,
    )
    vehicle.full_clean()
    vehicle.save()

    return customer, vehicle


@pytest.mark.django_db
def test_receptionist_can_open_job_with_snapshots() -> None:
    """Open a numbered job and preserve visit snapshots."""

    receptionist = _create_receptionist()
    customer, vehicle = _create_customer_and_vehicle(actor=receptionist)

    job_card = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45500,
            customer_complaint="Engine noise under acceleration.",
        ),
    )

    vehicle.refresh_from_db()

    assert job_card.job_number == (f"JOB-{job_card.pk:06d}")
    assert job_card.status == JobStatus.OPEN
    assert job_card.customer_name_snapshot == "Daniel Kato"
    assert job_card.vehicle_registration_snapshot == "UBD 245X"
    assert vehicle.current_mileage == 45500


@pytest.mark.django_db
def test_job_rejects_lower_arrival_mileage() -> None:
    """Reject an odometer value below the stored mileage."""

    receptionist = _create_receptionist()
    customer, vehicle = _create_customer_and_vehicle(
        actor=receptionist,
        mileage=45000,
    )

    with pytest.raises(ValidationError):
        open_job_card(
            actor=receptionist,
            command=OpenJobCardCommand(
                customer_id=customer.pk,
                vehicle_id=vehicle.pk,
                arrival_mileage=44000,
                customer_complaint="Routine service.",
            ),
        )


@pytest.mark.django_db
def test_vehicle_cannot_have_two_active_jobs() -> None:
    """Prevent concurrent active job cards for one vehicle."""

    receptionist = _create_receptionist()
    customer, vehicle = _create_customer_and_vehicle(actor=receptionist)

    command = OpenJobCardCommand(
        customer_id=customer.pk,
        vehicle_id=vehicle.pk,
        arrival_mileage=45000,
        customer_complaint="Routine service.",
    )

    open_job_card(
        actor=receptionist,
        command=command,
    )

    with pytest.raises(ValidationError):
        open_job_card(
            actor=receptionist,
            command=command,
        )


@pytest.mark.django_db
def test_inspection_marks_open_job_as_inspected() -> None:
    """Append an inspection and advance the job state."""

    receptionist = _create_receptionist()
    technician = _create_technician()
    customer, vehicle = _create_customer_and_vehicle(actor=receptionist)
    job_card = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Brake noise.",
        ),
    )

    inspection = add_inspection(
        actor=technician,
        job_card_id=job_card.pk,
        command=AddInspectionCommand(
            inspection_type=InspectionType.INITIAL,
            findings="Front brake pads are worn.",
            recommended_action="Replace front brake pads.",
        ),
    )

    job_card.refresh_from_db()

    assert inspection.job_card == job_card
    assert job_card.status == JobStatus.INSPECTED


@pytest.mark.django_db
def test_job_notes_are_appended() -> None:
    """Preserve multiple notes as separate records."""

    receptionist = _create_receptionist()
    customer, vehicle = _create_customer_and_vehicle(actor=receptionist)
    job_card = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Routine service.",
        ),
    )

    add_job_note(
        actor=receptionist,
        job_card_id=job_card.pk,
        command=AddJobNoteCommand(
            note_type=JobNoteType.CUSTOMER_COMMUNICATION,
            content="Customer approved initial inspection.",
        ),
    )
    add_job_note(
        actor=receptionist,
        job_card_id=job_card.pk,
        command=AddJobNoteCommand(
            note_type=JobNoteType.GENERAL,
            content="Vehicle moved to service bay.",
        ),
    )

    assert JobNote.objects.filter(job_card=job_card).count() == 2


@pytest.mark.django_db
def test_cancelled_job_allows_new_visit() -> None:
    """Allow a new active job after the earlier one is cancelled."""

    receptionist = _create_receptionist()
    customer, vehicle = _create_customer_and_vehicle(actor=receptionist)
    first_job = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Routine service.",
        ),
    )

    cancel_job_card(
        actor=receptionist,
        job_card_id=first_job.pk,
        command=CancelJobCardCommand(reason="Customer postponed the work."),
    )

    second_job = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Customer returned.",
        ),
    )

    assert JobCard.objects.filter(vehicle=vehicle).count() == 2
    assert first_job.pk != second_job.pk
