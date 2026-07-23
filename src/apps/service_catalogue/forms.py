"""Forms used by the service-catalogue interface."""

from decimal import Decimal
from typing import Any

from django import forms

from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
)
from apps.service_catalogue.normalization import (
    normalize_service_code_display,
    normalize_service_code_key,
)
from apps.vehicles.constants import VehicleCategory


def _clean_unique_service_code(
    *,
    value: str,
    service_id: int | None = None,
) -> str:
    """Normalize a code and reject another matching service.

    Args:
        value: Service code entered by the employee.
        service_id: Existing service excluded during editing.

    Returns:
        The normalized display code.

    Raises:
        forms.ValidationError: If another service uses the code.
    """

    normalized_code = normalize_service_code_display(value)
    normalized_key = normalize_service_code_key(normalized_code)

    matching_services = Service.objects.filter(normalized_code=normalized_key)

    if service_id is not None:
        matching_services = matching_services.exclude(pk=service_id)

    if matching_services.exists():
        raise forms.ValidationError("A service with this code already exists.")

    return normalized_code


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
        """Configure service-creation fields."""

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
                    "placeholder": ("For example, Engine Oil Change"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ("Describe what the service includes"),
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

    def clean_code(self) -> str:
        """Normalize the code and reject an existing service."""

        return _clean_unique_service_code(value=self.cleaned_data["code"])

    def clean_currency(self) -> str:
        """Normalize the three-letter currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency


class ServiceUpdateForm(forms.ModelForm):
    """Collect editable information for an existing service."""

    applicable_categories = forms.MultipleChoiceField(
        choices=VehicleCategory.choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox-list"}),
        label="Applicable vehicle categories",
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure service-update fields."""

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
                    "placeholder": ("For example, Engine Oil Change"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "estimated_duration_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
        }

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load the service's existing applicable categories."""

        super().__init__(*args, **kwargs)

        if self.instance.pk is not None and not self.is_bound:
            self.initial["applicable_categories"] = list(
                ServiceApplicability.objects.filter(
                    service_id=self.instance.pk
                ).values_list(
                    "vehicle_category",
                    flat=True,
                )
            )

    def clean_code(self) -> str:
        """Normalize the code without matching this service."""

        return _clean_unique_service_code(
            value=self.cleaned_data["code"],
            service_id=self.instance.pk,
        )


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
                "placeholder": ("Reason or notes for this price change"),
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
