"""Tests for quotation application services."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

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
    ChangeProductPriceCommand,
    CreateProductCategoryCommand,
    CreateProductCommand,
    change_product_price,
    create_product,
    create_product_category,
)
from apps.quotations.constants import (
    CustomerDecisionMethod,
    QuotationStatus,
)
from apps.quotations.models import (
    QuotationProductLine,
    QuotationServiceLine,
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
    create_quotation_revision,
    reject_quotation,
    submit_quotation,
)
from apps.service_catalogue.models import Service
from apps.service_catalogue.services.catalogue import (
    ChangeServicePriceCommand,
    CreateServiceCommand,
    change_service_price,
    create_service,
)
from apps.vehicles.constants import VehicleCategory
from apps.vehicles.models import Vehicle


def _create_manager() -> User:
    """Create a manager with quotation permissions."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="quotation.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    return manager


def _create_quotation_context() -> tuple[
    User,
    JobCard,
    Service,
    Product,
]:
    """Create a job, service, and product for quotation tests."""

    manager = _create_manager()

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

    return manager, job_card, service, product


@pytest.mark.django_db
def test_quotation_calculates_snapshot_totals() -> None:
    """Calculate service, product, discount, tax, and total."""

    manager, job_card, service, product = _create_quotation_context()

    quotation = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(
            discount_percentage=Decimal("10.00"),
            tax_percentage=Decimal("18.00"),
        ),
    )

    add_service_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=service.pk,
        ),
    )
    add_product_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddProductLineCommand(
            product_id=product.pk,
            quantity=Decimal("2.000"),
        ),
    )

    assert quotation.service_subtotal == Decimal("100000.00")
    assert quotation.product_subtotal == Decimal("100000.00")
    assert quotation.subtotal == Decimal("200000.00")
    assert quotation.discount_amount == Decimal("20000.00")
    assert quotation.taxable_amount == Decimal("180000.00")
    assert quotation.tax_amount == Decimal("32400.00")
    assert quotation.total == Decimal("212400.00")


@pytest.mark.django_db
def test_catalogue_changes_do_not_change_quote_snapshots() -> None:
    """Preserve quoted prices after catalogue prices change."""

    manager, job_card, service, product = _create_quotation_context()
    quotation = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(),
    )

    service_line = add_service_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddServiceLineCommand(
            service_id=service.pk,
        ),
    )
    product_line = add_product_line(
        actor=manager,
        quotation_id=quotation.pk,
        command=AddProductLineCommand(
            product_id=product.pk,
        ),
    )

    change_service_price(
        actor=manager,
        service_id=service.pk,
        command=ChangeServicePriceCommand(
            amount=Decimal("120000.00"),
        ),
    )
    change_product_price(
        actor=manager,
        product_id=product.pk,
        command=ChangeProductPriceCommand(
            amount=Decimal("60000.00"),
        ),
    )

    service_line.refresh_from_db()
    product_line.refresh_from_db()

    assert service_line.unit_price == Decimal("100000.00")
    assert product_line.unit_price == Decimal("50000.00")


@pytest.mark.django_db
def test_job_cannot_have_two_current_quotations() -> None:
    """Prevent two current quotation revisions for one job."""

    manager, job_card, _, _ = _create_quotation_context()

    create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(),
    )

    with pytest.raises(ValidationError):
        create_quotation(
            actor=manager,
            job_card_id=job_card.pk,
            command=CreateQuotationCommand(),
        )


@pytest.mark.django_db
def test_empty_quotation_cannot_be_submitted() -> None:
    """Require at least one quotation line."""

    manager, job_card, _, _ = _create_quotation_context()
    quotation = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(),
    )

    with pytest.raises(ValidationError):
        submit_quotation(
            actor=manager,
            quotation_id=quotation.pk,
        )


@pytest.mark.django_db
def test_approved_quotation_is_immutable() -> None:
    """Prevent line changes after customer approval."""

    manager, job_card, service, product = _create_quotation_context()
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
        ),
    )
    submit_quotation(
        actor=manager,
        quotation_id=quotation.pk,
    )
    approve_quotation(
        actor=manager,
        quotation_id=quotation.pk,
        command=RecordCustomerDecisionCommand(
            customer_name="Daniel Kato",
            method=CustomerDecisionMethod.IN_PERSON,
        ),
    )

    with pytest.raises(ValidationError):
        add_product_line(
            actor=manager,
            quotation_id=quotation.pk,
            command=AddProductLineCommand(
                product_id=product.pk,
            ),
        )

    quotation.refresh_from_db()

    assert quotation.status == QuotationStatus.APPROVED
    assert quotation.decision_recorded_by == manager


@pytest.mark.django_db
def test_rejected_quotation_can_be_revised() -> None:
    """Copy rejected line snapshots into a new draft revision."""

    manager, job_card, service, product = _create_quotation_context()
    original = create_quotation(
        actor=manager,
        job_card_id=job_card.pk,
        command=CreateQuotationCommand(),
    )

    add_service_line(
        actor=manager,
        quotation_id=original.pk,
        command=AddServiceLineCommand(
            service_id=service.pk,
        ),
    )
    add_product_line(
        actor=manager,
        quotation_id=original.pk,
        command=AddProductLineCommand(
            product_id=product.pk,
        ),
    )
    submit_quotation(
        actor=manager,
        quotation_id=original.pk,
    )
    reject_quotation(
        actor=manager,
        quotation_id=original.pk,
        command=RecordCustomerDecisionCommand(
            customer_name="Daniel Kato",
            method=CustomerDecisionMethod.PHONE,
            notes="Customer requested a lower-cost option.",
        ),
    )

    revision = create_quotation_revision(
        actor=manager,
        quotation_id=original.pk,
    )
    original.refresh_from_db()

    assert original.status == QuotationStatus.REJECTED
    assert not original.is_current

    assert revision.revision_number == 2
    assert revision.status == QuotationStatus.DRAFT
    assert revision.is_current

    assert QuotationServiceLine.objects.filter(
        quotation=revision,
        unit_price=Decimal("100000.00"),
    ).exists()
    assert QuotationProductLine.objects.filter(
        quotation=revision,
        unit_price=Decimal("50000.00"),
    ).exists()
