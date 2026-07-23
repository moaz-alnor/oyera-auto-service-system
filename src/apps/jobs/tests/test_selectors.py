"""Tests for job-card read queries."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.constants import (
    InspectionType,
    JobNoteType,
    JobPriority,
    JobStatus,
)
from apps.jobs.selectors import (
    get_job_inspections,
    get_job_notes,
    search_job_cards,
)
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


@pytest.fixture
def receptionist() -> User:
    """Create a receptionist for job selector tests."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.selector.receptionist",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create a technician for inspection selector tests."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.selector.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def customer(receptionist: User) -> Customer:
    """Create an active job-card customer."""

    customer = Customer(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        email="daniel@example.com",
        created_by=receptionist,
        updated_by=receptionist,
    )
    customer.full_clean()
    customer.save()

    return customer


@pytest.fixture
def vehicles(
    receptionist: User,
    customer: Customer,
) -> tuple[Vehicle, Vehicle]:
    """Create two active vehicles for the same customer."""

    first_vehicle = Vehicle(
        vehicle_number="VEH-000001",
        registration_number="UBD 245X",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        year=2018,
        color="Silver",
        current_mileage=45000,
        created_by=receptionist,
        updated_by=receptionist,
    )
    first_vehicle.full_clean()
    first_vehicle.save()

    second_vehicle = Vehicle(
        vehicle_number="VEH-000002",
        registration_number="UBE 310A",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Honda",
        model="Fit",
        year=2019,
        color="Blue",
        current_mileage=32000,
        created_by=receptionist,
        updated_by=receptionist,
    )
    second_vehicle.full_clean()
    second_vehicle.save()

    return first_vehicle, second_vehicle


@pytest.fixture
def job_records(
    receptionist: User,
    customer: Customer,
    vehicles: tuple[Vehicle, Vehicle],
) -> tuple:
    """Create one active and one cancelled job card."""

    first_vehicle, second_vehicle = vehicles

    active_job = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=first_vehicle.pk,
            arrival_mileage=45500,
            customer_complaint=("Brake vibration under heavy braking."),
            priority=JobPriority.URGENT,
        ),
    )

    cancelled_job = open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=second_vehicle.pk,
            arrival_mileage=32100,
            customer_complaint="Routine engine service.",
            priority=JobPriority.NORMAL,
        ),
    )

    cancel_job_card(
        actor=receptionist,
        job_card_id=cancelled_job.pk,
        command=CancelJobCardCommand(reason="Customer postponed the service."),
    )
    cancelled_job.refresh_from_db()

    return active_job, cancelled_job


@pytest.mark.django_db
def test_job_search_finds_job_number(
    job_records: tuple,
) -> None:
    """Find a job using its generated number."""

    active_job, _ = job_records

    results = search_job_cards(query=active_job.job_number)

    assert list(results) == [active_job]


@pytest.mark.django_db
def test_job_search_finds_snapshot_information(
    job_records: tuple,
) -> None:
    """Find jobs using preserved customer and vehicle snapshots."""

    active_job, _ = job_records

    customer_results = search_job_cards(query="Daniel Kato")
    vehicle_results = search_job_cards(query="UBD 245X")

    assert active_job in customer_results
    assert list(vehicle_results) == [active_job]


@pytest.mark.django_db
def test_job_search_filters_status(
    job_records: tuple,
) -> None:
    """Return only jobs with the selected status."""

    _, cancelled_job = job_records

    results = search_job_cards(status=JobStatus.CANCELLED)

    assert list(results) == [cancelled_job]


@pytest.mark.django_db
def test_job_search_filters_priority(
    job_records: tuple,
) -> None:
    """Return only jobs with the selected priority."""

    active_job, _ = job_records

    results = search_job_cards(priority=JobPriority.URGENT)

    assert list(results) == [active_job]


@pytest.mark.django_db
def test_inspections_and_notes_are_returned_newest_first(
    receptionist: User,
    technician: User,
    job_records: tuple,
) -> None:
    """Order append-only job history from newest to oldest."""

    active_job, _ = job_records
    earlier_time = timezone.now() - timedelta(hours=2)
    later_time = timezone.now() - timedelta(hours=1)

    first_inspection = add_inspection(
        actor=technician,
        job_card_id=active_job.pk,
        command=AddInspectionCommand(
            inspection_type=InspectionType.INITIAL,
            findings="Brake pads require measurement.",
            inspected_at=earlier_time,
        ),
    )
    second_inspection = add_inspection(
        actor=technician,
        job_card_id=active_job.pk,
        command=AddInspectionCommand(
            inspection_type=InspectionType.SAFETY,
            findings="Front brake pads are below limit.",
            inspected_at=later_time,
        ),
    )

    first_note = add_job_note(
        actor=receptionist,
        job_card_id=active_job.pk,
        command=AddJobNoteCommand(
            note_type=JobNoteType.GENERAL,
            content="Vehicle entered the inspection bay.",
        ),
    )
    second_note = add_job_note(
        actor=receptionist,
        job_card_id=active_job.pk,
        command=AddJobNoteCommand(
            note_type=JobNoteType.CUSTOMER_COMMUNICATION,
            content="Customer was informed of findings.",
        ),
    )

    first_note.created_at = earlier_time
    first_note.save(update_fields=("created_at",))

    second_note.created_at = later_time
    second_note.save(update_fields=("created_at",))

    inspections = list(get_job_inspections(job_card_id=active_job.pk))
    notes = list(get_job_notes(job_card_id=active_job.pk))

    assert inspections == [
        second_inspection,
        first_inspection,
    ]
    assert notes == [
        second_note,
        first_note,
    ]
