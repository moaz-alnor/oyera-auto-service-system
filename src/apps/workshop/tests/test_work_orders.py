"""Tests for creating workshop work orders."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)

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
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import Product
from apps.product_catalogue.services.catalogue import (
    CreateProductCategoryCommand,
    CreateProductCommand,
    create_product,
    create_product_category,
)
from apps.quotations.constants import (
    CustomerDecisionMethod,
    QuotationStatus,
)
from apps.quotations.models import Quotation
from apps.quotations.services.quotations import (
    AddProductLineCommand,
    AddServiceLineCommand,
    CreateQuotationCommand,
    RecordCustomerDecisionCommand,
    add_product_line,
    add_service_line,
    approve_quotation,
    create_quotation,
    submit_quotation,
)
from apps.service_catalogue.models import Service
from apps.service_catalogue.services.catalogue import (
    CreateServiceCommand,
    create_service,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle
from apps.workshop.constants import (
    ProductRequirementStatus,
    WorkOrderStatus,
    WorkTaskStatus,
)
from apps.workshop.models import WorkOrder
from apps.workshop.services.work_orders import (
    CreateWorkOrderCommand,
    create_work_order,
)


@dataclass(frozen=True, slots=True)
class WorkOrderTestContext:
    """Contain records shared by work-order tests."""

    manager: User
    technician: User
    job_card: JobCard
    service: Service
    product: Product


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create an employee assigned to one role."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def work_order_context() -> WorkOrderTestContext:
    """Create a job and workshop catalogue records."""

    manager = _create_employee(
        username="workshop.manager",
        role=RoleName.MANAGER,
    )
    technician = _create_employee(
        username="workshop.technician",
        role=RoleName.TECHNICIAN,
    )

    customer = Customer(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="0700123456",
        created_by=manager,
        updated_by=manager,
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
            code="BRAKE-SERVICE",
            name="Brake Inspection and Service",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("100000.00"),
        ),
    )

    category = create_product_category(
        actor=manager,
        command=CreateProductCategoryCommand(
            code="BRAKES",
            name="Brake Parts",
        ),
    )

    product = create_product(
        actor=manager,
        command=CreateProductCommand(
            category_id=category.pk,
            sku="BRAKE-PAD-001",
            name="Front Brake Pad Set",
            unit=ProductUnit.SET,
            initial_price=Decimal("50000.00"),
        ),
    )

    return WorkOrderTestContext(
        manager=manager,
        technician=technician,
        job_card=job_card,
        service=service,
        product=product,
    )


def _create_quotation(
    *,
    context: WorkOrderTestContext,
    approve: bool,
) -> Quotation:
    """Create a populated draft or approved quotation."""

    quotation = create_quotation(
        actor=context.manager,
        job_card_id=context.job_card.pk,
        command=CreateQuotationCommand(),
    )

    add_service_line(
        actor=context.manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=context.service.pk,
            quantity=Decimal("1.00"),
        ),
    )
    add_product_line(
        actor=context.manager,
        quotation_id=quotation.pk,
        command=AddProductLineCommand(
            product_id=context.product.pk,
            quantity=Decimal("2.000"),
        ),
    )

    if not approve:
        return quotation

    quotation = submit_quotation(
        actor=context.manager,
        quotation_id=quotation.pk,
    )

    return approve_quotation(
        actor=context.manager,
        quotation_id=quotation.pk,
        command=RecordCustomerDecisionCommand(
            customer_name="Daniel Kato",
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Customer approved the repair work.",
        ),
    )


@pytest.mark.django_db
def test_manager_creates_work_order_from_approved_quotation(
    work_order_context: WorkOrderTestContext,
) -> None:
    """Copy approved service and product snapshots."""

    quotation = _create_quotation(
        context=work_order_context,
        approve=True,
    )

    work_order = create_work_order(
        actor=work_order_context.manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    task = work_order.tasks.get()
    requirement = work_order.product_requirements.get()

    assert work_order.work_order_number.startswith("WO-")
    assert work_order.status == WorkOrderStatus.PLANNED
    assert work_order.job_card == work_order_context.job_card
    assert work_order.approved_quotation == quotation

    assert task.status == WorkTaskStatus.PENDING
    assert task.service_code_snapshot == "BRAKE-SERVICE"
    assert task.service_name_snapshot == "Brake Inspection and Service"
    assert task.approved_quantity == Decimal("1.00")
    assert task.approved_unit_price == Decimal("100000.00")

    assert requirement.product_sku_snapshot == "BRAKE-PAD-001"
    assert requirement.product_name_snapshot == "Front Brake Pad Set"
    assert requirement.approved_quantity == Decimal("2.000")
    assert requirement.approved_unit_price == Decimal("50000.00")
    assert requirement.inventory_status == ProductRequirementStatus.NOT_RESERVED

    quotation.refresh_from_db()
    assert quotation.status == QuotationStatus.APPROVED


@pytest.mark.django_db
def test_work_order_requires_approved_quotation(
    work_order_context: WorkOrderTestContext,
) -> None:
    """Reject workshop creation from a draft quotation."""

    quotation = _create_quotation(
        context=work_order_context,
        approve=False,
    )

    with pytest.raises(
        ValidationError,
        match="Only an approved quotation",
    ):
        create_work_order(
            actor=work_order_context.manager,
            command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
        )

    assert not WorkOrder.objects.exists()


@pytest.mark.django_db
def test_job_can_have_only_one_work_order(
    work_order_context: WorkOrderTestContext,
) -> None:
    """Prevent duplicate workshop execution records."""

    quotation = _create_quotation(
        context=work_order_context,
        approve=True,
    )

    create_work_order(
        actor=work_order_context.manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    with pytest.raises(
        ValidationError,
        match="already has a workshop work order",
    ):
        create_work_order(
            actor=work_order_context.manager,
            command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
        )

    assert WorkOrder.objects.count() == 1


@pytest.mark.django_db
def test_technician_cannot_create_work_order(
    work_order_context: WorkOrderTestContext,
) -> None:
    """Prevent technicians from opening workshop execution."""

    quotation = _create_quotation(
        context=work_order_context,
        approve=True,
    )

    with pytest.raises(PermissionDenied):
        create_work_order(
            actor=work_order_context.technician,
            command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
        )

    assert not WorkOrder.objects.exists()
