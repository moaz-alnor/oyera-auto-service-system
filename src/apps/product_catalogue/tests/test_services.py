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
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)
from apps.product_catalogue.services.catalogue import (
    ChangeProductPriceCommand,
    CreateProductCategoryCommand,
    CreateProductCommand,
    UpdateProductCategoryCommand,
    UpdateProductCommand,
    change_product_price,
    create_product,
    create_product_category,
    deactivate_product,
    deactivate_product_category,
    reactivate_product,
    reactivate_product_category,
    update_product,
    update_product_category,
)


def _create_lifecycle_manager(
    username: str,
) -> User:
    """Create a manager for product lifecycle tests."""

    ensure_default_roles()

    manager = User.objects.create_user(
        username=username,
        password="Strong-Test-Password-2026",
    )
    manager.groups.add(Group.objects.get(name=RoleName.MANAGER.value))

    return manager


def _create_test_category(
    *,
    actor: User,
    code: str = "FILTERS",
    name: str = "Filters",
) -> ProductCategory:
    """Create a product category through the service layer."""

    return create_product_category(
        actor=actor,
        command=CreateProductCategoryCommand(
            code=code,
            name=name,
        ),
    )


def _create_test_product(
    *,
    actor: User,
    category: ProductCategory,
    sku: str = "OIL-FILTER-001",
    name: str = "Engine Oil Filter",
) -> Product:
    """Create a priced product through the service layer."""

    if category.pk is None:
        raise RuntimeError("The test category must be saved.")

    return create_product(
        actor=actor,
        command=CreateProductCommand(
            category_id=category.pk,
            sku=sku,
            name=name,
            unit=ProductUnit.EACH,
            initial_price=Decimal("45000.00"),
        ),
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


@pytest.mark.django_db
def test_manager_can_update_product_category() -> None:
    """Update category information without replacing the record."""

    manager = _create_lifecycle_manager("category.update.manager")
    category = _create_test_category(
        actor=manager,
    )

    updated_category = update_product_category(
        actor=manager,
        category_id=category.pk,
        command=UpdateProductCategoryCommand(
            code="ENGINE-FILTERS",
            name="Engine Filters",
            description="Filters used in vehicle engines.",
        ),
    )

    assert updated_category.pk == category.pk
    assert updated_category.code == "ENGINE-FILTERS"
    assert updated_category.normalized_code == ("ENGINEFILTERS")
    assert updated_category.name == "Engine Filters"
    assert updated_category.description == ("Filters used in vehicle engines.")


@pytest.mark.django_db
def test_category_with_active_products_cannot_be_deactivated() -> None:
    """Protect active products from having an inactive category."""

    manager = _create_lifecycle_manager("category.block.manager")
    category = _create_test_category(
        actor=manager,
    )
    _create_test_product(
        actor=manager,
        category=category,
    )

    with pytest.raises(ValidationError):
        deactivate_product_category(
            actor=manager,
            category_id=category.pk,
        )

    category.refresh_from_db()

    assert category.is_active


@pytest.mark.django_db
def test_empty_category_can_be_deactivated_and_reactivated() -> None:
    """Change the status of a category with no active products."""

    manager = _create_lifecycle_manager("category.status.manager")
    category = _create_test_category(
        actor=manager,
    )

    deactivated_category = deactivate_product_category(
        actor=manager,
        category_id=category.pk,
    )

    assert not deactivated_category.is_active

    reactivated_category = reactivate_product_category(
        actor=manager,
        category_id=category.pk,
    )

    assert reactivated_category.is_active


@pytest.mark.django_db
def test_manager_can_update_product_without_changing_price_history() -> None:
    """Update product details while preserving its price records."""

    manager = _create_lifecycle_manager("product.update.manager")
    original_category = _create_test_category(
        actor=manager,
        code="FILTERS",
        name="Filters",
    )
    replacement_category = _create_test_category(
        actor=manager,
        code="ENGINE-PARTS",
        name="Engine Parts",
    )
    product = _create_test_product(
        actor=manager,
        category=original_category,
    )

    original_price = ProductPrice.objects.get(
        product=product,
        effective_until__isnull=True,
    )

    updated_product = update_product(
        actor=manager,
        product_id=product.pk,
        command=UpdateProductCommand(
            category_id=replacement_category.pk,
            sku="FILTER-ENGINE-001",
            name="Premium Engine Oil Filter",
            unit=ProductUnit.EACH,
            manufacturer="Toyota",
            manufacturer_part_number="90915-YZZD2",
            description="Premium replacement oil filter.",
        ),
    )

    prices = ProductPrice.objects.filter(product=product)

    assert updated_product.category == replacement_category
    assert updated_product.sku == "FILTER-ENGINE-001"
    assert updated_product.name == ("Premium Engine Oil Filter")
    assert updated_product.manufacturer == "Toyota"

    assert prices.count() == 1
    assert prices.get().pk == original_price.pk
    assert prices.get().amount == Decimal("45000.00")


@pytest.mark.django_db
def test_inactive_product_price_cannot_be_changed() -> None:
    """Prevent new price periods for inactive products."""

    manager = _create_lifecycle_manager("inactive.price.manager")
    category = _create_test_category(
        actor=manager,
    )
    product = _create_test_product(
        actor=manager,
        category=category,
    )

    deactivate_product(
        actor=manager,
        product_id=product.pk,
    )

    with pytest.raises(ValidationError):
        change_product_price(
            actor=manager,
            product_id=product.pk,
            command=ChangeProductPriceCommand(
                amount=Decimal("52000.00"),
            ),
        )

    assert ProductPrice.objects.filter(product=product).count() == 1


@pytest.mark.django_db
def test_product_reactivation_requires_active_category() -> None:
    """Block reactivation while the product category is inactive."""

    manager = _create_lifecycle_manager("reactivation.category.manager")
    category = _create_test_category(
        actor=manager,
    )
    product = _create_test_product(
        actor=manager,
        category=category,
    )

    deactivate_product(
        actor=manager,
        product_id=product.pk,
    )
    deactivate_product_category(
        actor=manager,
        category_id=category.pk,
    )

    with pytest.raises(ValidationError):
        reactivate_product(
            actor=manager,
            product_id=product.pk,
        )

    product.refresh_from_db()
    category.refresh_from_db()

    assert not product.is_active
    assert not category.is_active
