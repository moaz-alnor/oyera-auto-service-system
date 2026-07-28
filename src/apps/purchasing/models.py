"""Database models for supplier purchasing."""

from collections.abc import Collection
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.inventory.constants import StockMovementType
from apps.inventory.models import (
    InventoryItem,
    StockMovement,
)
from apps.product_catalogue.models import Product
from apps.purchasing.calculations import (
    PurchaseOrderTotals,
    calculate_line_total,
    calculate_purchase_order_totals,
)
from apps.purchasing.constants import (
    PurchaseOrderStatus,
)
from apps.purchasing.normalization import (
    normalize_contact_value,
    normalize_supplier_code,
    normalize_supplier_name,
)


class Supplier(TimeStampedModel):
    """Represent a business supplying products or services."""

    supplier_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    code = models.CharField(
        max_length=30,
    )
    normalized_code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
    )
    normalized_name = models.CharField(
        max_length=200,
        db_index=True,
        editable=False,
    )
    contact_name = models.CharField(
        max_length=200,
        blank=True,
    )
    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )
    email = models.EmailField(
        blank=True,
    )
    address = models.TextField(
        blank=True,
    )
    tax_identifier = models.CharField(
        max_length=80,
        blank=True,
    )
    payment_terms_days = models.PositiveIntegerField(
        default=0,
    )
    preferred_currency = models.CharField(
        max_length=3,
        default="UGX",
    )
    notes = models.TextField(
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="suppliers_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="suppliers_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure supplier ordering and permissions."""

        ordering = (
            "name",
            "supplier_number",
        )
        permissions = (
            (
                "deactivate_supplier",
                "Can deactivate supplier",
            ),
            (
                "reactivate_supplier",
                "Can reactivate supplier",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "is_active",
                    "name",
                ),
                name="purch_supplier_active_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(payment_terms_days__gte=0),
                name="purch_supplier_terms_nonnegative",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalise supplier data before field validation."""

        excluded_fields = set(exclude or ())

        if "code" not in excluded_fields:
            self.code = normalize_supplier_code(self.code)
            self.normalized_code = self.code

        if "name" not in excluded_fields:
            self.name = " ".join(self.name.strip().split())
            self.normalized_name = normalize_supplier_name(self.name)

        if "contact_name" not in excluded_fields:
            self.contact_name = normalize_contact_value(self.contact_name)

        if "phone_number" not in excluded_fields:
            self.phone_number = normalize_contact_value(self.phone_number)

        if "email" not in excluded_fields:
            self.email = normalize_contact_value(self.email).casefold()

        if "address" not in excluded_fields:
            self.address = normalize_contact_value(self.address)

        if "tax_identifier" not in excluded_fields:
            self.tax_identifier = normalize_contact_value(self.tax_identifier).upper()

        if "preferred_currency" not in excluded_fields:
            self.preferred_currency = normalize_contact_value(
                self.preferred_currency
            ).upper()

        if "notes" not in excluded_fields:
            self.notes = normalize_contact_value(self.notes)

        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        """Validate supplier identity and payment settings."""

        super().clean()

        errors: dict[str, str] = {}

        if not self.normalized_code:
            errors["code"] = "Enter a valid supplier code."

        if not self.normalized_name:
            errors["name"] = "Enter a supplier name."

        if len(self.preferred_currency) != 3:
            errors["preferred_currency"] = "Currency must use a three-letter code."

        if self.payment_terms_days < 0:
            errors["payment_terms_days"] = "Payment terms cannot be negative."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        """Return the supplier number and name."""

        if self.supplier_number:
            return f"{self.supplier_number} — {self.name}"

        return f"{self.code} — {self.name}"


class PurchaseOrder(TimeStampedModel):
    """Represent an order placed with one supplier."""

    if TYPE_CHECKING:
        supplier_id: int
        submitted_by_id: int | None
        approved_by_id: int | None
        cancelled_by_id: int | None
        lines: models.Manager["PurchaseOrderLine"]

    purchase_order_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    supplier_number_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )
    supplier_code_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    supplier_name_snapshot = models.CharField(
        max_length=200,
        editable=False,
    )

    status = models.CharField(
        max_length=30,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        default="UGX",
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    delivery_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
    )
    supplier_reference = models.CharField(
        max_length=80,
        blank=True,
    )
    notes = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_submitted",
        null=True,
        blank=True,
        editable=False,
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_approved",
        null=True,
        blank=True,
        editable=False,
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_cancelled",
        null=True,
        blank=True,
        editable=False,
    )
    cancellation_reason = models.TextField(
        blank=True,
        editable=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure purchase-order behaviour and permissions."""

        ordering = (
            "-created_at",
            "-pk",
        )
        permissions = (
            (
                "submit_purchase_order",
                "Can submit purchase order for approval",
            ),
            (
                "approve_purchase_order",
                "Can approve purchase order",
            ),
            (
                "cancel_purchase_order",
                "Can cancel purchase order",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "supplier",
                    "status",
                ),
                name="purch_order_supplier_idx",
            ),
            models.Index(
                fields=(
                    "status",
                    "expected_delivery_date",
                ),
                name="purch_order_status_date_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=(
                    Q(discount_percentage__gte=0) & Q(discount_percentage__lte=100)
                ),
                name="purch_order_discount_range",
            ),
            models.CheckConstraint(
                condition=(Q(tax_percentage__gte=0) & Q(tax_percentage__lte=100)),
                name="purch_order_tax_range",
            ),
            models.CheckConstraint(
                condition=Q(delivery_cost__gte=0),
                name="purch_order_delivery_nonnegative",
            ),
        )

    def clean(self) -> None:
        """Validate financial and lifecycle consistency."""

        super().clean()

        self.currency = self.currency.strip().upper()
        self.supplier_reference = self.supplier_reference.strip()
        self.notes = self.notes.strip()
        self.cancellation_reason = self.cancellation_reason.strip()

        errors: dict[str, str] = {}

        if len(self.currency) != 3 or not self.currency.isalpha():
            errors["currency"] = "Currency must be a three-letter code."

        if not (Decimal("0.00") <= self.discount_percentage <= Decimal("100.00")):
            errors["discount_percentage"] = (
                "Discount percentage must be between 0 and 100."
            )

        if not (Decimal("0.00") <= self.tax_percentage <= Decimal("100.00")):
            errors["tax_percentage"] = "Tax percentage must be between 0 and 100."

        if self.delivery_cost < Decimal("0.00"):
            errors["delivery_cost"] = "Delivery cost cannot be negative."

        try:
            supplier = self.supplier
        except ObjectDoesNotExist:
            supplier = None

        if (
            supplier is not None
            and self.status
            in {
                PurchaseOrderStatus.DRAFT,
                PurchaseOrderStatus.SUBMITTED,
            }
            and not supplier.is_active
        ):
            errors["supplier"] = (
                "A draft or submitted purchase order requires an active supplier."
            )

        if self.status == PurchaseOrderStatus.DRAFT:
            if any(
                (
                    self.submitted_at,
                    self.submitted_by_id,
                    self.approved_at,
                    self.approved_by_id,
                    self.cancelled_at,
                    self.cancelled_by_id,
                    self.cancellation_reason,
                )
            ):
                errors["status"] = (
                    "A draft purchase order cannot contain "
                    "submission, approval, or cancellation data."
                )

        if self.status == PurchaseOrderStatus.SUBMITTED:
            if self.submitted_at is None or self.submitted_by_id is None:
                errors["submitted_at"] = (
                    "A submitted purchase order requires submission metadata."
                )

            if any(
                (
                    self.approved_at,
                    self.approved_by_id,
                    self.cancelled_at,
                    self.cancelled_by_id,
                    self.cancellation_reason,
                )
            ):
                errors["status"] = (
                    "A submitted purchase order cannot "
                    "contain approval or cancellation data."
                )

        approved_statuses = {
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
            PurchaseOrderStatus.RECEIVED,
        }

        if self.status in approved_statuses:
            if self.submitted_at is None or self.submitted_by_id is None:
                errors["submitted_at"] = (
                    "An approved purchase order requires submission metadata."
                )

            if self.approved_at is None or self.approved_by_id is None:
                errors["approved_at"] = (
                    "An approved purchase order requires approval metadata."
                )

            if any(
                (
                    self.cancelled_at,
                    self.cancelled_by_id,
                    self.cancellation_reason,
                )
            ):
                errors["status"] = (
                    "An active approved purchase order "
                    "cannot contain cancellation data."
                )

        if self.status == PurchaseOrderStatus.CANCELLED:
            if (
                self.cancelled_at is None
                or self.cancelled_by_id is None
                or not self.cancellation_reason
            ):
                errors["cancellation_reason"] = (
                    "A cancelled purchase order requires "
                    "the cancellation actor, time, and reason."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def totals(self) -> PurchaseOrderTotals:
        """Return calculated totals from all order lines."""

        return calculate_purchase_order_totals(
            line_totals=(line.line_total for line in self.lines.all()),
            discount_percentage=(self.discount_percentage),
            tax_percentage=self.tax_percentage,
            delivery_cost=self.delivery_cost,
        )

    def __str__(self) -> str:
        """Return purchase-order and supplier details."""

        return f"{self.purchase_order_number} — {self.supplier_name_snapshot}"


class PurchaseOrderLine(TimeStampedModel):
    """Preserve one ordered product and supplier cost."""

    if TYPE_CHECKING:
        purchase_order_id: int
        product_id: int
        receipt_lines: models.Manager["GoodsReceiptLine"]

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )
    position = models.PositiveSmallIntegerField()

    product_sku_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )
    product_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )
    unit_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )
    description_snapshot = models.TextField(
        blank=True,
        editable=False,
    )

    quantity_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure line ordering and constraints."""

        ordering = (
            "position",
            "pk",
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "purchase_order",
                    "product",
                ),
                name="purch_order_unique_product",
            ),
            models.UniqueConstraint(
                fields=(
                    "purchase_order",
                    "position",
                ),
                name="purch_order_unique_position",
            ),
            models.CheckConstraint(
                condition=Q(quantity_ordered__gt=0),
                name="purch_order_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_cost__gt=0),
                name="purch_order_unit_cost_positive",
            ),
        )

    @property
    def line_total(self) -> Decimal:
        """Return quantity multiplied by supplier cost."""

        return calculate_line_total(
            quantity=self.quantity_ordered,
            unit_cost=self.unit_cost,
        )

    @property
    def quantity_received(self) -> Decimal:
        """Return the total quantity received for this line."""

        return self.receipt_lines.aggregate(total=Sum("quantity_received"))[
            "total"
        ] or Decimal("0.000")

    @property
    def remaining_quantity(self) -> Decimal:
        """Return the quantity still awaiting delivery."""

        remaining = self.quantity_ordered - self.quantity_received

        return max(
            remaining,
            Decimal("0.000"),
        )

    def clean(self) -> None:
        """Allow line changes only on draft orders."""

        super().clean()

        self.product_sku_snapshot = self.product_sku_snapshot.strip().upper()
        self.product_name_snapshot = " ".join(
            self.product_name_snapshot.strip().split()
        )
        self.unit_snapshot = self.unit_snapshot.strip().upper()
        self.description_snapshot = self.description_snapshot.strip()

        errors: dict[str, str] = {}

        if self.quantity_ordered <= Decimal("0.000"):
            errors["quantity_ordered"] = "Ordered quantity must be greater than zero."

        if self.unit_cost <= Decimal("0.00"):
            errors["unit_cost"] = "Supplier unit cost must be greater than zero."

        try:
            purchase_order = self.purchase_order
        except ObjectDoesNotExist:
            purchase_order = None

        if (
            purchase_order is not None
            and purchase_order.status != PurchaseOrderStatus.DRAFT
        ):
            errors["purchase_order"] = (
                "Lines can only be changed on a draft purchase order."
            )

        try:
            product = self.product
        except ObjectDoesNotExist:
            product = None

        if product is not None and not product.is_active:
            errors["product"] = (
                "An inactive product cannot be added to a purchase order."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        """Return order and product description."""

        return (
            f"{self.purchase_order.purchase_order_number} — "
            f"{self.product_name_snapshot}"
        )


class GoodsReceipt(TimeStampedModel):
    """Record one posted supplier delivery."""

    if TYPE_CHECKING:
        purchase_order_id: int
        received_by_id: int
        lines: models.Manager["GoodsReceiptLine"]

    goods_receipt_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="goods_receipts",
    )

    purchase_order_number_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    supplier_number_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )
    supplier_name_snapshot = models.CharField(
        max_length=200,
        editable=False,
    )

    supplier_delivery_reference = models.CharField(
        max_length=120,
        blank=True,
    )
    received_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="goods_receipts_received",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure receipt ordering and permissions."""

        ordering = (
            "-received_at",
            "-pk",
        )
        permissions = (
            (
                "receive_purchase_order",
                "Can receive an approved purchase order",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "purchase_order",
                    "received_at",
                ),
                name="purch_receipt_order_time_idx",
            ),
        )

    def clean(self) -> None:
        """Validate receipt identity and purchase-order state."""

        super().clean()

        self.goods_receipt_number = self.goods_receipt_number.strip().upper()
        self.purchase_order_number_snapshot = (
            self.purchase_order_number_snapshot.strip().upper()
        )
        self.supplier_number_snapshot = self.supplier_number_snapshot.strip().upper()
        self.supplier_name_snapshot = " ".join(
            self.supplier_name_snapshot.strip().split()
        )
        self.supplier_delivery_reference = self.supplier_delivery_reference.strip()
        self.notes = self.notes.strip()

        errors: dict[str, str] = {}

        try:
            purchase_order = self.purchase_order
        except ObjectDoesNotExist:
            purchase_order = None

        receivable_statuses = {
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
            PurchaseOrderStatus.RECEIVED,
        }

        if (
            purchase_order is not None
            and purchase_order.status not in receivable_statuses
        ):
            errors["purchase_order"] = (
                "Goods receipts require an approved purchase order."
            )

        if not self.goods_receipt_number:
            errors["goods_receipt_number"] = "A goods-receipt number is required."

        if not self.purchase_order_number_snapshot:
            errors["purchase_order_number_snapshot"] = (
                "The purchase-order number snapshot is required."
            )

        if not self.supplier_name_snapshot:
            errors["supplier_name_snapshot"] = "The supplier name snapshot is required."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        """Return receipt and purchase-order identity."""

        return f"{self.goods_receipt_number} — {self.purchase_order_number_snapshot}"


class GoodsReceiptLine(TimeStampedModel):
    """Connect received goods to inventory movements."""

    if TYPE_CHECKING:
        goods_receipt_id: int
        purchase_order_line_id: int
        inventory_item_id: int
        stock_movement_id: int
        created_by_id: int

    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine,
        on_delete=models.PROTECT,
        related_name="receipt_lines",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="purchase_receipt_lines",
    )
    stock_movement = models.OneToOneField(
        StockMovement,
        on_delete=models.PROTECT,
        related_name="goods_receipt_line",
    )

    product_sku_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )
    product_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )
    unit_snapshot = models.CharField(
        max_length=20,
        editable=False,
    )

    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    unit_cost_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    currency_snapshot = models.CharField(
        max_length=3,
        editable=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="goods_receipt_lines_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure receipt-line integrity."""

        ordering = (
            "purchase_order_line__position",
            "pk",
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "goods_receipt",
                    "purchase_order_line",
                ),
                name="purch_receipt_unique_order_line",
            ),
            models.CheckConstraint(
                condition=Q(quantity_received__gt=0),
                name="purch_receipt_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_cost_snapshot__gt=0),
                name="purch_receipt_cost_positive",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "purchase_order_line",
                    "created_at",
                ),
                name="purch_receipt_line_time_idx",
            ),
        )

    def clean(self) -> None:
        """Validate receipt, product and movement alignment."""

        super().clean()

        self.product_sku_snapshot = self.product_sku_snapshot.strip().upper()
        self.product_name_snapshot = " ".join(
            self.product_name_snapshot.strip().split()
        )
        self.unit_snapshot = self.unit_snapshot.strip().upper()
        self.currency_snapshot = self.currency_snapshot.strip().upper()

        errors: dict[str, str] = {}

        if self.quantity_received <= Decimal("0.000"):
            errors["quantity_received"] = "Received quantity must be greater than zero."

        if self.unit_cost_snapshot <= Decimal("0.00"):
            errors["unit_cost_snapshot"] = (
                "Received unit cost must be greater than zero."
            )

        if len(self.currency_snapshot) != 3 or not self.currency_snapshot.isalpha():
            errors["currency_snapshot"] = "Currency must be a three-letter code."

        try:
            receipt = self.goods_receipt
        except ObjectDoesNotExist:
            receipt = None

        try:
            order_line = self.purchase_order_line
        except ObjectDoesNotExist:
            order_line = None

        try:
            inventory_item = self.inventory_item
        except ObjectDoesNotExist:
            inventory_item = None

        try:
            movement = self.stock_movement
        except ObjectDoesNotExist:
            movement = None

        if (
            receipt is not None
            and order_line is not None
            and order_line.purchase_order_id != receipt.purchase_order_id
        ):
            errors["purchase_order_line"] = (
                "The received line belongs to a different purchase order."
            )

        if (
            order_line is not None
            and inventory_item is not None
            and order_line.product.pk != inventory_item.product.pk
        ):
            errors["inventory_item"] = (
                "The inventory product must match the ordered product."
            )

        if (
            order_line is not None
            and self.quantity_received > order_line.quantity_ordered
        ):
            errors["quantity_received"] = (
                "A receipt line cannot exceed the original ordered quantity."
            )

        if movement is not None:
            if movement.movement_type != StockMovementType.RECEIPT:
                errors["stock_movement"] = (
                    "A goods receipt must reference an inventory receipt movement."
                )

            if (
                inventory_item is not None
                and movement.inventory_item.pk != inventory_item.pk
            ):
                errors["stock_movement"] = (
                    "The stock movement belongs to a different inventory item."
                )

            if movement.quantity != self.quantity_received:
                errors["stock_movement"] = (
                    "The stock movement quantity must match the goods-receipt quantity."
                )

            if movement.unit_cost != self.unit_cost_snapshot:
                errors["stock_movement"] = (
                    "The stock movement cost must match the purchase-order cost."
                )

            if movement.currency != self.currency_snapshot:
                errors["stock_movement"] = (
                    "The stock movement currency must match the purchase order."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        """Return receipt and product identity."""

        return (
            f"{self.goods_receipt.goods_receipt_number} — {self.product_name_snapshot}"
        )
