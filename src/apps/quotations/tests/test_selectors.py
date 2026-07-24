"""Tests for quotation read queries."""

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
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import Product
from apps.product_catalogue.services.catalogue import (
    CreateProductCategoryCommand,
    CreateProductCommand,
    create_product,
    create_product_category,
)
from apps.quotations.constants import QuotationStatus
from apps.quotations.selectors import (
    get_jobs_available_for_quotation,
    get_products_available_for_quotation,
    get_quotation_by_id,
    get_services_available_for_quotation,
    search_quotations,
)
from apps.quotations.services.quotations import (
    AddProductLineCommand,
    AddServiceLineCommand,
    CreateQuotationCommand,
    add_product_line,
    add_service_line,
    create_quotation,
)
from apps.service_catalogue.models import Service
from apps.service_catalogue.services.catalogue import (
    CreateServiceCommand,
    create_service,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


@dataclass(frozen=True, slots=True)
class QuotationTestContext:
    """Contain records shared by quotation tests."""

    manager: User
    job_card: JobCard
    service: Service
    product: Product


def _create_manager() -> User:
    """Create a manager with the configured role policy."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="selector.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    return manager


def _create_job(
    *,
    manager: User,
    index: int,
    customer_name: str,
) -> JobCard:
    """Create one active customer, vehicle, and job card."""

    customer = Customer(
        customer_number=f"CUS-{index:06d}",
        customer_type=CustomerType.INDIVIDUAL,
        name=customer_name,
        phone_number=f"070000{index:04d}",
        created_by=manager,
        updated_by=manager,
    )
    customer.full_clean()
    customer.save()

    vehicle = Vehicle(
        vehicle_number=f"VEH-{index:06d}",
        registration_number=f"UBD {240 + index}X",
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

    return open_job_card(
        actor=manager,
        command=OpenJobCardCommand(
            customer_id=customer.pk,
            vehicle_id=vehicle.pk,
            arrival_mileage=45000,
            customer_complaint="Brake vibration.",
        ),
    )


@pytest.fixture
def quotation_context() -> QuotationTestContext:
    """Create catalogue records and an active workshop job."""

    manager = _create_manager()
    job_card = _create_job(
        manager=manager,
        index=1,
        customer_name="Daniel Kato",
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

    return QuotationTestContext(
        manager=manager,
        job_card=job_card,
        service=service,
        product=product,
    )


@pytest.mark.django_db
def test_quotation_search_matches_customer_and_vehicle(
    quotation_context: QuotationTestContext,
) -> None:
    """Search quotation records using job snapshots."""

    quotation = create_quotation(
        actor=quotation_context.manager,
        job_card_id=quotation_context.job_card.pk,
        command=CreateQuotationCommand(),
    )

    customer_results = search_quotations(query="Daniel Kato")
    vehicle_results = search_quotations(query="UBD 241X")

    assert list(customer_results) == [quotation]
    assert list(vehicle_results) == [quotation]


@pytest.mark.django_db
def test_quotation_search_filters_status_and_current_revision(
    quotation_context: QuotationTestContext,
) -> None:
    """Filter quotation results by status and current flag."""

    quotation = create_quotation(
        actor=quotation_context.manager,
        job_card_id=quotation_context.job_card.pk,
        command=CreateQuotationCommand(),
    )

    draft_results = search_quotations(
        status=QuotationStatus.DRAFT,
        current_only=True,
    )
    approved_results = search_quotations(
        status=QuotationStatus.APPROVED,
        current_only=True,
    )

    assert list(draft_results) == [quotation]
    assert not approved_results.exists()


@pytest.mark.django_db
def test_quotation_detail_selector_returns_snapshot_lines(
    quotation_context: QuotationTestContext,
) -> None:
    """Load service and product lines for quotation display."""

    quotation = create_quotation(
        actor=quotation_context.manager,
        job_card_id=quotation_context.job_card.pk,
        command=CreateQuotationCommand(),
    )

    add_service_line(
        actor=quotation_context.manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=quotation_context.service.pk,
        ),
    )
    add_product_line(
        actor=quotation_context.manager,
        quotation_id=quotation.pk,
        command=AddProductLineCommand(
            product_id=quotation_context.product.pk,
        ),
    )

    selected = get_quotation_by_id(quotation_id=quotation.pk)

    service_line = selected.service_lines.first()
    product_line = selected.product_lines.first()

    assert service_line is not None
    assert product_line is not None

    assert service_line.service_name_snapshot == "Brake Inspection and Service"
    assert product_line.product_name_snapshot == "Front Brake Pad Set"


@pytest.mark.django_db
def test_available_quotation_choices_follow_business_rules(
    quotation_context: QuotationTestContext,
) -> None:
    """Return eligible jobs, services, and products."""

    available_job = _create_job(
        manager=quotation_context.manager,
        index=2,
        customer_name="Sarah Auma",
    )

    quotation = create_quotation(
        actor=quotation_context.manager,
        job_card_id=quotation_context.job_card.pk,
        command=CreateQuotationCommand(),
    )

    jobs = get_jobs_available_for_quotation()
    services = get_services_available_for_quotation(quotation=quotation)
    products = get_products_available_for_quotation(quotation=quotation)

    assert available_job in jobs
    assert quotation_context.job_card not in jobs
    assert quotation_context.service in services
    assert quotation_context.product in products
