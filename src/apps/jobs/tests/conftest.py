"""Shared fixtures for vehicle-release tests."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import (
    ensure_default_roles,
)
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
class ReleaseTestContext:
    """Contain records used by release-service tests."""

    manager: User
    receptionist: User
    technician: User
    cashier: User
    job_card: JobCard
    work_order: WorkOrder


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create one employee assigned to a role."""

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def release_context() -> ReleaseTestContext:
    """Create one approved workshop workflow."""

    ensure_default_roles()

    manager = _create_employee(
        username="release.manager",
        role=RoleName.MANAGER,
    )
    receptionist = _create_employee(
        username="release.receptionist",
        role=RoleName.RECEPTIONIST,
    )
    technician = _create_employee(
        username="release.technician",
        role=RoleName.TECHNICIAN,
    )
    cashier = _create_employee(
        username="release.cashier",
        role=RoleName.CASHIER,
    )

    customer = Customer(
        customer_number="CUS-RELEASE-001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Release Test Customer",
        phone_number="0700111222",
        email="release.customer@example.com",
        created_by=manager,
        updated_by=manager,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-RELEASE-001",
        registration_number="UBR 101R",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        year=2022,
        color="Silver",
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
            customer_complaint=("Routine vehicle-release test service."),
        ),
    )

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="RELEASE-SERVICE",
            name="Release Test Service",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("80000.00"),
        ),
    )

    quotation = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(
            currency="UGX",
            discount_percentage=Decimal("0.00"),
            tax_percentage=Decimal("0.00"),
        ),
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
            customer_name="Release Test Customer",
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Approved for release testing.",
        ),
    )

    work_order = create_work_order(
        actor=manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    return ReleaseTestContext(
        manager=manager,
        receptionist=receptionist,
        technician=technician,
        cashier=cashier,
        job_card=job_card,
        work_order=work_order,
    )
