"""Shared fixtures for inventory-domain tests."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
)
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
)
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
from apps.service_catalogue.services.catalogue import (
    CreateServiceCommand,
    create_service,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle
from apps.workshop.models import (
    WorkOrder,
    WorkProductRequirement,
)
from apps.workshop.services.work_orders import (
    CreateWorkOrderCommand,
    create_work_order,
)


@dataclass(frozen=True, slots=True)
class InventoryTestContext:
    """Contain records shared by inventory tests."""

    manager: User
    technician: User
    product: Product
    location: StockLocation
    inventory_item: InventoryItem


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
def inventory_context() -> InventoryTestContext:
    """Create an inventory item and authorised employees."""

    ensure_default_roles()

    manager = _create_employee(
        username="inventory.manager",
        role=RoleName.MANAGER,
    )
    technician = _create_employee(
        username="inventory.technician",
        role=RoleName.TECHNICIAN,
    )

    category = create_product_category(
        actor=manager,
        command=CreateProductCategoryCommand(
            code="FILTERS",
            name="Filters",
        ),
    )

    product = create_product(
        actor=manager,
        command=CreateProductCommand(
            category_id=category.pk,
            sku="OIL-FILTER-001",
            name="Engine Oil Filter",
            unit=ProductUnit.EACH,
            initial_price=Decimal("25000.00"),
        ),
    )

    location = StockLocation(
        code="MAIN-STORE",
        name="Main Parts Store",
        description="Primary workshop stock location.",
        created_by=manager,
        updated_by=manager,
    )
    location.full_clean()
    location.save()

    inventory_item = InventoryItem(
        product=product,
        location=location,
        reorder_level=Decimal("5.000"),
        created_by=manager,
        updated_by=manager,
    )
    inventory_item.full_clean()
    inventory_item.save()

    return InventoryTestContext(
        manager=manager,
        technician=technician,
        product=product,
        location=location,
        inventory_item=inventory_item,
    )


@dataclass(frozen=True, slots=True)
class InventoryReservationContext:
    """Contain inventory and workshop reservation records."""

    inventory: InventoryTestContext
    job_card: JobCard
    work_order: WorkOrder
    requirement: WorkProductRequirement


@pytest.fixture
def inventory_reservation_context(
    inventory_context: InventoryTestContext,
) -> InventoryReservationContext:
    """Create workshop product demand for the inventory item."""

    manager = inventory_context.manager

    customer = Customer(
        customer_number="CUS-INV-001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Inventory Test Customer",
        phone_number="0700999000",
        created_by=manager,
        updated_by=manager,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number="VEH-INV-001",
        registration_number="UBI 101A",
        current_owner=customer,
        category=VehicleCategory.SMALL,
        make="Toyota",
        model="Corolla",
        current_mileage=50000,
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
            arrival_mileage=50000,
            customer_complaint="Engine oil service required.",
        ),
    )

    service = create_service(
        actor=manager,
        command=CreateServiceCommand(
            code="INV-OIL-SERVICE",
            name="Engine Oil Service",
            applicable_categories=(VehicleCategory.SMALL,),
            initial_price=Decimal("80000.00"),
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

    add_product_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddProductLineCommand(
            product_id=inventory_context.product.pk,
            quantity=Decimal("2.000"),
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
            customer_name="Inventory Test Customer",
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Customer approved the service.",
        ),
    )

    work_order = create_work_order(
        actor=manager,
        command=CreateWorkOrderCommand(approved_quotation_id=quotation.pk),
    )

    requirement = work_order.product_requirements.get()

    return InventoryReservationContext(
        inventory=inventory_context,
        job_card=job_card,
        work_order=work_order,
        requirement=requirement,
    )
