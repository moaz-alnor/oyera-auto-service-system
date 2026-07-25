"""Database models for inventory and stock movements."""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.inventory.constants import (
    ReservationStatus,
    StockMovementType,
)
from apps.inventory.normalization import (
    normalize_location_code,
    normalize_reference,
)
from apps.product_catalogue.models import Product
from apps.workshop.models import WorkProductRequirement


class StockLocation(TimeStampedModel):
    """Represent a physical inventory storage location."""

    code = models.CharField(
        max_length=30,
    )
    normalized_code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    name = models.CharField(
        max_length=120,
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
        related_name="inventory_locations_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_locations_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        """Configure storage-location ordering and indexes."""

        ordering = (
            "name",
            "code",
        )
        indexes = (
            models.Index(
                fields=(
                    "is_active",
                    "name",
                ),
                name="inv_loc_active_name_idx",
            ),
        )

    def clean(self) -> None:
        """Normalize and validate the location."""

        super().clean()

        self.code = self.code.strip()
        self.normalized_code = normalize_location_code(self.code)
        self.name = self.name.strip()
        self.description = self.description.strip()

        if not self.normalized_code:
            raise ValidationError({"code": ("Enter a valid storage-location code.")})

        if not self.name:
            raise ValidationError({"name": "Enter a storage-location name."})

    def __str__(self) -> str:
        """Return the location code and name."""

        return f"{self.code} — {self.name}"


class InventoryItem(TimeStampedModel):
    """Connect one catalogue product to one stock location."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory_items",
    )
    location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        related_name="inventory_items",
    )
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_items_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_items_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        """Configure item uniqueness and indexes."""

        ordering = (
            "product__name",
            "location__name",
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "product",
                    "location",
                ),
                name="inv_unique_product_location",
            ),
            models.CheckConstraint(
                condition=Q(reorder_level__gte=0),
                name="inv_reorder_level_nonnegative",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "is_active",
                    "product",
                ),
                name="inv_item_active_product_idx",
            ),
            models.Index(
                fields=(
                    "location",
                    "is_active",
                ),
                name="inv_item_location_idx",
            ),
        )

    def clean(self) -> None:
        """Validate product and location availability."""

        super().clean()

        self.notes = self.notes.strip()

        if self.reorder_level < Decimal("0"):
            raise ValidationError(
                {"reorder_level": ("Reorder level cannot be negative.")}
            )

        if self.is_active and not self.product.is_active:
            raise ValidationError(
                {
                    "product": (
                        "An active inventory item requires an active catalogue product."
                    )
                }
            )

        if self.is_active and not self.location.is_active:
            raise ValidationError(
                {
                    "location": (
                        "An active inventory item requires an active stock location."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the product and storage location."""

        return f"{self.product} — {self.location.code}"


class StockReservation(TimeStampedModel):
    """Reserve inventory for one workshop product requirement."""

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    work_product_requirement = models.ForeignKey(
        WorkProductRequirement,
        on_delete=models.PROTECT,
        related_name="stock_reservations",
    )
    status = models.CharField(
        max_length=24,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
        db_index=True,
    )

    quantity_reserved = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    quantity_issued = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
    )
    quantity_released = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
    )

    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_reservations_created",
        editable=False,
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_reservations_released",
        null=True,
        blank=True,
        editable=False,
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    release_reason = models.TextField(
        blank=True,
    )

    class Meta:
        """Configure reservation integrity and permissions."""

        ordering = (
            "-created_at",
            "-pk",
        )
        permissions = (
            (
                "reserve_stock",
                "Can reserve stock",
            ),
            (
                "release_stock_reservation",
                "Can release a stock reservation",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(quantity_reserved__gt=0),
                name="inv_reservation_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(quantity_issued__gte=0),
                name="inv_reservation_issued_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_released__gte=0),
                name="inv_reservation_released_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        quantity_issued__lte=(
                            F("quantity_reserved") - F("quantity_released")
                        )
                    )
                ),
                name="inv_reservation_within_quantity",
            ),
            models.UniqueConstraint(
                fields=(
                    "inventory_item",
                    "work_product_requirement",
                ),
                condition=Q(
                    status__in=(
                        ReservationStatus.ACTIVE,
                        ReservationStatus.PARTIALLY_ISSUED,
                    )
                ),
                name="inv_one_active_reservation",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "inventory_item",
                    "status",
                ),
                name="inv_res_item_status_idx",
            ),
            models.Index(
                fields=(
                    "work_product_requirement",
                    "status",
                ),
                name="inv_res_requirement_idx",
            ),
        )

    @property
    def remaining_quantity(self) -> Decimal:
        """Return quantity still reserved and unissued."""

        return self.quantity_reserved - self.quantity_issued - self.quantity_released

    def clean(self) -> None:
        """Validate quantities and product compatibility."""

        super().clean()

        self.release_reason = self.release_reason.strip()

        if self.quantity_reserved <= Decimal("0"):
            raise ValidationError(
                {"quantity_reserved": ("Reserved quantity must be greater than zero.")}
            )

        if self.quantity_issued < Decimal("0"):
            raise ValidationError(
                {"quantity_issued": ("Issued quantity cannot be negative.")}
            )

        if self.quantity_released < Decimal("0"):
            raise ValidationError(
                {"quantity_released": ("Released quantity cannot be negative.")}
            )

        if self.quantity_issued + self.quantity_released > self.quantity_reserved:
            raise ValidationError(
                "Issued and released quantities cannot exceed the reserved quantity."
            )

        requirement_product = self.work_product_requirement.source_product_line.product

        if self.inventory_item.product != requirement_product:
            raise ValidationError(
                {
                    "inventory_item": (
                        "The inventory product must match the "
                        "work-order product requirement."
                    )
                }
            )

        if (
            self.status
            in {
                ReservationStatus.RELEASED,
                ReservationStatus.CANCELLED,
            }
            and not self.release_reason
        ):
            raise ValidationError(
                {"release_reason": ("Record why this reservation ended.")}
            )

    def __str__(self) -> str:
        """Return the reserved product and work order."""

        requirement = self.work_product_requirement

        return (
            f"{requirement.work_order.work_order_number} — "
            f"{requirement.product_name_snapshot}"
        )


class StockMovement(TimeStampedModel):
    """Record one immutable physical stock change."""

    POSITIVE_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            StockMovementType.RECEIPT,
            StockMovementType.RETURN,
            StockMovementType.ADJUSTMENT_IN,
        }
    )
    NEGATIVE_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            StockMovementType.ISSUE,
            StockMovementType.ADJUSTMENT_OUT,
        }
    )

    movement_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(
        max_length=24,
        choices=StockMovementType.choices,
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    reservation = models.ForeignKey(
        StockReservation,
        on_delete=models.PROTECT,
        related_name="movements",
        null=True,
        blank=True,
    )
    source_movement = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="reversal_movements",
        null=True,
        blank=True,
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        max_length=3,
        default="UGX",
    )
    external_reference = models.CharField(
        max_length=120,
        blank=True,
    )
    notes = models.TextField(
        blank=True,
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements_created",
        editable=False,
    )

    class Meta:
        """Configure ledger ordering, permissions, and checks."""

        ordering = (
            "-occurred_at",
            "-pk",
        )
        permissions = (
            (
                "receive_stock",
                "Can receive stock",
            ),
            (
                "issue_stock",
                "Can issue stock",
            ),
            (
                "return_stock",
                "Can return issued stock",
            ),
            (
                "adjust_stock",
                "Can adjust stock",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="inv_movement_quantity_positive",
            ),
            models.CheckConstraint(
                condition=(Q(unit_cost__isnull=True) | Q(unit_cost__gte=0)),
                name="inv_movement_cost_nonnegative",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "inventory_item",
                    "occurred_at",
                ),
                name="inv_move_item_time_idx",
            ),
            models.Index(
                fields=(
                    "movement_type",
                    "occurred_at",
                ),
                name="inv_move_type_time_idx",
            ),
        )

    @property
    def signed_quantity(self) -> Decimal:
        """Return quantity with its ledger direction."""

        if self.movement_type in self.POSITIVE_TYPES:
            return self.quantity

        return -self.quantity

    def clean(self) -> None:
        """Validate stock-movement references."""

        super().clean()

        self.movement_number = self.movement_number.strip().upper()
        self.currency = self.currency.strip().upper()
        self.external_reference = normalize_reference(self.external_reference)
        self.notes = self.notes.strip()

        if not self.movement_number:
            raise ValidationError(
                {"movement_number": ("A stock movement number is required.")}
            )

        if self.quantity <= Decimal("0"):
            raise ValidationError(
                {"quantity": ("Movement quantity must be greater than zero.")}
            )

        if self.unit_cost is not None and self.unit_cost < 0:
            raise ValidationError({"unit_cost": ("Unit cost cannot be negative.")})

        if len(self.currency) != 3:
            raise ValidationError(
                {"currency": ("Currency must use a three-letter code.")}
            )

        if (
            self.movement_type
            in {
                StockMovementType.ISSUE,
                StockMovementType.RETURN,
            }
            and self.reservation is None
        ):
            raise ValidationError(
                {
                    "reservation": (
                        "Workshop issues and returns must "
                        "reference a stock reservation."
                    )
                }
            )

        if (
            self.reservation is not None
            and self.reservation.inventory_item != self.inventory_item
        ):
            raise ValidationError(
                {
                    "reservation": (
                        "The reservation belongs to a different inventory item."
                    )
                }
            )

        if (
            self.movement_type == StockMovementType.RETURN
            and self.source_movement is None
        ):
            raise ValidationError(
                {
                    "source_movement": (
                        "A stock return must reference its original issue."
                    )
                }
            )

        if self.source_movement is not None:
            if self.source_movement.movement_type != StockMovementType.ISSUE:
                raise ValidationError(
                    {
                        "source_movement": (
                            "Only a stock issue can be the source of a return."
                        )
                    }
                )

            if self.source_movement.inventory_item != self.inventory_item:
                raise ValidationError(
                    {
                        "source_movement": (
                            "The source issue belongs to a different inventory item."
                        )
                    }
                )

    def __str__(self) -> str:
        """Return the movement number and movement type."""

        return f"{self.movement_number} — {self.get_movement_type_display()}"
