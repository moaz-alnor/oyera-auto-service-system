"""Forms used by the inventory-management interface."""

from decimal import Decimal
from typing import Any

from django import forms
from django.db.models import Q, Sum

from apps.inventory.constants import (
    ReservationStatus,
    StockMovementType,
)
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
    StockReservation,
)
from apps.inventory.normalization import (
    normalize_location_code,
)
from apps.product_catalogue.models import Product
from apps.workshop.models import WorkProductRequirement

_DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"

_ACTIVE_RESERVATION_STATUSES = (
    ReservationStatus.ACTIVE,
    ReservationStatus.PARTIALLY_ISSUED,
)


def _datetime_widget() -> forms.DateTimeInput:
    """Return the shared optional transaction-time widget."""

    return forms.DateTimeInput(
        format=_DATETIME_LOCAL_FORMAT,
        attrs={
            "class": "form-control",
            "type": "datetime-local",
        },
    )


class StockLocationForm(forms.ModelForm):
    """Collect a physical stock-location definition."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure editable stock-location fields."""

        model = StockLocation
        fields = (
            "code",
            "name",
            "description",
        )
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, MAIN-STORE",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, Main Parts Store",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ("Optional description of the location."),
                }
            ),
        }

    def clean_code(self) -> str:
        """Normalize the code and reject another matching location."""

        code = self.cleaned_data["code"].strip()
        normalized_code = normalize_location_code(code)

        if not normalized_code:
            raise forms.ValidationError("Enter a valid stock-location code.")

        matching_locations = StockLocation.objects.filter(
            normalized_code=normalized_code
        )

        if self.instance.pk is not None:
            matching_locations = matching_locations.exclude(pk=self.instance.pk)

        if matching_locations.exists():
            raise forms.ValidationError(
                "A stock location with this code already exists."
            )

        return code


