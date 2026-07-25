"""Shared fixtures for billing-domain tests."""

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
class BillingTestContext:
    """Contain records shared by billing tests."""

    manager: User
    cashier: User
    job_card: JobCard
    work_order: WorkOrder


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create an employee assigned to one role."""

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def billing_context() -> BillingTestContext:
    """Create an approved workshop workflow for billing."""

    ensure_default_roles()

    manager = _create_employee(
        username="billing.manager",
        role=RoleName.MANAGER,
    )
    cashier = _create_employee(
        username="billing.cashier",
        role=RoleName.CASHIER,
    )

    customer = Customer(
        customer_number="CUS-BILL-001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Billing Test Customer",
        phone_number="0700111222",
        email="billing.customer@example.com",
        created_by=manager,
        updated_by=manager,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-BILL-001",
        registration_number="UBB 101B",
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
            customer_complaint=("Routine engine oil service required."),
        ),
    )

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="BILL-OIL-SERVICE",
            name="Billing Engine Oil Service",
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
            customer_name="Billing Test Customer",
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Approved for billing tests.",
        ),
    )

    work_order = create_work_order(
        actor=manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    return BillingTestContext(
        manager=manager,
        cashier=cashier,
        job_card=job_card,
        work_order=work_order,
    )
