"""Database models for the product catalogue."""

from collections.abc import Collection
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.normalization import (
    normalize_category_code_display,
    normalize_category_code_key,
    normalize_part_number_display,
    normalize_part_number_key,
    normalize_product_name,
    normalize_product_sku_display,
    normalize_product_sku_key,
)


class ProductCategory(TimeStampedModel):
    """Represent a reusable product classification."""

    code = models.CharField(
        max_length=30,
    )
    normalized_code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_categories_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_categories_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure category ordering and indexes."""

        ordering = (
            "name",
            "code",
        )
        indexes = (
            models.Index(
                fields=("is_active", "name"),
                name="prodcat_active_name_idx",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalize category fields before validation."""

        excluded_fields = set(exclude or ())

        if "code" not in excluded_fields:
            self.code = normalize_category_code_display(self.code)
            self.normalized_code = normalize_category_code_key(self.code)

        if "name" not in excluded_fields:
            self.name = normalize_product_name(self.name)

        super().clean_fields(exclude=exclude)

    def __str__(self) -> str:
        """Return the category code and name."""

        return f"{self.code} — {self.name}"


class Product(TimeStampedModel):
    """Represent a sellable part, material, or consumable."""

    sku = models.CharField(
        max_length=40,
    )
    normalized_sku = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )
    name = models.CharField(
        max_length=150,
        db_index=True,
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
    )
    manufacturer_part_number = models.CharField(
        max_length=80,
        blank=True,
    )
    normalized_manufacturer_part_number = models.CharField(
        max_length=80,
        blank=True,
        db_index=True,
        editable=False,
    )
    unit = models.CharField(
        max_length=20,
        choices=ProductUnit.choices,
        default=ProductUnit.EACH,
    )
    description = models.TextField(
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="catalogue_products_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="catalogue_products_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure product ordering and permissions."""

        ordering = (
            "name",
            "sku",
        )
        permissions = (
            (
                "change_product_price",
                "Can change product price",
            ),
            (
                "deactivate_product",
                "Can deactivate product",
            ),
            (
                "reactivate_product",
                "Can reactivate product",
            ),
        )
        indexes = (
            models.Index(
                fields=("is_active", "name"),
                name="product_active_name_idx",
            ),
            models.Index(
                fields=("category", "is_active"),
                name="product_category_idx",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalize product fields before validation."""

        excluded_fields = set(exclude or ())

        if "sku" not in excluded_fields:
            self.sku = normalize_product_sku_display(self.sku)
            self.normalized_sku = normalize_product_sku_key(self.sku)

        if "name" not in excluded_fields:
            self.name = normalize_product_name(self.name)

        if "manufacturer_part_number" not in excluded_fields:
            self.manufacturer_part_number = normalize_part_number_display(
                self.manufacturer_part_number
            )
            self.normalized_manufacturer_part_number = normalize_part_number_key(
                self.manufacturer_part_number
            )

        self.manufacturer = (
            normalize_product_name(self.manufacturer)
            if self.manufacturer.strip()
            else ""
        )

        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        """Require an active category for an active product."""

        super().clean()

        try:
            category = self.category
        except ObjectDoesNotExist:
            # Django's field validation will report a missing category.
            return

        if self.is_active and not category.is_active:
            raise ValidationError(
                {
                    "category": (
                        "An active product must belong to an active product category."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the product SKU and name."""

        return f"{self.sku} — {self.name}"


class ProductPrice(TimeStampedModel):
    """Preserve a historical product selling-price period."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="price_history",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(
        max_length=3,
        default="UGX",
    )
    effective_from = models.DateTimeField(
        default=timezone.now,
    )
    effective_until = models.DateTimeField(
        null=True,
        blank=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="product_price_changes",
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure price ordering and database constraints."""

        ordering = (
            "-effective_from",
            "-created_at",
        )
        constraints = (
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(effective_until__isnull=True),
                name="product_one_current_price",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="product_price_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(effective_until__isnull=True)
                    | Q(effective_until__gt=F("effective_from"))
                ),
                name="product_price_valid_period",
            ),
        )

    def clean(self) -> None:
        """Validate price, currency, and effective period."""

        super().clean()

        if self.amount <= Decimal("0"):
            raise ValidationError(
                {"amount": ("Product price must be greater than zero.")}
            )

        self.currency = self.currency.strip().upper()

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": ("Currency must be a three-letter code.")}
            )

        if (
            self.effective_until is not None
            and self.effective_until <= self.effective_from
        ):
            raise ValidationError(
                {
                    "effective_until": (
                        "The price end time must be later than its start time."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the product and price description."""

        return f"{self.product.sku} — {self.currency} {self.amount}"
