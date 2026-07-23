"""Tests for product-catalogue application services."""

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
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import ProductPrice
from apps.product_catalogue.services.catalogue import (
    ChangeProductPriceCommand,
    CreateProductCategoryCommand,
    CreateProductCommand,
    change_product_price,
    create_product,
    create_product_category,
)


@pytest.mark.django_db
def test_manager_can_create_product_with_initial_price() -> None:
    """Create a category, product, and current selling price."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="product.catalogue.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

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
            initial_price=Decimal("45000.00"),
            manufacturer="Toyota",
            manufacturer_part_number="90915-YZZD2",
        ),
    )

    current_price = ProductPrice.objects.get(
        product=product,
        effective_until__isnull=True,
    )

    assert product.sku == "OIL-FILTER-001"
    assert product.category == category
    assert current_price.amount == Decimal("45000.00")


@pytest.mark.django_db
def test_manager_can_change_product_price() -> None:
    """Close the previous price and create a new current price."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="product.price.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

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
            initial_price=Decimal("120000.00"),
        ),
    )

    previous_price = ProductPrice.objects.get(
        product=product,
        effective_until__isnull=True,
    )

    new_price = change_product_price(
        actor=manager,
        product_id=product.pk,
        command=ChangeProductPriceCommand(
            amount=Decimal("135000.00"),
            notes="Updated supplier cost.",
        ),
    )

    previous_price.refresh_from_db()

    assert previous_price.effective_until is not None
    assert new_price.amount == Decimal("135000.00")
    assert new_price.effective_until is None
    assert previous_price.effective_until == new_price.effective_from


@pytest.mark.django_db
def test_product_cannot_use_inactive_category() -> None:
    """Prevent new products from using an inactive category."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="inactive.category.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    category = create_product_category(
        actor=manager,
        command=CreateProductCategoryCommand(
            code="ARCHIVED",
            name="Archived Products",
        ),
    )
    category.is_active = False
    category.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    with pytest.raises(ValidationError):
        create_product(
            actor=manager,
            command=CreateProductCommand(
                category_id=category.pk,
                sku="ARCHIVED-001",
                name="Archived Part",
                unit=ProductUnit.EACH,
                initial_price=Decimal("10000.00"),
            ),
        )


@pytest.mark.django_db
def test_receptionist_cannot_change_product_price() -> None:
    """Prevent receptionists from modifying selling prices."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username="product.owner.manager",
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    receptionist = User.objects.create_user(
        username="product.receptionist",
        password="Strong-Test-Password-2026",
    )
    receptionist.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    category = create_product_category(
        actor=manager,
        command=CreateProductCategoryCommand(
            code="FLUIDS",
            name="Vehicle Fluids",
        ),
    )
    product = create_product(
        actor=manager,
        command=CreateProductCommand(
            category_id=category.pk,
            sku="ENGINE-OIL-5W30",
            name="Engine Oil 5W-30",
            unit=ProductUnit.LITRE,
            initial_price=Decimal("79000.00"),
        ),
    )

    with pytest.raises(PermissionDenied):
        change_product_price(
            actor=receptionist,
            product_id=product.pk,
            command=ChangeProductPriceCommand(
                amount=Decimal("85000.00"),
            ),
        )
