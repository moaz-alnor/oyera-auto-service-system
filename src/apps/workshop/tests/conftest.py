"""Shared fixtures for workshop execution tests."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.jobs.models import JobCard
from apps.jobs.services.intake import (
    OpenJobCardCommand,
    open_job_card,
)
from apps.quotations.constants import (
    CustomerDecisionMethod,
)
from apps.quotations.services.quotations import (
    AddServiceLineCommand,
    CreateQuotationCommand,
    RecordCustomerDecisionCommand,
    add_service_line,
    approve_quotation,
    create_quotation,
    submit_quotation,
)
from apps.service_catalogue.services.catalogue import (
    CreateServiceCommand,
    create_service,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle
from apps.workshop.models import WorkOrder
from apps.workshop.services.work_orders import (
    CreateWorkOrderCommand,
    create_work_order,
)


@dataclass(frozen=True, slots=True)
class WorkshopExecutionContext:
    """Contain records shared by workshop execution tests."""

    manager: User
    technician: User
    second_technician: User
    receptionist: User
    job_card: JobCard
    work_order: WorkOrder


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create an employee assigned to one application role."""

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def workshop_execution_context() -> WorkshopExecutionContext:
    """Create an approved quotation and planned work order."""

    ensure_default_roles()

    manager = _create_employee(
        username="assignment.manager",
        role=RoleName.MANAGER,
    )
    technician = _create_employee(
        username="assignment.technician",
        role=RoleName.TECHNICIAN,
    )
    second_technician = _create_employee(
        username="assignment.technician.two",
        role=RoleName.TECHNICIAN,
    )
    receptionist = _create_employee(
        username="assignment.receptionist",
        role=RoleName.RECEPTIONIST,
    )

    customer = Customer(
        customer_number="CUS-900001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        created_by=manager,
        updated_by=manager,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-900001",
        registration_number="UBD 945X",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        current_mileage=45000,
        created_by=manager,
        updated_by=manager,
    )
    vehicle.full_clean()
    vehicle.save()

    job_card = open_job_card(
        actor=manager,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Brake vibration.",
        ),
    )

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="WORKSHOP-BRAKE",
            name="Workshop Brake Service",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("100000.00"),
        ),
    )

    quotation = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(),
    )

    add_service_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=service.pk,
            quantity=Decimal("1.00"),
        ),
    )

    quotation = submit_quotation(
        actor=manager,
        quotation_id=quotation.pk,
    )

    quotation = approve_quotation(
        actor=manager,
        quotation_id=quotation.pk,
        command=RecordCustomerDecisionCommand(
            customer_name="Daniel Kato",
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Customer approved workshop execution.",
        ),
    )

    work_order = create_work_order(
        actor=manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    return WorkshopExecutionContext(
        manager=manager,
        technician=technician,
        second_technician=second_technician,
        receptionist=receptionist,
        job_card=job_card,
        work_order=work_order,
    )
