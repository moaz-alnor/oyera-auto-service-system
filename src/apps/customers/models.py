"""Database models for customer management."""

from collections.abc import Collection

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.customers.constants import CustomerType
from apps.customers.normalization import (
    normalize_customer_name,
    normalize_email_address,
    normalize_phone_number,
)


class Customer(TimeStampedModel):
    """Represent an individual or company using the service bay."""

    customer_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=30,
    )
    normalized_phone_number = models.CharField(
        max_length=15,
        db_index=True,
        editable=False,
    )
    email = models.EmailField(
        blank=True,
    )
    address = models.TextField(
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
        related_name="customers_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customers_updated",
        null=True,
        blank=True,
        editable=False,
    )

    # Django uses an inner Meta class as declarative model configuration.
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure customer ordering and business permissions."""

        ordering = (
            "name",
            "customer_number",
        )
        permissions = (
            (
                "deactivate_customer",
                "Can deactivate customer",
            ),
            (
                "reactivate_customer",
                "Can reactivate customer",
            ),
        )
        indexes = (
            models.Index(
                fields=("is_active", "name"),
                name="cust_active_name_idx",
            ),
        )

    def clean_fields(
        self,
        exclude: Collection[str] | None = None,
    ) -> None:
        """Normalize customer fields before Django validates them.

        Args:
            exclude: Field names Django should exclude from validation.
        """

        excluded_fields = set(exclude or ())

        if "name" not in excluded_fields:
            self.name = normalize_customer_name(self.name)

        if "phone_number" not in excluded_fields:
            self.phone_number = self.phone_number.strip()
            self.normalized_phone_number = normalize_phone_number(self.phone_number)

        if "email" not in excluded_fields:
            self.email = normalize_email_address(self.email)

        super().clean_fields(exclude=exclude)

    def __str__(self) -> str:
        """Return the customer number and display name."""

        if self.customer_number:
            return f"{self.customer_number} — {self.name}"

        return self.name
