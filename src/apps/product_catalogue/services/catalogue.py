"""Application services for product-catalogue operations."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.product_catalogue.constants import (
    ProductPermissionName,
    ProductUnit,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
    ProductPrice,
)


@dataclass(frozen=True, slots=True)
class CreateProductCategoryCommand:
    """Contain validated product-category information."""

    code: str
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class UpdateProductCategoryCommand:
    """Contain replacement product-category information."""

    code: str
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    """Contain validated product and initial-price information."""

    category_id: int
    sku: str
    name: str
    unit: ProductUnit
    initial_price: Decimal
    manufacturer: str = ""
    manufacturer_part_number: str = ""
    description: str = ""
    currency: str = "UGX"
    price_notes: str = ""


@dataclass(frozen=True, slots=True)
class UpdateProductCommand:
    """Contain replacement product information."""

    category_id: int
    sku: str
    name: str
    unit: ProductUnit
    manufacturer: str = ""
    manufacturer_part_number: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class ChangeProductPriceCommand:
    """Contain information for a product price change."""

    amount: Decimal
    currency: str = "UGX"
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: ProductPermissionName,
) -> None:
    """Require an employee to hold a product permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this product-catalogue action."
        )


@transaction.atomic
def create_product_category(
    *,
    actor: User,
    command: CreateProductCategoryCommand,
) -> ProductCategory:
    """Create a reusable product category."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.ADD_PRODUCT_CATEGORY),
    )

    category = ProductCategory(
        code=command.code,
        name=command.name,
        description=command.description.strip(),
        created_by=actor,
        updated_by=actor,
    )

    category.full_clean()
    category.save()

    return category


@transaction.atomic
def update_product_category(
    *,
    actor: User,
    category_id: int,
    command: UpdateProductCategoryCommand,
) -> ProductCategory:
    """Update a product category without changing its products."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.CHANGE_PRODUCT_CATEGORY),
    )

    category = ProductCategory.objects.select_for_update().get(pk=category_id)

    category.code = command.code
    category.name = command.name
    category.description = command.description.strip()
    category.updated_by = actor

    category.full_clean()
    category.save(
        update_fields=(
            "code",
            "normalized_code",
            "name",
            "description",
            "updated_by",
            "updated_at",
        )
    )

    return category


@transaction.atomic
def deactivate_product_category(
    *,
    actor: User,
    category_id: int,
) -> ProductCategory:
    """Deactivate a category that has no active products."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.CHANGE_PRODUCT_CATEGORY),
    )

    category = ProductCategory.objects.select_for_update().get(pk=category_id)

    if not category.is_active:
        return category

    if Product.objects.filter(
        category=category,
        is_active=True,
    ).exists():
        raise ValidationError(
            {
                "is_active": (
                    "This category cannot be deactivated while "
                    "it contains active products. Deactivate or "
                    "move those products first."
                )
            }
        )

    category.is_active = False
    category.updated_by = actor
    category.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return category


@transaction.atomic
def reactivate_product_category(
    *,
    actor: User,
    category_id: int,
) -> ProductCategory:
    """Reactivate a product category."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.CHANGE_PRODUCT_CATEGORY),
    )

    category = ProductCategory.objects.select_for_update().get(pk=category_id)

    if category.is_active:
        return category

    category.is_active = True
    category.updated_by = actor
    category.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return category


@transaction.atomic
def create_product(
    *,
    actor: User,
    command: CreateProductCommand,
) -> Product:
    """Create a product with its initial selling price."""

    _require_permission(
        actor=actor,
        permission=ProductPermissionName.ADD_PRODUCT,
    )

    category = ProductCategory.objects.select_for_update().get(pk=command.category_id)

    if not category.is_active:
        raise ValidationError(
            {"category": ("A product cannot be created in an inactive category.")}
        )

    product = Product(
        category=category,
        sku=command.sku,
        name=command.name,
        unit=command.unit,
        manufacturer=command.manufacturer,
        manufacturer_part_number=(command.manufacturer_part_number),
        description=command.description.strip(),
        created_by=actor,
        updated_by=actor,
    )

    product.full_clean()
    product.save()

    price = ProductPrice(
        product=product,
        amount=command.initial_price,
        currency=command.currency,
        changed_by=actor,
        notes=command.price_notes.strip(),
    )

    price.full_clean()
    price.save()

    return product


