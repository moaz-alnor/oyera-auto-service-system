"""Database models for the service catalogue."""

from collections.abc import Collection
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.service_catalogue.normalization import (
    normalize_service_code_display,
    normalize_service_code_key,
    normalize_service_name,
)
from apps.vehicles.constants import VehicleCategory


class Service(TimeStampedModel):
    """Represent a service offered by the auto-service business."""

    code = models.CharField(
        max_length=30,
    )
    normalized_code = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )
    name = models.CharField(
        max_length=150,
        db_index=True,
    )
    description = models.TextField(
        blank=True,
    )
    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="catalogue_services_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="catalogue_services_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure service ordering and business permissions."""

        ordering = (
            "name",
            "code",
        )
        permissions = (
            (
                "change_service_price",
                "Can change service price",
            ),
            (
                "deactivate_service",
                "Can deactivate service",
            ),
            (
                "reactivate_service",
                "Can reactivate service",
            ),
        )
        indexes = (
            models.Index(
                fields=("is_active", "name"),
                name="svc_active_name_idx",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalize service fields before Django validates them.

        Args:
            exclude: Field names Django should exclude from validation.
        """

        excluded_fields = set(exclude or ())

        if "code" not in excluded_fields:
            self.code = normalize_service_code_display(self.code)
            self.normalized_code = normalize_service_code_key(self.code)

        if "name" not in excluded_fields:
            self.name = normalize_service_name(self.name)

        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        """Validate service business information."""

        super().clean()

        if (
            self.estimated_duration_minutes is not None
            and self.estimated_duration_minutes == 0
        ):
            raise ValidationError(
                {
                    "estimated_duration_minutes": (
                        "Estimated duration must be greater than zero."
                    )
                }
            )

    def __str__(self) -> str:
        """Return the code and service name."""

        return f"{self.code} — {self.name}"


class ServiceApplicability(TimeStampedModel):
    """Identify a vehicle category supported by a service."""

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="applicabilities",
    )
    vehicle_category = models.CharField(
        max_length=20,
        choices=VehicleCategory.choices,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure service applicability constraints."""

        ordering = (
            "service",
            "vehicle_category",
        )
        constraints = (
            models.UniqueConstraint(
                fields=(
                    "service",
                    "vehicle_category",
                ),
                name="svc_unique_category",
            ),
        )
        indexes = (
            models.Index(
                fields=(
                    "vehicle_category",
                    "service",
                ),
                name="svc_category_idx",
            ),
        )

    def __str__(self) -> str:
        """Return the service and supported vehicle category."""

        category_label = VehicleCategory(self.vehicle_category).label

        return f"{self.service.code} — {category_label}"


class ServicePrice(TimeStampedModel):
    """Preserve a historical service-price period."""

    service = models.ForeignKey(
        Service,
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
        related_name="service_price_changes",
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure service-price ordering and constraints."""

        ordering = (
            "-effective_from",
            "-created_at",
        )
        constraints = (
            models.UniqueConstraint(
                fields=("service",),
                condition=Q(effective_until__isnull=True),
                name="svc_one_current_price",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="svc_price_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(effective_until__isnull=True)
                    | Q(effective_until__gt=F("effective_from"))
                ),
                name="svc_price_valid_period",
            ),
        )

    def clean(self) -> None:
        """Validate price, currency, and effective period."""

        super().clean()

        if self.amount <= Decimal("0"):
            raise ValidationError(
                {"amount": ("Service price must be greater than zero.")}
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
        """Return the service and price description."""

        return f"{self.service.code} — {self.currency} {self.amount}"
