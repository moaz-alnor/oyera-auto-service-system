"""Tests for product-catalogue models."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)


@pytest.fixture
def actor() -> User:
    """Create an employee for product model tests."""

    return User.objects.create_user(
        username="product.model.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.mark.django_db
def test_product_information_is_normalized(
    actor: User,
) -> None:
    """Normalize category codes, SKUs, names, and part numbers."""

    category = ProductCategory(
        code=" engine_parts ",
        name="  Engine   Parts  ",
        created_by=actor,
        updated_by=actor,
    )
    category.full_clean()
    category.save()

    product = Product(
        sku=" oil_filter_001 ",
        name="  Engine   Oil Filter  ",
        category=category,
        unit=ProductUnit.EACH,
        manufacturer="  Toyota  ",
        manufacturer_part_number="90915-yzzd2",
        created_by=actor,
        updated_by=actor,
    )

    product.full_clean()

    assert category.code == "ENGINE-PARTS"
    assert category.normalized_code == "ENGINEPARTS"
    assert category.name == "Engine Parts"

    assert product.sku == "OIL-FILTER-001"
    assert product.normalized_sku == "OILFILTER001"
    assert product.name == "Engine Oil Filter"
    assert product.manufacturer == "Toyota"
    assert product.manufacturer_part_number == "90915-YZZD2"
    assert product.normalized_manufacturer_part_number == "90915YZZD2"


@pytest.mark.django_db
def test_product_price_rejects_non_positive_amount(
    actor: User,
) -> None:
    """Reject zero or negative product selling prices."""

    category = ProductCategory.objects.create(
        code="FILTERS",
        normalized_code="FILTERS",
        name="Filters",
        created_by=actor,
        updated_by=actor,
    )
    product = Product.objects.create(
        sku="FILTER-001",
        normalized_sku="FILTER001",
        name="Oil Filter",
        category=category,
        unit=ProductUnit.EACH,
        created_by=actor,
        updated_by=actor,
    )

    price = ProductPrice(
        product=product,
        amount=Decimal("0.00"),
        currency="UGX",
        changed_by=actor,
    )

    with pytest.raises(ValidationError):
        price.full_clean()
