"""Database models for invoices and customer payments."""

from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.billing.calculations import calculate_line_total
from apps.billing.constants import (
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
)
from apps.core.models import TimeStampedModel
from apps.workshop.models import (
    WorkOrder,
    WorkProductRequirement,
    WorkTask,
)


class Invoice(TimeStampedModel):
    """Represent the final customer invoice for one work order."""

    if TYPE_CHECKING:
        work_order_id: int
        service_lines: models.Manager["InvoiceServiceLine"]
        product_lines: models.Manager["InvoiceProductLine"]
        payments: models.Manager["Payment"]

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="invoice",
    )
    status = models.CharField(
        max_length=30,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        default="UGX",
    )

    # Historical workflow snapshots.
    work_order_number_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    job_number_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    quotation_number_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )

    # Historical customer snapshots.
    customer_name_snapshot = models.CharField(
        max_length=200,
        editable=False,
    )
    customer_phone_snapshot = models.CharField(
        max_length=30,
        blank=True,
        editable=False,
    )
    customer_email_snapshot = models.EmailField(
        blank=True,
        editable=False,
    )

    # Historical vehicle snapshots.
    vehicle_registration_snapshot = models.CharField(
        max_length=40,
        editable=False,
    )
    vehicle_make_snapshot = models.CharField(
        max_length=100,
        editable=False,
    )
    vehicle_model_snapshot = models.CharField(
        max_length=100,
        editable=False,
    )
    vehicle_year_snapshot = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        editable=False,
    )
    vehicle_color_snapshot = models.CharField(
        max_length=50,
        blank=True,
        editable=False,
    )

    # Frozen invoice totals.
    service_subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    product_subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    taxable_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    issued_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    due_date = models.DateField(
        null=True,
        blank=True,
    )
    notes = models.TextField(
        blank=True,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_voided",
        null=True,
        blank=True,
        editable=False,
    )
    void_reason = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure invoice ordering and constraints."""

        ordering = (
            "-created_at",
            "-pk",
        )
        permissions = (
            (
                "issue_invoice",
                "Can issue an invoice",
            ),
            (
                "void_invoice",
                "Can void an invoice",
            ),
        )
        indexes = (
            models.Index(
                fields=("status", "created_at"),
                name="bill_invoice_status_idx",
            ),
            models.Index(
                fields=("due_date", "status"),
                name="bill_invoice_due_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=(
                    Q(discount_percentage__gte=0) & Q(discount_percentage__lte=100)
                ),
                name="bill_invoice_discount_range",
            ),
            models.CheckConstraint(
                condition=(Q(tax_percentage__gte=0) & Q(tax_percentage__lte=100)),
                name="bill_invoice_tax_range",
            ),
            models.CheckConstraint(
                condition=Q(service_subtotal__gte=0),
                name="bill_service_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(product_subtotal__gte=0),
                name="bill_product_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="bill_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=0),
                name="bill_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(taxable_amount__gte=0),
                name="bill_taxable_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=0),
                name="bill_tax_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="bill_total_nonnegative",
            ),
        )

    def clean(self) -> None:
        """Validate snapshots, totals, currency, and lifecycle state."""

        super().clean()

        self.currency = self.currency.strip().upper()
        self.notes = self.notes.strip()
        self.void_reason = self.void_reason.strip()

        self.work_order_number_snapshot = self.work_order_number_snapshot.strip()
        self.job_number_snapshot = self.job_number_snapshot.strip()
        self.quotation_number_snapshot = self.quotation_number_snapshot.strip()
        self.customer_name_snapshot = self.customer_name_snapshot.strip()
        self.customer_phone_snapshot = self.customer_phone_snapshot.strip()
        self.customer_email_snapshot = self.customer_email_snapshot.strip().lower()
        self.vehicle_registration_snapshot = (
            self.vehicle_registration_snapshot.strip().upper()
        )
        self.vehicle_make_snapshot = self.vehicle_make_snapshot.strip()
        self.vehicle_model_snapshot = self.vehicle_model_snapshot.strip()
        self.vehicle_color_snapshot = self.vehicle_color_snapshot.strip()

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": ("Currency must be a three-letter code.")}
            )

        expected_subtotal = self.service_subtotal + self.product_subtotal

        if self.subtotal != expected_subtotal:
            raise ValidationError(
                {
                    "subtotal": (
                        "Invoice subtotal must equal service "
                        "subtotal plus product subtotal."
                    )
                }
            )

        expected_taxable_amount = self.subtotal - self.discount_amount

        if self.taxable_amount != expected_taxable_amount:
            raise ValidationError(
                {
                    "taxable_amount": (
                        "Taxable amount must equal subtotal minus discount."
                    )
                }
            )

        expected_total = self.taxable_amount + self.tax_amount

        if self.total != expected_total:
            raise ValidationError(
                {"total": ("Invoice total must equal taxable amount plus tax.")}
            )

        if self.discount_amount > self.subtotal:
            raise ValidationError(
                {"discount_amount": ("Discount cannot exceed the invoice subtotal.")}
            )

        if self.status == InvoiceStatus.DRAFT:
            if self.issued_at is not None:
                raise ValidationError(
                    {"issued_at": ("A draft invoice cannot have an issue time.")}
                )

            if self.due_date is not None:
                raise ValidationError(
                    {"due_date": ("A draft invoice cannot have a payment due date.")}
                )
        else:
            issue_metadata_errors: dict[str, str] = {}

            if self.issued_at is None:
                issue_metadata_errors["issued_at"] = (
                    "A non-draft invoice requires an issue time."
                )

            if self.due_date is None:
                issue_metadata_errors["due_date"] = (
                    "A non-draft invoice requires a payment due date."
                )

            if issue_metadata_errors:
                raise ValidationError(issue_metadata_errors)

        if (
            self.issued_at is not None
            and self.due_date is not None
            and self.due_date < self.issued_at.date()
        ):
            raise ValidationError(
                {
                    "due_date": (
                        "Payment due date cannot be earlier "
                        "than the invoice issue date."
                    )
                }
            )

        if self.status == InvoiceStatus.VOIDED:
            if self.voided_at is None:
                raise ValidationError(
                    {"voided_at": ("A voided invoice requires a void time.")}
                )

            if self.voided_by is None:
                raise ValidationError(
                    {
                        "voided_by": (
                            "A voided invoice requires the employee who voided it."
                        )
                    }
                )

            if not self.void_reason:
                raise ValidationError(
                    {"void_reason": ("Record why the invoice was voided.")}
                )
        elif any(
            (
                self.voided_at,
                self.voided_by,
                self.void_reason,
            )
        ):
            raise ValidationError(
                {"status": ("Void information is only valid for a voided invoice.")}
            )

        try:
            work_order = self.work_order
        except ObjectDoesNotExist:
            return

        if self.currency != work_order.approved_quotation.currency:
            raise ValidationError(
                {"currency": ("Invoice currency must match the approved quotation.")}
            )

    def __str__(self) -> str:
        """Return invoice and work-order numbers."""

        return f"{self.invoice_number} — {self.work_order_number_snapshot}"


class InvoiceServiceLine(TimeStampedModel):
    """Preserve one invoiced workshop service snapshot."""

    if TYPE_CHECKING:
        invoice_id: int
        source_work_task_id: int

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="service_lines",
    )
    source_work_task = models.OneToOneField(
        WorkTask,
        on_delete=models.PROTECT,
        related_name="invoice_service_line",
    )
    position = models.PositiveSmallIntegerField()
    service_code_snapshot = models.CharField(
        max_length=30,
        editable=False,
    )
    service_name_snapshot = models.CharField(
        max_length=150,
        editable=False,
    )
    description_snapshot = models.TextField(
        blank=True,
        editable=False,
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoice_service_lines_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure invoice service lines."""

        ordering = (
            "position",
            "pk",
        )
        constraints = (
            models.UniqueConstraint(
                fields=("invoice", "position"),
                name="bill_unique_service_position",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="bill_service_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="bill_service_price_positive",
            ),
        )

    @property
    def line_total(self) -> Decimal:
        """Return quantity multiplied by frozen unit price."""

        return calculate_line_total(
            quantity=self.quantity,
            unit_price=self.unit_price,
        )

    def clean(self) -> None:
        """Validate the service origin and invoice relationship."""

        super().clean()

        self.service_code_snapshot = self.service_code_snapshot.strip().upper()
        self.service_name_snapshot = self.service_name_snapshot.strip()
        self.description_snapshot = self.description_snapshot.strip()

        try:
            invoice = self.invoice
            task = self.source_work_task
        except ObjectDoesNotExist:
            return

        if task.work_order_id != invoice.work_order_id:
            raise ValidationError(
                {
                    "source_work_task": (
                        "The service task must belong to the invoice work order."
                    )
                }
            )

    def __str__(self) -> str:
        """Return invoice and service description."""

        return f"{self.invoice.invoice_number} — {self.service_name_snapshot}"


