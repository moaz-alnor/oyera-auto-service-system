"""Read-only database queries for product-catalogue information."""

from django.db.models import Q, QuerySet

from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)
from apps.product_catalogue.normalization import (
    normalize_category_code_search,
    normalize_part_number_search,
    normalize_product_sku_search,
)


def search_product_categories(
    *,
    query: str = "",
    include_inactive: bool = False,
) -> QuerySet[ProductCategory]:
    """Return product categories matching search criteria."""

    categories = ProductCategory.objects.select_related(
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        categories = categories.filter(is_active=True)

    search_value = query.strip()

    if not search_value:
        return categories

    normalized_code = normalize_category_code_search(search_value)

    search_filter = (
        Q(code__icontains=search_value)
        | Q(name__icontains=search_value)
        | Q(description__icontains=search_value)
    )

    if normalized_code:
        search_filter |= Q(normalized_code__icontains=normalized_code)

    return categories.filter(search_filter)


def get_active_product_categories() -> QuerySet[ProductCategory]:
    """Return active categories for product selection."""

    return ProductCategory.objects.filter(is_active=True).order_by(
        "name",
        "code",
    )


def search_products(
    *,
    query: str = "",
    category_id: int | None = None,
    include_inactive: bool = False,
) -> QuerySet[Product]:
    """Return products matching catalogue search criteria."""

    products = Product.objects.select_related(
        "category",
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        products = products.filter(is_active=True)

    if category_id is not None:
        products = products.filter(category_id=category_id)

    search_value = query.strip()

    if not search_value:
        return products

    normalized_sku = normalize_product_sku_search(search_value)
    normalized_part_number = normalize_part_number_search(search_value)

    search_filter = (
        Q(sku__icontains=search_value)
        | Q(name__icontains=search_value)
        | Q(manufacturer__icontains=search_value)
        | Q(manufacturer_part_number__icontains=search_value)
        | Q(description__icontains=search_value)
    )

    if normalized_sku:
        search_filter |= Q(normalized_sku__icontains=normalized_sku)

    if normalized_part_number:
        search_filter |= Q(
            normalized_manufacturer_part_number__icontains=(normalized_part_number)
        )

    return products.filter(search_filter)


def get_product_by_id(
    *,
    product_id: int,
) -> Product:
    """Return one product with category and employee information."""

    return Product.objects.select_related(
        "category",
        "created_by",
        "updated_by",
    ).get(pk=product_id)


def get_current_product_price(
    *,
    product_id: int,
) -> ProductPrice | None:
    """Return the current open-ended selling price."""

    return (
        ProductPrice.objects.filter(
            product_id=product_id,
            effective_until__isnull=True,
        )
        .select_related(
            "product",
            "changed_by",
        )
        .first()
    )


def get_product_price_history(
    *,
    product_id: int,
) -> QuerySet[ProductPrice]:
    """Return all product-price periods, newest first."""

    return (
        ProductPrice.objects.filter(product_id=product_id)
        .select_related(
            "product",
            "changed_by",
        )
        .order_by(
            "-effective_from",
            "-created_at",
        )
    )


def get_product_category_by_id(
    *,
    category_id: int,
) -> ProductCategory:
    """Return one product category with employee information."""

    return ProductCategory.objects.select_related(
        "created_by",
        "updated_by",
    ).get(pk=category_id)
