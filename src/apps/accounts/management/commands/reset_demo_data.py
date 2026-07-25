"""Reset the local database and create coherent demonstration data."""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)
from django.db import transaction

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.customers.services.customers import (
    RegisterCustomerCommand,
    register_customer,
)
from apps.inventory.services.issues import (
    IssueStockCommand,
    issue_reserved_stock,
)
from apps.inventory.services.master_data import (
    CreateInventoryItemCommand,
    CreateStockLocationCommand,
    create_inventory_item,
    create_stock_location,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.services.reservations import (
    ReserveStockCommand,
    reserve_stock,
)
from apps.jobs.constants import (
    FuelLevel,
    JobPriority,
)
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
from apps.quotations.constants import CustomerDecisionMethod
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
from apps.vehicles.constants import (
    FuelType,
    VehicleCategory,
)
from apps.vehicles.services.vehicles import (
    RegisterVehicleCommand,
    register_vehicle,
)
from apps.workshop.models import (
    WorkOrder,
)
from apps.workshop.services.assignments import (
    AssignTechnicianCommand,
    assign_technician,
)
from apps.workshop.services.work_orders import (
    CreateWorkOrderCommand,
    create_work_order,
)


def _require_pk(
    value: int | None,
    *,
    label: str,
) -> int:
    """Return a saved integer primary key."""

    if value is None:
        raise RuntimeError(f"{label} was created without a primary key.")

    return value


def _create_employee(
    *,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    role: RoleName,
    email: str,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> User:
    """Create one employee and attach the requested role."""

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number="+256700000000",
        is_active=True,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )

    group = Group.objects.get(name=role.value)
    user.groups.add(group)

    return user


def _create_approved_work_order(
    *,
    actor: User,
    customer: Customer,
    service: Service,
    product: Product,
    registration_number: str,
    mileage: int,
    complaint: str,
    product_quantity: Decimal,
) -> WorkOrder:
    """Create a complete approved commercial workflow."""

    vehicle = register_vehicle(
        actor=actor,
        command=RegisterVehicleCommand(
            owner_id=_require_pk(
                customer.pk,
                label="Customer",
            ),
            registration_number=registration_number,
            category=VehicleCategory.SMALL,
            make="Toyota",
            model="Corolla",
            year=2022,
            color="Silver",
            current_mileage=mileage,
            fuel_type=FuelType.PETROL,
            notes="Generated demonstration vehicle.",
        ),
    )

    job_card = open_job_card(
        actor=actor,
        command=OpenJobCardCommand(
            customer_id=_require_pk(
                customer.pk,
                label="Customer",
            ),
            vehicle_id=_require_pk(
                vehicle.pk,
                label="Vehicle",
            ),
            arrival_mileage=mileage,
            customer_complaint=complaint,
            visible_condition=("Vehicle received in normal external condition."),
            fuel_level=FuelLevel.HALF,
            priority=JobPriority.NORMAL,
        ),
    )

    quotation = create_quotation(
        actor=actor,
        job_card_id=_require_pk(
            job_card.pk,
            label="Job card",
        ),
        command=CreateQuotationCommand(
            currency="UGX",
            discount_percentage=Decimal("0.00"),
            tax_percentage=Decimal("0.00"),
            valid_until=(date.today() + timedelta(days=14)),
            notes="Generated demonstration quotation.",
        ),
    )

    add_service_line(
        actor=actor,
        quotation_id=_require_pk(
            quotation.pk,
            label="Quotation",
        ),
        command=AddServiceLineCommand(
            service_id=_require_pk(
                service.pk,
                label="Service",
            ),
            quantity=Decimal("1.00"),
        ),
    )

    add_product_line(
        actor=actor,
        quotation_id=_require_pk(
            quotation.pk,
            label="Quotation",
        ),
        command=AddProductLineCommand(
            product_id=_require_pk(
                product.pk,
                label="Product",
            ),
            quantity=product_quantity,
        ),
    )

    submit_quotation(
        actor=actor,
        quotation_id=_require_pk(
            quotation.pk,
            label="Quotation",
        ),
    )

    approve_quotation(
        actor=actor,
        quotation_id=_require_pk(
            quotation.pk,
            label="Quotation",
        ),
        command=RecordCustomerDecisionCommand(
            customer_name=customer.name,
            method=CustomerDecisionMethod.IN_PERSON,
            notes="Approved for demonstration testing.",
        ),
    )

    return create_work_order(
        actor=actor,
        command=CreateWorkOrderCommand(
            approved_quotation_id=_require_pk(
                quotation.pk,
                label="Quotation",
            )
        ),
    )


def _make_work_order_ready(
    *,
    actor: User,
    technician: User,
    work_order: WorkOrder,
) -> None:
    """Assign the technician and move the order to READY."""

    task = work_order.tasks.get()

    assign_technician(
        actor=actor,
        command=AssignTechnicianCommand(
            work_task_id=_require_pk(
                task.pk,
                label="Work task",
            ),
            technician_id=_require_pk(
                technician.pk,
                label="Technician",
            ),
        ),
    )

    work_order.refresh_from_db()


class Command(BaseCommand):
    """Reset local records and create reusable test scenarios."""

    help = "Delete local database records and create coherent Oyera demonstration data."

    def add_arguments(
        self,
        parser: CommandParser,
    ) -> None:
        """Register destructive-operation confirmation."""

        parser.add_argument(
            "--yes",
            action="store_true",
            help=("Confirm deletion of all records in the configured local database."),
        )

    def handle(
        self,
        *args: object,
        **options: object,
    ) -> None:
        """Flush local records and construct demo workflows."""

        if not settings.DEBUG:
            raise CommandError("reset_demo_data is restricted to DEBUG mode.")

        if not bool(options["yes"]):
            raise CommandError(
                "This deletes all local database records. "
                "Run again with --yes to confirm."
            )

        self.stdout.write(self.style.WARNING("Deleting all local database records..."))

        call_command(
            "flush",
            interactive=False,
            verbosity=0,
        )

        ensure_default_roles()

        with transaction.atomic():
            admin = _create_employee(
                username="admin",
                password="AdminDemo123!",
                first_name="Demo",
                last_name="Administrator",
                role=RoleName.ADMINISTRATOR,
                email="admin@example.com",
                is_staff=True,
                is_superuser=True,
            )

            _create_employee(
                username="manager",
                password="ManagerDemo123!",
                first_name="Demo",
                last_name="Manager",
                role=RoleName.MANAGER,
                email="manager@example.com",
            )

            technician = _create_employee(
                username="technician",
                password="TechnicianDemo123!",
                first_name="Demo",
                last_name="Technician",
                role=RoleName.TECHNICIAN,
                email="technician@example.com",
            )

            _create_employee(
                username="receptionist",
                password="ReceptionDemo123!",
                first_name="Demo",
                last_name="Receptionist",
                role=RoleName.RECEPTIONIST,
                email="receptionist@example.com",
            )

            category = create_product_category(
                actor=admin,
                command=CreateProductCategoryCommand(
                    code="FILTERS",
                    name="Filters",
                    description=("Filters used during vehicle servicing."),
                ),
            )

            product = create_product(
                actor=admin,
                command=CreateProductCommand(
                    category_id=_require_pk(
                        category.pk,
                        label="Product category",
                    ),
                    sku="OIL-FILTER-001",
                    name="Engine oil filter",
                    unit=ProductUnit.EACH,
                    initial_price=Decimal("35000.00"),
                    manufacturer="Demo Parts",
                    manufacturer_part_number="OF-001",
                    description=(
                        "Standard engine oil filter for demonstration workflows."
                    ),
                    currency="UGX",
                    price_notes="Initial demonstration price.",
                ),
            )

            service = create_service(
                actor=admin,
                command=CreateServiceCommand(
                    code="OIL-CHANGE",
                    name="Engine oil and filter change",
                    applicable_categories=(VehicleCategory.SMALL,),
                    initial_price=Decimal("80000.00"),
                    description=("Drain engine oil and replace the engine oil filter."),
                    estimated_duration_minutes=45,
                    currency="UGX",
                    price_notes="Initial demonstration price.",
                ),
            )

            location = create_stock_location(
                actor=admin,
                command=CreateStockLocationCommand(
                    code="MAIN-STORE",
                    name="Main Parts Store",
                    description=("Primary storage location for demonstration stock."),
                ),
            )

            inventory_item = create_inventory_item(
                actor=admin,
                command=CreateInventoryItemCommand(
                    product_id=_require_pk(
                        product.pk,
                        label="Product",
                    ),
                    location_id=_require_pk(
                        location.pk,
                        label="Stock location",
                    ),
                    reorder_level=Decimal("5.000"),
                    notes="Reusable demonstration inventory.",
                ),
            )

            receive_stock(
                actor=admin,
                command=ReceiveStockCommand(
                    inventory_item_id=_require_pk(
                        inventory_item.pk,
                        label="Inventory item",
                    ),
                    quantity=Decimal("25.000"),
                    unit_cost=Decimal("22000.00"),
                    currency="UGX",
                    external_reference="DEMO-OPENING-STOCK",
                    notes="Opening stock generated by reset command.",
                ),
            )

            customer = register_customer(
                actor=admin,
                command=RegisterCustomerCommand(
                    customer_type=CustomerType.INDIVIDUAL,
                    name="Demo Workshop Customer",
                    phone_number="+256700123456",
                    email="customer@example.com",
                    address="Kampala, Uganda",
                    notes="Reusable demonstration customer.",
                ),
            )

            # Scenario 1:
            # PLANNED and NOT_RESERVED.
            # Use this to test the Reserve Stock button.
            reserve_order = _create_approved_work_order(
                actor=admin,
                customer=customer,
                service=service,
                product=product,
                registration_number="UAT 101A",
                mileage=10100,
                complaint=("Reserve scenario: oil service requested."),
                product_quantity=Decimal("1.000"),
            )

            reserve_requirement = reserve_order.product_requirements.get()

            # Scenario 2:
            # READY with an ACTIVE reservation.
            # Use this to test Issue or Release.
            issue_order = _create_approved_work_order(
                actor=admin,
                customer=customer,
                service=service,
                product=product,
                registration_number="UAT 202B",
                mileage=20200,
                complaint=("Issue scenario: oil service requested."),
                product_quantity=Decimal("2.000"),
            )

            _make_work_order_ready(
                actor=admin,
                technician=technician,
                work_order=issue_order,
            )

            issue_requirement = issue_order.product_requirements.get()

            issue_reservation = reserve_stock(
                actor=admin,
                command=ReserveStockCommand(
                    inventory_item_id=_require_pk(
                        inventory_item.pk,
                        label="Inventory item",
                    ),
                    work_product_requirement_id=_require_pk(
                        issue_requirement.pk,
                        label="Product requirement",
                    ),
                    quantity=Decimal("2.000"),
                ),
            )

            # Scenario 3:
            # READY with a partial issue already recorded.
            # Use this to test Return Stock.
            return_order = _create_approved_work_order(
                actor=admin,
                customer=customer,
                service=service,
                product=product,
                registration_number="UAT 303C",
                mileage=30300,
                complaint=("Return scenario: oil service requested."),
                product_quantity=Decimal("3.000"),
            )

            _make_work_order_ready(
                actor=admin,
                technician=technician,
                work_order=return_order,
            )

            return_requirement = return_order.product_requirements.get()

            return_reservation = reserve_stock(
                actor=admin,
                command=ReserveStockCommand(
                    inventory_item_id=_require_pk(
                        inventory_item.pk,
                        label="Inventory item",
                    ),
                    work_product_requirement_id=_require_pk(
                        return_requirement.pk,
                        label="Product requirement",
                    ),
                    quantity=Decimal("3.000"),
                ),
            )

            issue_movement = issue_reserved_stock(
                actor=admin,
                command=IssueStockCommand(
                    reservation_id=_require_pk(
                        return_reservation.pk,
                        label="Reservation",
                    ),
                    quantity=Decimal("1.500"),
                    notes=("Demo issue generated for return testing."),
                ),
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Local demonstration database created."))

        self.stdout.write("")
        self.stdout.write("Login accounts:")
        self.stdout.write("  admin / AdminDemo123! — Django administrator")
        self.stdout.write("  manager / ManagerDemo123! — operational manager")
        self.stdout.write("  technician / TechnicianDemo123! — technician")
        self.stdout.write("  receptionist / ReceptionDemo123! — receptionist")

        self.stdout.write("")
        self.stdout.write("Testing scenarios:")

        self.stdout.write(
            "  Ready to reserve:"
            f" /inventory/requirements/"
            f"{_require_pk(reserve_requirement.pk, label='Requirement')}"
            "/reserve/"
        )

        self.stdout.write(
            "  Ready to issue or release:"
            f" /inventory/reservations/"
            f"{_require_pk(issue_reservation.pk, label='Reservation')}"
            "/issue/"
        )

        self.stdout.write(
            "  Ready to return:"
            f" /inventory/movements/"
            f"{_require_pk(issue_movement.pk, label='Movement')}"
            "/return/"
        )

        self.stdout.write(
            "  Inventory detail:"
            f" /inventory/"
            f"{_require_pk(inventory_item.pk, label='Inventory item')}/"
        )

        self.stdout.write("")
        self.stdout.write(f"Administrator created: {admin.username}")