class InventoryItemForm(forms.ModelForm):
    """Connect a catalogue product to a stock location."""

    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    location = forms.ModelChoiceField(
        queryset=StockLocation.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure editable inventory-item fields."""

        model = InventoryItem
        fields = (
            "product",
            "location",
            "reorder_level",
            "notes",
        )
        widgets = {
            "reorder_level": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.001",
                    "placeholder": "0.000",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional inventory notes.",
                }
            ),
        }

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load active products and stock locations."""

        super().__init__(*args, **kwargs)

        current_product_id = getattr(
            self.instance,
            "product_id",
            None,
        )
        current_location_id = getattr(
            self.instance,
            "location_id",
            None,
        )

        product_query = Q(is_active=True)

        if current_product_id is not None:
            product_query |= Q(pk=current_product_id)

        location_query = Q(is_active=True)

        if current_location_id is not None:
            location_query |= Q(pk=current_location_id)

        product_field = self.fields["product"]
        location_field = self.fields["location"]

        if isinstance(
            product_field,
            forms.ModelChoiceField,
        ):
            product_field.queryset = (
                Product.objects.filter(product_query)
                .select_related("category")
                .order_by(
                    "name",
                    "sku",
                )
            )

        if isinstance(
            location_field,
            forms.ModelChoiceField,
        ):
            location_field.queryset = StockLocation.objects.filter(
                location_query
            ).order_by(
                "name",
                "code",
            )

    def clean(self) -> dict[str, Any]:
        """Reject a duplicate product-location combination."""

        cleaned_data = super().clean()

        product = cleaned_data.get("product")
        location = cleaned_data.get("location")

        if product is None or location is None:
            return cleaned_data

        matching_items = InventoryItem.objects.filter(
            product=product,
            location=location,
        )

        if self.instance.pk is not None:
            matching_items = matching_items.exclude(pk=self.instance.pk)

        if matching_items.exists():
            raise forms.ValidationError(
                "An inventory item already exists for this product and stock location."
            )

        return cleaned_data


class ReceiveStockForm(forms.Form):
    """Collect a positive physical stock receipt."""

    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    unit_cost = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }
        ),
    )
    currency = forms.CharField(
        max_length=3,
        initial="UGX",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "maxlength": 3,
            }
        ),
    )
    external_reference = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Supplier invoice or delivery reference"),
            }
        ),
    )
    occurred_at = forms.DateTimeField(
        required=False,
        input_formats=(_DATETIME_LOCAL_FORMAT,),
        widget=_datetime_widget(),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Optional receipt notes.",
            }
        ),
    )

    def clean_currency(self) -> str:
        """Normalize and validate the currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency


class ReserveStockForm(forms.Form):
    """Collect stock allocated to one workshop requirement."""

    inventory_item = forms.ModelChoiceField(
        queryset=InventoryItem.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        requirement: WorkProductRequirement,
        **kwargs: Any,
    ) -> None:
        """List eligible stock records for the required product."""

        super().__init__(*args, **kwargs)

        source_product_id = requirement.source_product_line.product_id

        already_reserved_item_ids = StockReservation.objects.filter(
            work_product_requirement=requirement,
            status__in=_ACTIVE_RESERVATION_STATUSES,
        ).values_list(
            "inventory_item_id",
            flat=True,
        )

        inventory_item_field = self.fields["inventory_item"]

        if isinstance(
            inventory_item_field,
            forms.ModelChoiceField,
        ):
            inventory_item_field.queryset = (
                InventoryItem.objects.filter(
                    product_id=source_product_id,
                    product__is_active=True,
                    location__is_active=True,
                    is_active=True,
                )
                .exclude(pk__in=already_reserved_item_ids)
                .select_related(
                    "product",
                    "location",
                )
                .order_by(
                    "location__name",
                    "location__code",
                )
            )


class ReleaseReservationForm(forms.Form):
    """Collect an explanation for releasing reserved stock."""

    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explain why the remaining reservation is being released."
                ),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Require a meaningful release explanation."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the reservation is being released.")

        return reason


class IssueStockForm(forms.Form):
    """Collect stock issued against one reservation."""

    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    occurred_at = forms.DateTimeField(
        required=False,
        input_formats=(_DATETIME_LOCAL_FORMAT,),
        widget=_datetime_widget(),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Optional workshop issue notes.",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        reservation: StockReservation,
        **kwargs: Any,
    ) -> None:
        """Store the reservation used for quantity validation."""

        super().__init__(*args, **kwargs)

        self.reservation = reservation

        quantity_field = self.fields["quantity"]

        quantity_field.help_text = (
            f"Maximum issue quantity: {reservation.remaining_quantity}"
        )

    def clean_quantity(self) -> Decimal:
        """Prevent input above the reservation balance."""

        quantity = self.cleaned_data["quantity"]

        if quantity > self.reservation.remaining_quantity:
            raise forms.ValidationError(
                "Issued quantity cannot exceed the stock remaining on the reservation."
            )

        return quantity


class ReturnStockForm(forms.Form):
    """Collect stock returned from one original issue."""

    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    occurred_at = forms.DateTimeField(
        required=False,
        input_formats=(_DATETIME_LOCAL_FORMAT,),
        widget=_datetime_widget(),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain what was returned.",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        source_movement: StockMovement,
        **kwargs: Any,
    ) -> None:
        """Calculate stock still returnable from an issue."""

        super().__init__(*args, **kwargs)

        self.source_movement = source_movement

        returned_quantity = StockMovement.objects.filter(
            source_movement=source_movement,
            movement_type=StockMovementType.RETURN,
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0.000")

        self.returnable_quantity = source_movement.quantity - returned_quantity

        quantity_field = self.fields["quantity"]
        quantity_field.help_text = (
            f"Maximum return quantity: {self.returnable_quantity}"
        )

    def clean_quantity(self) -> Decimal:
        """Prevent cumulative returns above the original issue."""

        quantity = self.cleaned_data["quantity"]

        if quantity > self.returnable_quantity:
            raise forms.ValidationError(
                "Returned quantity cannot exceed the quantity "
                "remaining on the original issue."
            )

        return quantity


class AdjustStockForm(forms.Form):
    """Collect an auditable positive or negative adjustment."""

    movement_type = forms.ChoiceField(
        choices=(
            (
                StockMovementType.ADJUSTMENT_IN,
                StockMovementType.ADJUSTMENT_IN.label,
            ),
            (
                StockMovementType.ADJUSTMENT_OUT,
                StockMovementType.ADJUSTMENT_OUT.label,
            ),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=12,
        decimal_places=3,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why the physical count changed."),
            }
        ),
    )
    external_reference = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Optional stock-count or incident reference"),
            }
        ),
    )
    occurred_at = forms.DateTimeField(
        required=False,
        input_formats=(_DATETIME_LOCAL_FORMAT,),
        widget=_datetime_widget(),
    )

    def clean_movement_type(self) -> StockMovementType:
        """Return the selected adjustment enum member."""

        return StockMovementType(self.cleaned_data["movement_type"])

    def clean_reason(self) -> str:
        """Require a meaningful adjustment explanation."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError(
                "Record why the stock balance is being adjusted."
            )

        return reason