@transaction.atomic
def update_product(
    *,
    actor: User,
    product_id: int,
    command: UpdateProductCommand,
) -> Product:
    """Update product information without changing price history."""

    _require_permission(
        actor=actor,
        permission=ProductPermissionName.CHANGE_PRODUCT,
    )

    product = Product.objects.select_for_update().get(pk=product_id)
    category = ProductCategory.objects.select_for_update().get(pk=command.category_id)

    if product.is_active and not category.is_active:
        raise ValidationError(
            {"category": ("An active product cannot be moved to an inactive category.")}
        )

    product.category = category
    product.sku = command.sku
    product.name = command.name
    product.unit = command.unit
    product.manufacturer = command.manufacturer
    product.manufacturer_part_number = command.manufacturer_part_number
    product.description = command.description.strip()
    product.updated_by = actor

    product.full_clean()
    product.save(
        update_fields=(
            "category",
            "sku",
            "normalized_sku",
            "name",
            "unit",
            "manufacturer",
            "manufacturer_part_number",
            "normalized_manufacturer_part_number",
            "description",
            "updated_by",
            "updated_at",
        )
    )

    return product


@transaction.atomic
def deactivate_product(
    *,
    actor: User,
    product_id: int,
) -> Product:
    """Deactivate a product without deleting its history."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.DEACTIVATE_PRODUCT),
    )

    product = Product.objects.select_for_update().get(pk=product_id)

    if not product.is_active:
        return product

    product.is_active = False
    product.updated_by = actor
    product.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return product


@transaction.atomic
def reactivate_product(
    *,
    actor: User,
    product_id: int,
) -> Product:
    """Reactivate a product with a valid category and price."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.REACTIVATE_PRODUCT),
    )

    product = (
        Product.objects.select_for_update()
        .select_related("category")
        .get(pk=product_id)
    )

    if product.is_active:
        return product

    if not product.category.is_active:
        raise ValidationError(
            {
                "is_active": (
                    "This product cannot be reactivated because "
                    "its category is inactive."
                )
            }
        )

    if not ProductPrice.objects.filter(
        product=product,
        effective_until__isnull=True,
    ).exists():
        raise ValidationError(
            {
                "is_active": (
                    "This product cannot be reactivated without "
                    "a current selling price."
                )
            }
        )

    product.is_active = True
    product.updated_by = actor
    product.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return product


@transaction.atomic
def change_product_price(
    *,
    actor: User,
    product_id: int,
    command: ChangeProductPriceCommand,
) -> ProductPrice:
    """Close the current price and create a new price period."""

    _require_permission(
        actor=actor,
        permission=(ProductPermissionName.CHANGE_PRODUCT_PRICE),
    )

    product = Product.objects.select_for_update().get(pk=product_id)

    if not product.is_active:
        raise ValidationError(
            {"product": ("The price of an inactive product cannot be changed.")}
        )

    current_price = (
        ProductPrice.objects.select_for_update()
        .filter(
            product=product,
            effective_until__isnull=True,
        )
        .first()
    )

    normalized_currency = command.currency.strip().upper()

    if (
        current_price is not None
        and current_price.amount == command.amount
        and current_price.currency == normalized_currency
    ):
        raise ValidationError(
            {"amount": ("The new product price must differ from the current price.")}
        )

    change_time = timezone.now()

    if current_price is not None:
        current_price.effective_until = change_time
        current_price.full_clean()
        current_price.save(
            update_fields=(
                "effective_until",
                "updated_at",
            )
        )

    new_price = ProductPrice(
        product=product,
        amount=command.amount,
        currency=normalized_currency,
        effective_from=change_time,
        changed_by=actor,
        notes=command.notes.strip(),
    )

    new_price.full_clean()
    new_price.save()

    return new_price
