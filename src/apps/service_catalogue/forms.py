"""Forms used by the service-catalogue interface."""

from decimal import Decimal
from typing import Any

from django import forms

from apps.service_catalogue.models import Service
from apps.vehicles.constants import VehicleCategory


class ServiceCreateForm(forms.ModelForm):
    """Collect a service definition and its initial price."""

    applicable_categories = forms.MultipleChoiceField(
        choices=VehicleCategory.choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox-list"}),
        label="Applicable vehicle categories",
    )
    initial_price = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
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
    price_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional initial-price notes",
            }
        ),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure editable service-definition fields."""

        model = Service
        fields = (
            "code",
            "name",
            "description",
            "estimated_duration_minutes",
        )
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, OIL-CHANGE",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, Engine Oil Change",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what the service includes",
                }
            ),
            "estimated_duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "placeholder": "Estimated minutes",
                }
            ),
        }

    def clean_currency(self) -> str:
        """Normalize the three-letter currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency


class ServicePriceChangeForm(forms.Form):
    """Collect a replacement current service price."""

    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
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
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Reason or notes for this price change",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        current_currency: str = "UGX",
        **kwargs: Any,
    ) -> None:
        """Initialize the form using the current currency."""

        super().__init__(*args, **kwargs)

        if not self.is_bound:
            self.initial["currency"] = current_currency

    def clean_currency(self) -> str:
        """Normalize the three-letter currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency
