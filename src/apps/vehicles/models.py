"""Database models for vehicle management."""

from collections.abc import Collection

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.customers.models import Customer
from apps.vehicles.constants import FuelType, VehicleCategory
from apps.vehicles.normalization import (
    normalize_optional_identifier,
    normalize_registration_display,
    normalize_registration_key,
    normalize_vehicle_name,
)


class Vehicle(TimeStampedModel):
    """Represent a vehicle registered with the service bay."""

    vehicle_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    registration_number = models.CharField(
        max_length=30,
    )
    normalized_registration_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )
    current_owner = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    category = models.CharField(
        max_length=20,
        choices=VehicleCategory.choices,
    )
    make = models.CharField(
        max_length=100,
        db_index=True,
    )
    model = models.CharField(
        max_length=100,
        db_index=True,
    )
    year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    color = models.CharField(
        max_length=50,
        blank=True,
    )
    current_mileage = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        blank=True,
    )
    engine_number = models.CharField(
        max_length=50,
        blank=True,
    )
    chassis_number = models.CharField(
        max_length=50,
        blank=True,
    )
    vin = models.CharField(
        max_length=50,
        blank=True,
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
        related_name="vehicles_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicles_updated",
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure vehicle ordering and business permissions."""

        ordering = (
            "registration_number",
            "vehicle_number",
        )
        permissions = (
            (
                "transfer_vehicle_owner",
                "Can transfer vehicle ownership",
            ),
            (
                "deactivate_vehicle",
                "Can deactivate vehicle",
            ),
            (
                "reactivate_vehicle",
                "Can reactivate vehicle",
            ),
        )
        indexes = (
            models.Index(
                fields=("is_active", "registration_number"),
                name="veh_active_reg_idx",
            ),
            models.Index(
                fields=("current_owner", "is_active"),
                name="veh_owner_active_idx",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalize vehicle fields before Django validates them.

        Args:
            exclude: Field names Django should exclude from validation.
        """

        excluded_fields = set(exclude or ())

        if "registration_number" not in excluded_fields:
            self.registration_number = normalize_registration_display(
                self.registration_number
            )
            self.normalized_registration_number = normalize_registration_key(
                self.registration_number
            )

        if "make" not in excluded_fields:
            self.make = normalize_vehicle_name(self.make)

        if "model" not in excluded_fields:
            self.model = normalize_vehicle_name(self.model)

        if "color" not in excluded_fields:
            self.color = normalize_vehicle_name(self.color)

        if "engine_number" not in excluded_fields:
            self.engine_number = normalize_optional_identifier(self.engine_number)

        if "chassis_number" not in excluded_fields:
            self.chassis_number = normalize_optional_identifier(self.chassis_number)

        if "vin" not in excluded_fields:
            self.vin = normalize_optional_identifier(self.vin)

        if self.year is not None:
            maximum_year = timezone.now().year + 1

            if not 1886 <= self.year <= maximum_year:
                raise ValidationError(
                    {
                        "year": (
                            "Enter a valid manufacturing year between "
                            f"1886 and {maximum_year}."
                        )
                    }
                )

        super().clean_fields(exclude=exclude)

    def __str__(self) -> str:
        """Return the registration number and vehicle description."""

        return f"{self.registration_number} — {self.make} {self.model}"


class VehicleOwnership(TimeStampedModel):
    """Preserve the ownership history of a registered vehicle."""

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="ownership_history",
    )
    owner = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="vehicle_ownership_history",
    )
    started_at = models.DateTimeField(
        default=timezone.now,
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_ownership_changes",
    )
    notes = models.TextField(
        blank=True,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure ownership-history ordering and constraints."""

        ordering = ("-started_at", "-created_at")
        constraints = (
            models.UniqueConstraint(
                fields=("vehicle",),
                condition=Q(ended_at__isnull=True),
                name="veh_one_open_owner",
            ),
        )

    def clean(self) -> None:
        """Ensure an ownership period ends after it begins."""

        super().clean()

        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValidationError(
                {"ended_at": ("Ownership cannot end before it begins.")}
            )

    def __str__(self) -> str:
        """Return the vehicle and owner description."""

        return f"{self.vehicle.registration_number} — {self.owner}"
