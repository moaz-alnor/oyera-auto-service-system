"""Tests for product-catalogue read queries."""

from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)
from apps.product_catalogue.selectors import (
    get_current_product_price,
    search_products,
)


@pytest.fixture
def actor() -> User:
    """Create an employee for product selector tests."""

    return User.objects.create_user(
        username="product.selector.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.fixture
def catalogue_records(
    actor: User,
) -> tuple[
    ProductCategory,
    ProductCategory,
    Product,
    Product,
    Product,
]:
    """Create categories and products for catalogue searches."""

    filters_category = ProductCategory.objects.create(
        code="FILTERS",
        normalized_code="FILTERS",
        name="Filters",
        created_by=actor,
        updated_by=actor,
    )
    brakes_category = ProductCategory.objects.create(
        code="BRAKES",
        normalized_code="BRAKES",
        name="Brake Parts",
        created_by=actor,
        updated_by=actor,
    )

    oil_filter = Product.objects.create(
        sku="OIL-FILTER-001",
        normalized_sku="OILFILTER001",
        name="Engine Oil Filter",
        category=filters_category,
        manufacturer="Toyota",
        manufacturer_part_number="90915-YZZD2",
        normalized_manufacturer_part_number="90915YZZD2",
        unit=ProductUnit.EACH,
        created_by=actor,
        updated_by=actor,
    )
    brake_pad = Product.objects.create(
        sku="BRAKE-PAD-001",
        normalized_sku="BRAKEPAD001",
        name="Front Brake Pad Set",
        category=brakes_category,
        unit=ProductUnit.SET,
        created_by=actor,
        updated_by=actor,
    )
    inactive_filter = Product.objects.create(
        sku="FILTER-ARCHIVED",
        normalized_sku="FILTERARCHIVED",
        name="Archived Filter",
        category=filters_category,
        unit=ProductUnit.EACH,
        is_active=False,
        created_by=actor,
        updated_by=actor,
    )

    ProductPrice.objects.create(
        product=oil_filter,
        amount=Decimal("45000.00"),
        currency="UGX",
        changed_by=actor,
    )

    return (
        filters_category,
        brakes_category,
        oil_filter,
        brake_pad,
        inactive_filter,
    )


@pytest.mark.django_db
def test_product_search_finds_formatted_sku(
    catalogue_records: tuple[
        ProductCategory,
        ProductCategory,
        Product,
        Product,
        Product,
    ],
) -> None:
    """Find a product despite differences in SKU punctuation."""

    _, _, oil_filter, _, _ = catalogue_records

    results = search_products(query="oil filter 001")

    assert list(results) == [oil_filter]


@pytest.mark.django_db
def test_product_search_finds_part_number(
    catalogue_records: tuple[
        ProductCategory,
        ProductCategory,
        Product,
        Product,
        Product,
    ],
) -> None:
    """Find a product using a formatted manufacturer part number."""

    _, _, oil_filter, _, _ = catalogue_records

    results = search_products(query="90915 yzzd2")

    assert list(results) == [oil_filter]


@pytest.mark.django_db
def test_product_search_filters_by_category(
    catalogue_records: tuple[
        ProductCategory,
        ProductCategory,
        Product,
        Product,
        Product,
    ],
) -> None:
    """Return active products from the selected category."""

    filters_category, _, oil_filter, _, _ = catalogue_records

    results = search_products(
        category_id=filters_category.pk,
    )

    assert list(results) == [oil_filter]


@pytest.mark.django_db
def test_product_search_excludes_inactive_by_default(
    catalogue_records: tuple[
        ProductCategory,
        ProductCategory,
        Product,
        Product,
        Product,
    ],
) -> None:
    """Hide inactive products unless explicitly requested."""

    _, _, _, _, inactive_filter = catalogue_records

    default_results = search_products(query="Archived Filter")
    historical_results = search_products(
        query="Archived Filter",
        include_inactive=True,
    )

    assert inactive_filter not in default_results
    assert inactive_filter in historical_results


@pytest.mark.django_db
def test_current_product_price_returns_open_price(
    catalogue_records: tuple[
        ProductCategory,
        ProductCategory,
        Product,
        Product,
        Product,
    ],
) -> None:
    """Return the current open-ended product price."""

    _, _, oil_filter, _, _ = catalogue_records

    current_price = get_current_product_price(product_id=oil_filter.pk)

    assert current_price is not None
    assert current_price.amount == Decimal("45000.00")
    assert current_price.effective_until is None