class InvoiceProductLine(TimeStampedModel):
    """Preserve one invoiced product-consumption snapshot."""

    if TYPE_CHECKING:
        invoice_id: int
        source_product_requirement_id: int

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="product_lines",
    )
    source_product_requirement = models.OneToOneField(
        WorkProductRequirement,
        on_delete=models.PROTECT,
        related_name="invoice_product_line",
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
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoice_product_lines_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure invoice product lines."""

        ordering = (
            "position",
            "pk",
        )
        constraints = (
            models.UniqueConstraint(
                fields=("invoice", "position"),
                name="bill_unique_product_position",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="bill_product_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="bill_product_price_positive",
            ),
        )

    @property
    def line_total(self) -> Decimal:
        """Return consumed quantity multiplied by frozen price."""

        return calculate_line_total(
            quantity=self.quantity,
            unit_price=self.unit_price,
        )

    def clean(self) -> None:
        """Validate product origin and invoice relationship."""

        super().clean()

        self.product_sku_snapshot = self.product_sku_snapshot.strip().upper()
        self.product_name_snapshot = self.product_name_snapshot.strip()
        self.unit_snapshot = self.unit_snapshot.strip()
        self.description_snapshot = self.description_snapshot.strip()

        try:
            invoice = self.invoice
            requirement = self.source_product_requirement
        except ObjectDoesNotExist:
            return

        if requirement.work_order_id != invoice.work_order_id:
            raise ValidationError(
                {
                    "source_product_requirement": (
                        "The product requirement must belong to the invoice work order."
                    )
                }
            )

    def __str__(self) -> str:
        """Return invoice and product description."""

        return f"{self.invoice.invoice_number} — {self.product_name_snapshot}"


class Payment(TimeStampedModel):
    """Represent an append-only payment against an invoice."""

    if TYPE_CHECKING:
        invoice_id: int

    payment_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.POSTED,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    currency = models.CharField(
        max_length=3,
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
    )
    external_reference = models.CharField(
        max_length=100,
        blank=True,
    )
    paid_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_received",
        editable=False,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments_voided",
        null=True,
        blank=True,
        editable=False,
    )
    void_reason = models.TextField(
        blank=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure payment ordering, permissions, and constraints."""

        ordering = (
            "-paid_at",
            "-pk",
        )
        permissions = (
            (
                "record_payment",
                "Can record an invoice payment",
            ),
            (
                "void_payment",
                "Can void an invoice payment",
            ),
        )
        indexes = (
            models.Index(
                fields=("invoice", "status"),
                name="bill_payment_invoice_idx",
            ),
            models.Index(
                fields=("status", "paid_at"),
                name="bill_payment_status_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="bill_payment_amount_positive",
            ),
        )

    def clean(self) -> None:
        """Validate payment currency and voiding consistency."""

        super().clean()

        self.currency = self.currency.strip().upper()
        self.external_reference = self.external_reference.strip()
        self.notes = self.notes.strip()
        self.void_reason = self.void_reason.strip()

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": ("Currency must be a three-letter code.")}
            )

        try:
            invoice = self.invoice
        except ObjectDoesNotExist:
            return

        if self.currency != invoice.currency:
            raise ValidationError(
                {"currency": ("Payment currency must match the invoice currency.")}
            )

        if invoice.status == InvoiceStatus.VOIDED:
            raise ValidationError(
                {"invoice": ("Payments cannot be attached to a voided invoice.")}
            )

        if self.status == PaymentStatus.VOIDED:
            if self.voided_at is None:
                raise ValidationError(
                    {"voided_at": ("A voided payment requires a void time.")}
                )

            if self.voided_by is None:
                raise ValidationError(
                    {
                        "voided_by": (
                            "A voided payment requires the employee who voided it."
                        )
                    }
                )

            if not self.void_reason:
                raise ValidationError(
                    {"void_reason": ("Record why the payment was voided.")}
                )
        elif any(
            (
                self.voided_at,
                self.voided_by,
                self.void_reason,
            )
        ):
            raise ValidationError(
                {"status": ("Void information is only valid for a voided payment.")}
            )

    def __str__(self) -> str:
        """Return payment and invoice numbers."""

        return f"{self.payment_number} — {self.invoice.invoice_number}"
