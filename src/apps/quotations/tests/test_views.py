"""Tests for quotation HTTP workflows."""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

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
from apps.quotations.models import (
    Quotation,
    QuotationProductLine,
    QuotationServiceLine,
)
from apps.quotations.services.quotations import (
    AddServiceLineCommand,
    CreateQuotationCommand,
    add_service_line,
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


@dataclass(frozen=True, slots=True)
class QuotationViewContext:
    """Contain records used by quotation view tests."""

    manager: User
    job_card: JobCard
    service: Service
    product: Product


def _create_employee(
    *,
    username: str,
    role: RoleName,
) -> User:
    """Create an employee assigned to one application role."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=role.value))

    return employee


@pytest.fixture
def quotation_view_context() -> QuotationViewContext:
    """Create an active job and quotation catalogue records."""

    manager = _create_employee(
        username="quotation.view.manager",
        role=RoleName.MANAGER,
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

    return QuotationViewContext(
        manager=manager,
        job_card=job_card,
        service=service,
        product=product,
    )


def _create_draft_quotation(
    context: QuotationViewContext,
) -> Quotation:
    """Create one current draft quotation."""

    return create_quotation(
        actor=context.manager,
        job_card_id=context.job_card.pk,
        command=CreateQuotationCommand(),
    )


def _create_submitted_quotation(
    context: QuotationViewContext,
) -> Quotation:
    """Create a submitted quotation with one service line."""

    quotation = _create_draft_quotation(context)

    add_service_line(
        actor=context.manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=context.service.pk,
        ),
    )

    return submit_quotation(
        actor=context.manager,
        quotation_id=quotation.pk,
    )


@pytest.mark.django_db
def test_manager_can_view_quotation_list(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Display quotation records to authorized managers."""

    quotation = _create_draft_quotation(quotation_view_context)
    client.force_login(quotation_view_context.manager)

    response = client.get(reverse("quotations:list"))

    assert response.status_code == 200
    assert quotation.quotation_number.encode() in response.content


@pytest.mark.django_db
def test_technician_has_read_only_quotation_access(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Allow technicians to view but not create quotations."""

    quotation = _create_draft_quotation(quotation_view_context)
    technician = _create_employee(
        username="quotation.technician",
        role=RoleName.TECHNICIAN,
    )
    client.force_login(technician)

    list_response = client.get(reverse("quotations:list"))
    detail_response = client.get(
        reverse(
            "quotations:detail",
            args=(quotation.pk,),
        )
    )
    create_response = client.get(reverse("quotations:create"))

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert create_response.status_code == 403


@pytest.mark.django_db
def test_manager_can_create_quotation(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Create the first quotation through the web form."""

    client.force_login(quotation_view_context.manager)

    response = client.post(
        reverse("quotations:create"),
        {
            "job_card": quotation_view_context.job_card.pk,
            "currency": "UGX",
            "discount_percentage": "10.00",
            "tax_percentage": "18.00",
            "valid_until": "",
            "notes": "Initial customer estimate.",
        },
    )

    quotation = Quotation.objects.get(job_card=quotation_view_context.job_card)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "quotations:detail",
        args=(quotation.pk,),
    )
    assert quotation.discount_percentage == Decimal("10.00")
    assert quotation.tax_percentage == Decimal("18.00")


@pytest.mark.django_db
def test_manager_can_add_service_and_product_lines(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Add catalogue snapshots through quotation forms."""

    quotation = _create_draft_quotation(quotation_view_context)
    client.force_login(quotation_view_context.manager)

    service_response = client.post(
        reverse(
            "quotations:service_line_create",
            args=(quotation.pk,),
        ),
        {
            "service": quotation_view_context.service.pk,
            "quantity": "1.00",
            "description_override": "",
        },
    )
    product_response = client.post(
        reverse(
            "quotations:product_line_create",
            args=(quotation.pk,),
        ),
        {
            "product": quotation_view_context.product.pk,
            "quantity": "2.000",
            "description_override": "",
        },
    )

    assert service_response.status_code == 302
    assert product_response.status_code == 302

    assert QuotationServiceLine.objects.filter(quotation=quotation).count() == 1
    assert QuotationProductLine.objects.filter(quotation=quotation).count() == 1


@pytest.mark.django_db
def test_manager_can_submit_quotation(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Submit a populated draft quotation from its detail page."""

    quotation = _create_draft_quotation(quotation_view_context)
    add_service_line(
        actor=quotation_view_context.manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=quotation_view_context.service.pk,
        ),
    )
    client.force_login(quotation_view_context.manager)

    response = client.post(
        reverse(
            "quotations:submit",
            args=(quotation.pk,),
        )
    )

    quotation.refresh_from_db()

    assert response.status_code == 302
    assert quotation.status == QuotationStatus.SENT
    assert quotation.submitted_at is not None


@pytest.mark.django_db
def test_manager_can_record_customer_approval(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Record customer approval through the decision form."""

    quotation = _create_submitted_quotation(quotation_view_context)
    client.force_login(quotation_view_context.manager)

    response = client.post(
        reverse(
            "quotations:approve",
            args=(quotation.pk,),
        ),
        {
            "customer_name": "Daniel Kato",
            "method": CustomerDecisionMethod.IN_PERSON,
            "notes": "Approved at reception.",
        },
    )

    quotation.refresh_from_db()

    assert response.status_code == 302
    assert quotation.status == QuotationStatus.APPROVED
    assert quotation.customer_decision_by_name == "Daniel Kato"
    assert quotation.decision_recorded_by == quotation_view_context.manager


@pytest.mark.django_db
def test_rejection_requires_reason_and_allows_revision(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Validate rejection evidence and create a new revision."""

    quotation = _create_submitted_quotation(quotation_view_context)
    client.force_login(quotation_view_context.manager)

    invalid_response = client.post(
        reverse(
            "quotations:reject",
            args=(quotation.pk,),
        ),
        {
            "customer_name": "Daniel Kato",
            "method": CustomerDecisionMethod.PHONE,
            "notes": "",
        },
    )

    quotation.refresh_from_db()

    assert invalid_response.status_code == 200
    assert quotation.status == QuotationStatus.SENT

    valid_response = client.post(
        reverse(
            "quotations:reject",
            args=(quotation.pk,),
        ),
        {
            "customer_name": "Daniel Kato",
            "method": CustomerDecisionMethod.PHONE,
            "notes": "Customer requested a cheaper option.",
        },
    )

    quotation.refresh_from_db()

    assert valid_response.status_code == 302
    assert quotation.status == QuotationStatus.REJECTED

    revision_response = client.post(
        reverse(
            "quotations:revise",
            args=(quotation.pk,),
        )
    )

    quotation.refresh_from_db()
    revision = Quotation.objects.get(
        job_card=quotation_view_context.job_card,
        is_current=True,
    )

    assert revision_response.status_code == 302
    assert not quotation.is_current
    assert revision.revision_number == 2
    assert revision.status == QuotationStatus.DRAFT


@pytest.mark.django_db
def test_job_detail_displays_current_quotation(
    client,
    quotation_view_context: QuotationViewContext,
) -> None:
    """Show quotation information on the related job page."""

    quotation = _create_draft_quotation(quotation_view_context)
    client.force_login(quotation_view_context.manager)

    response = client.get(
        reverse(
            "jobs:detail",
            args=(quotation_view_context.job_card.pk,),
        )
    )

    assert response.status_code == 200
    assert quotation.quotation_number.encode() in response.content
    assert b"Quotations" in response.content
