"""Database models for quotation and approval workflows."""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.jobs.models import JobCard
from apps.product_catalogue.models import Product
from apps.quotations.constants import (
    CustomerDecisionMethod,
    QuotationStatus,
)
from apps.service_catalogue.models import Service

_MONEY_INCREMENT = Decimal("0.01")
_PERCENT_DIVISOR = Decimal("100")


def _money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""

    return value.quantize(
        _MONEY_INCREMENT,
        rounding=ROUND_HALF_UP,
    )


class Quotation(TimeStampedModel):
    """Represent one version of a quotation for a job card."""

    quotation_number = models.CharField(
        max_length=40,
        unique=True,
        editable=False,
    )
    job_card = models.ForeignKey(
        JobCard,
        on_delete=models.PROTECT,
        related_name="quotations",
    )
    revision_number = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=20,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
        db_index=True,
    )
    is_current = models.BooleanField(
        default=True,
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
    valid_until = models.DateField(
        null=True,
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
    decision_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    customer_decision_by_name = models.CharField(
        max_length=150,
        blank=True,
    )
    decision_method = models.CharField(
        max_length=30,
        choices=CustomerDecisionMethod.choices,
        blank=True,
    )
    decision_notes = models.TextField(
        blank=True,
    )
    decision_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quotation_decisions_recorded",
        null=True,
        blank=True,
        editable=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quotations_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quotations_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure quotation ordering and constraints."""

        ordering = (
            "-created_at",
            "-revision_number",
        )
        permissions = (
            (
                "submit_quotation",
                "Can submit quotation to customer",
            ),
            (
                "approve_quotation",
                "Can record quotation approval",
            ),
            (
                "reject_quotation",
                "Can record quotation rejection",
            ),
            (
                "revise_quotation",
                "Can create quotation revision",
            ),
        )
        indexes = (
            models.Index(
                fields=("job_card", "status"),
                name="quote_job_status_idx",
            ),
            models.Index(
                fields=("is_current", "status"),
                name="quote_current_status_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "job_card",
                    "revision_number",
                ),
                name="quote_unique_job_revision",
            ),
            models.UniqueConstraint(
                fields=("job_card",),
                condition=Q(is_current=True),
                name="quote_one_current_per_job",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discount_percentage__gte=0) & Q(discount_percentage__lte=100)
                ),
                name="quote_discount_range",
            ),
            models.CheckConstraint(
                condition=(Q(tax_percentage__gte=0) & Q(tax_percentage__lte=100)),
                name="quote_tax_range",
            ),
        )

    @property
    def service_subtotal(self) -> Decimal:
        """Return the total value of all service lines."""

        total = sum(
            (
                line.line_total
                for line in QuotationServiceLine.objects.filter(quotation=self)
            ),
            Decimal("0"),
        )

        return _money(total)

    @property
    def product_subtotal(self) -> Decimal:
        """Return the total value of all product lines."""

        total = sum(
            (
                line.line_total
                for line in QuotationProductLine.objects.filter(quotation=self)
            ),
            Decimal("0"),
        )

        return _money(total)

    @property
    def subtotal(self) -> Decimal:
        """Return the combined pre-discount subtotal."""

        return _money(self.service_subtotal + self.product_subtotal)

    @property
    def discount_amount(self) -> Decimal:
        """Return the quotation-level discount amount."""

        return _money(self.subtotal * self.discount_percentage / _PERCENT_DIVISOR)

    @property
    def taxable_amount(self) -> Decimal:
        """Return the amount remaining after discount."""

        return _money(self.subtotal - self.discount_amount)

    @property
    def tax_amount(self) -> Decimal:
        """Return tax calculated after applying the discount."""

        return _money(self.taxable_amount * self.tax_percentage / _PERCENT_DIVISOR)

    @property
    def total(self) -> Decimal:
        """Return the final quotation amount."""

        return _money(self.taxable_amount + self.tax_amount)

    def clean(self) -> None:
        """Validate currency, status, and decision consistency."""

        super().clean()

        self.currency = self.currency.strip().upper()
        self.notes = self.notes.strip()
        self.customer_decision_by_name = self.customer_decision_by_name.strip()
        self.decision_notes = self.decision_notes.strip()

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": ("Currency must be a three-letter code.")}
            )

        if self.status == QuotationStatus.DRAFT:
            if self.submitted_at is not None:
                raise ValidationError(
                    {
                        "submitted_at": (
                            "A draft quotation cannot have a submission time."
                        )
                    }
                )

        if (
            self.status
            in {
                QuotationStatus.SENT,
                QuotationStatus.APPROVED,
                QuotationStatus.REJECTED,
                QuotationStatus.SUPERSEDED,
            }
            and self.submitted_at is None
        ):
            raise ValidationError(
                {"submitted_at": ("A submitted quotation requires a submission time.")}
            )

        if self.status == QuotationStatus.SUPERSEDED and self.is_current:
            raise ValidationError(
                {"is_current": ("A superseded quotation cannot be current.")}
            )

        decision_statuses = {
            QuotationStatus.APPROVED,
            QuotationStatus.REJECTED,
        }

        if self.status in decision_statuses:
            if self.decision_at is None:
                raise ValidationError(
                    {"decision_at": ("A customer decision time is required.")}
                )

            if self.decision_recorded_by is None:
                raise ValidationError(
                    {
                        "decision_recorded_by": (
                            "The employee recording the decision is required."
                        )
                    }
                )

            if not self.customer_decision_by_name:
                raise ValidationError(
                    {
                        "customer_decision_by_name": (
                            "Enter the name of the customer "
                            "representative making the decision."
                        )
                    }
                )

            if not self.decision_method:
                raise ValidationError(
                    {
                        "decision_method": (
                            "Record how the customer communicated their decision."
                        )
                    }
                )

            if self.status == QuotationStatus.REJECTED and not self.decision_notes:
                raise ValidationError(
                    {"decision_notes": ("A rejection reason is required.")}
                )
        elif any(
            (
                self.decision_at,
                self.customer_decision_by_name,
                self.decision_method,
                self.decision_notes,
                self.decision_recorded_by,
            )
        ):
            raise ValidationError(
                {
                    "status": (
                        "Decision information is only valid for "
                        "approved or rejected quotations."
                    )
                }
            )

    def __str__(self) -> str:
        """Return quotation number and job number."""

        return f"{self.quotation_number} — {self.job_card.job_number}"


class QuotationServiceLine(TimeStampedModel):
    """Preserve a service definition and price snapshot."""

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="service_lines",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="quotation_lines",
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
        default=Decimal("1.00"),
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quotation_service_lines_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure service-line ordering and constraints."""

        ordering = ("position", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("quotation", "service"),
                name="quote_unique_service_line",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="quote_service_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="quote_service_price_positive",
            ),
        )

    @property
    def line_total(self) -> Decimal:
        """Return quantity multiplied by the price snapshot."""

        return _money(self.quantity * self.unit_price)

    def clean(self) -> None:
        """Allow changes only on the current draft revision."""

        super().clean()

        self.description_snapshot = self.description_snapshot.strip()

        try:
            quotation = self.quotation
        except ObjectDoesNotExist:
            return

        if quotation.status != QuotationStatus.DRAFT or not quotation.is_current:
            raise ValidationError(
                {
                    "quotation": (
                        "Lines can only be changed on the current draft quotation."
                    )
                }
            )

    def __str__(self) -> str:
        """Return quotation and service description."""

        return f"{self.quotation.quotation_number} — {self.service_name_snapshot}"


class QuotationProductLine(TimeStampedModel):
    """Preserve a product definition and price snapshot."""

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="product_lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="quotation_lines",
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
        default=Decimal("1.000"),
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quotation_product_lines_created",
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure product-line ordering and constraints."""

        ordering = ("position", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("quotation", "product"),
                name="quote_unique_product_line",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="quote_product_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gt=0),
                name="quote_product_price_positive",
            ),
        )

    @property
    def line_total(self) -> Decimal:
        """Return quantity multiplied by the price snapshot."""

        return _money(self.quantity * self.unit_price)

    def clean(self) -> None:
        """Allow changes only on the current draft revision."""

        super().clean()

        self.description_snapshot = self.description_snapshot.strip()

        try:
            quotation = self.quotation
        except ObjectDoesNotExist:
            return

        if quotation.status != QuotationStatus.DRAFT or not quotation.is_current:
            raise ValidationError(
                {
                    "quotation": (
                        "Lines can only be changed on the current draft quotation."
                    )
                }
            )

    def __str__(self) -> str:
        """Return quotation and product description."""

        return f"{self.quotation.quotation_number} — {self.product_name_snapshot}"
