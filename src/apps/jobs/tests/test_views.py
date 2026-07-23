"""Tests for job-card HTTP workflows."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.constants import (
    FuelLevel,
    InspectionType,
    JobNoteType,
    JobPriority,
    JobStatus,
)
from apps.jobs.models import Inspection, JobCard, JobNote
from apps.jobs.services.intake import (
    OpenJobCardCommand,
    open_job_card,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


@pytest.fixture
def receptionist() -> User:
    """Create a receptionist with job-intake permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.view.receptionist",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create a technician with inspection permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="job.view.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def customer(receptionist: User) -> Customer:
    """Create an active customer for job view tests."""

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
def vehicle(
    receptionist: User,
    customer: Customer,
) -> Vehicle:
    """Create an active vehicle for job view tests."""

    vehicle = Vehicle(
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
    vehicle.full_clean()
    vehicle.save()

    return vehicle


@pytest.fixture
def job_card(
    receptionist: User,
    customer: Customer,
    vehicle: Vehicle,
) -> JobCard:
    """Open a job card through the application service."""

    return open_job_card(
        actor=receptionist,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45500,
            customer_complaint="Brake vibration.",
        ),
    )


@pytest.mark.django_db
def test_job_list_requires_authentication(client) -> None:
    """Redirect anonymous visitors to employee login."""

    response = client.get(reverse("jobs:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_technician_can_view_job_list(
    client,
    technician: User,
) -> None:
    """Allow technicians to inspect existing job cards."""

    client.force_login(technician)

    response = client.get(reverse("jobs:list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_technician_cannot_open_job_card(
    client,
    technician: User,
) -> None:
    """Return HTTP 403 for unauthorized intake attempts."""

    client.force_login(technician)

    response = client.get(reverse("jobs:create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_receptionist_can_open_job_card(
    client,
    receptionist: User,
    customer: Customer,
    vehicle: Vehicle,
) -> None:
    """Open a numbered job through the HTTP workflow."""

    client.force_login(receptionist)

    response = client.post(
        reverse("jobs:create"),
        {
            "customer": customer.pk,
            "vehicle": vehicle.pk,
            "arrival_mileage": 45500,
            "customer_complaint": ("Brake vibration under heavy braking."),
            "visible_condition": ("Minor scratch on rear bumper."),
            "fuel_level": FuelLevel.HALF,
            "priority": JobPriority.URGENT,
        },
    )

    job_card = JobCard.objects.get(vehicle=vehicle)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "jobs:detail",
        args=(job_card.pk,),
    )
    assert job_card.job_number.startswith("JOB-")
    assert job_card.priority == JobPriority.URGENT


@pytest.mark.django_db
def test_lower_arrival_mileage_is_shown_as_form_error(
    client,
    receptionist: User,
    customer: Customer,
    vehicle: Vehicle,
) -> None:
    """Show mileage validation without creating a job."""

    client.force_login(receptionist)

    response = client.post(
        reverse("jobs:create"),
        {
            "customer": customer.pk,
            "vehicle": vehicle.pk,
            "arrival_mileage": 44000,
            "customer_complaint": "Routine service.",
            "visible_condition": "",
            "fuel_level": FuelLevel.UNKNOWN,
            "priority": JobPriority.NORMAL,
        },
    )

    assert response.status_code == 200
    assert b"Arrival mileage cannot be lower" in response.content
    assert not JobCard.objects.exists()


@pytest.mark.django_db
def test_technician_can_add_inspection(
    client,
    technician: User,
    job_card: JobCard,
) -> None:
    """Append an inspection and advance the job status."""

    client.force_login(technician)

    response = client.post(
        reverse(
            "jobs:inspection_create",
            args=(job_card.pk,),
        ),
        {
            "inspection_type": InspectionType.INITIAL,
            "findings": "Front brake pads are worn.",
            "safety_observations": ("Braking performance may be reduced."),
            "recommended_action": ("Replace the front brake-pad set."),
        },
    )

    job_card.refresh_from_db()

    assert response.status_code == 302
    assert Inspection.objects.filter(job_card=job_card).count() == 1
    assert job_card.status == JobStatus.INSPECTED


@pytest.mark.django_db
def test_receptionist_can_add_job_note(
    client,
    receptionist: User,
    job_card: JobCard,
) -> None:
    """Append a communication note through the interface."""

    client.force_login(receptionist)

    response = client.post(
        reverse(
            "jobs:note_create",
            args=(job_card.pk,),
        ),
        {
            "note_type": (JobNoteType.CUSTOMER_COMMUNICATION),
            "content": ("Customer approved the initial inspection."),
        },
    )

    assert response.status_code == 302
    assert JobNote.objects.filter(
        job_card=job_card,
        content=("Customer approved the initial inspection."),
    ).exists()


@pytest.mark.django_db
def test_receptionist_can_cancel_job_card(
    client,
    receptionist: User,
    job_card: JobCard,
) -> None:
    """Cancel a job while preserving the record."""

    client.force_login(receptionist)

    response = client.post(
        reverse(
            "jobs:cancel",
            args=(job_card.pk,),
        ),
        {
            "reason": "Customer postponed the repair.",
        },
    )

    job_card.refresh_from_db()

    assert response.status_code == 302
    assert job_card.status == JobStatus.CANCELLED
    assert job_card.cancellation_reason == ("Customer postponed the repair.")
