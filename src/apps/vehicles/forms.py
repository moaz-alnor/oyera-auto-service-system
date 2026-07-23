"""Forms used by the vehicle-management interface."""

from typing import Any

from django import forms

from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.vehicles.normalization import (
    normalize_registration_display,
    normalize_registration_key,
)


class VehicleRegistrationForm(forms.ModelForm):
    """Collect vehicle information for initial registration."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure vehicle-registration fields and widgets."""

        model = Vehicle
        fields = (
            "current_owner",
            "registration_number",
            "category",
            "make",
            "model",
            "year",
            "color",
            "current_mileage",
            "fuel_type",
            "engine_number",
            "chassis_number",
            "vin",
            "notes",
        )
        labels = {
            "current_owner": "Owner",
        }
        widgets = {
            "current_owner": forms.Select(attrs={"class": "form-control"}),
            "registration_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, UBD 245X",
                    "autocomplete": "off",
                }
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "make": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, Toyota",
                }
            ),
            "model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, Corolla",
                }
            ),
            "year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1886,
                }
            ),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "current_mileage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "fuel_type": forms.Select(attrs={"class": "form-control"}),
            "engine_number": forms.TextInput(attrs={"class": "form-control"}),
            "chassis_number": forms.TextInput(attrs={"class": "form-control"}),
            "vin": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional vehicle notes",
                }
            ),
        }

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Limit owner choices to active customers."""

        super().__init__(*args, **kwargs)

        owner_field = self.fields["current_owner"]

        if isinstance(owner_field, forms.ModelChoiceField):
            owner_field.queryset = Customer.objects.filter(is_active=True).order_by(
                "name",
                "customer_number",
            )

    def clean_registration_number(self) -> str:
        """Normalize registration and reject existing vehicles."""

        registration_number = self.cleaned_data["registration_number"]
        normalized_key = normalize_registration_key(registration_number)

        if Vehicle.objects.filter(
            normalized_registration_number=normalized_key
        ).exists():
            raise forms.ValidationError(
                "A vehicle with this registration number already exists."
            )

        return normalize_registration_display(registration_number)


class VehicleOwnershipTransferForm(forms.Form):
    """Collect the new owner and transfer notes."""

    new_owner = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        label="New owner",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Optional reason or ownership-transfer notes"),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        current_owner_id: int,
        **kwargs: Any,
    ) -> None:
        """Exclude inactive customers and the current owner."""

        super().__init__(*args, **kwargs)

        owner_field = self.fields["new_owner"]

        if isinstance(owner_field, forms.ModelChoiceField):
            owner_field.queryset = (
                Customer.objects.filter(is_active=True)
                .exclude(pk=current_owner_id)
                .order_by(
                    "name",
                    "customer_number",
                )
            )
