"""Tests for product-catalogue HTTP workflows."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)
from apps.product_catalogue.services.catalogue import (
    CreateProductCategoryCommand,
    CreateProductCommand,
    create_product,
    create_product_category,
)


@pytest.fixture
def manager() -> User:
    """Create an employee with product-management permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="product.view.manager",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create an employee with read-only product access."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="product.view.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def product_category(
    manager: User,
) -> ProductCategory:
    """Create an active product category."""

    return create_product_category(
        actor=manager,
        command=CreateProductCategoryCommand(
            code="FILTERS",
            name="Filters",
        ),
    )


@pytest.fixture
def catalogue_product(
    manager: User,
    product_category: ProductCategory,
) -> Product:
    """Create a product through the application service."""

    return create_product(
        actor=manager,
        command=CreateProductCommand(
            category_id=product_category.pk,
            sku="OIL-FILTER-001",
            name="Engine Oil Filter",
            unit=ProductUnit.EACH,
            initial_price=Decimal("45000.00"),
            manufacturer="Toyota",
            manufacturer_part_number="90915-YZZD2",
        ),
    )


@pytest.mark.django_db
def test_product_list_requires_authentication(client) -> None:
    """Redirect anonymous visitors to employee login."""

    response = client.get(reverse("product_catalogue:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.headers["Location"]


@pytest.mark.django_db
def test_technician_can_view_products(
    client,
    technician: User,
) -> None:
    """Allow technicians to inspect catalogue products."""

    client.force_login(technician)

    response = client.get(reverse("product_catalogue:list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_technician_cannot_create_product(
    client,
    technician: User,
) -> None:
    """Return HTTP 403 for unauthorized product creation."""

    client.force_login(technician)

    response = client.get(reverse("product_catalogue:create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_can_create_product_category(
    client,
    manager: User,
) -> None:
    """Create a product category through the interface."""

    client.force_login(manager)

    response = client.post(
        reverse("product_catalogue:category_create"),
        {
            "code": "BRAKES",
            "name": "Brake Parts",
            "description": "Brake-system replacement parts.",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("product_catalogue:category_list")
    assert ProductCategory.objects.filter(normalized_code="BRAKES").exists()


@pytest.mark.django_db
def test_manager_can_create_product(
    client,
    manager: User,
    product_category: ProductCategory,
) -> None:
    """Create a product and initial price through the interface."""

    client.force_login(manager)

    response = client.post(
        reverse("product_catalogue:create"),
        {
            "category": product_category.pk,
            "sku": "BRAKE-PAD-001",
            "name": "Front Brake Pad Set",
            "manufacturer": "Toyota",
            "manufacturer_part_number": "04465-0D150",
            "unit": ProductUnit.SET,
            "description": "Front axle brake-pad set.",
            "initial_price": "120000.00",
            "currency": "UGX",
            "price_notes": "Opening catalogue price.",
        },
    )

    product = Product.objects.get(normalized_sku="BRAKEPAD001")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "product_catalogue:detail",
        args=(product.pk,),
    )
    assert ProductPrice.objects.filter(
        product=product,
        amount=Decimal("120000.00"),
        effective_until__isnull=True,
    ).exists()


@pytest.mark.django_db
def test_manager_can_change_product_price(
    client,
    manager: User,
    catalogue_product: Product,
) -> None:
    """Create a new historical selling-price period."""

    client.force_login(manager)

    response = client.post(
        reverse(
            "product_catalogue:change_price",
            args=(catalogue_product.pk,),
        ),
        {
            "amount": "52000.00",
            "currency": "UGX",
            "notes": "Updated supplier price.",
        },
    )

    prices = ProductPrice.objects.filter(product=catalogue_product)

    assert response.status_code == 302
    assert prices.count() == 2
    assert prices.filter(
        amount=Decimal("45000.00"),
        effective_until__isnull=False,
    ).exists()
    assert prices.filter(
        amount=Decimal("52000.00"),
        effective_until__isnull=True,
    ).exists()


@pytest.mark.django_db
def test_technician_cannot_change_product_price(
    client,
    technician: User,
    catalogue_product: Product,
) -> None:
    """Return HTTP 403 for unauthorized price changes."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "product_catalogue:change_price",
            args=(catalogue_product.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_product_detail_displays_price_history(
    client,
    technician: User,
    catalogue_product: Product,
) -> None:
    """Display product and current selling-price information."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "product_catalogue:detail",
            args=(catalogue_product.pk,),
        )
    )

    assert response.status_code == 200
    assert b"OIL-FILTER-001" in response.content
    assert b"Engine Oil Filter" in response.content
    assert b"45000.00" in response.content
