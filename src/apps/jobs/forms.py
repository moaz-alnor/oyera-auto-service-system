"""Forms used by job-card intake and history workflows."""

from typing import Any

from django import forms

from apps.customers.models import Customer
from apps.jobs.constants import (
    FuelLevel,
    InspectionType,
    JobNoteType,
    JobPriority,
)
from apps.jobs.selectors import (
    get_active_customers,
    get_active_vehicles,
)
from apps.vehicles.models import Vehicle


class JobCardOpenForm(forms.Form):
    """Collect intake information for one vehicle visit."""

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    arrival_mileage = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 0,
                "placeholder": "Current odometer reading",
            }
        ),
    )
    customer_complaint = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": ("Describe the customer's reported problem"),
            }
        ),
    )
    visible_condition = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Record visible damage or vehicle condition"),
            }
        ),
    )
    fuel_level = forms.ChoiceField(
        choices=FuelLevel.choices,
        initial=FuelLevel.UNKNOWN,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    priority = forms.ChoiceField(
        choices=JobPriority.choices,
        initial=JobPriority.NORMAL,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load only active customers and vehicles."""

        super().__init__(*args, **kwargs)

        customer_field = self.fields["customer"]
        vehicle_field = self.fields["vehicle"]

        if isinstance(
            customer_field,
            forms.ModelChoiceField,
        ):
            customer_field.queryset = get_active_customers()

        if isinstance(
            vehicle_field,
            forms.ModelChoiceField,
        ):
            vehicle_field.queryset = get_active_vehicles()

    def clean(self) -> dict[str, Any]:
        """Validate the selected customer, vehicle, and mileage."""

        cleaned_data = super().clean()

        customer = cleaned_data.get("customer")
        vehicle = cleaned_data.get("vehicle")
        arrival_mileage = cleaned_data.get("arrival_mileage")

        if (
            isinstance(customer, Customer)
            and isinstance(vehicle, Vehicle)
            and vehicle.current_owner != customer
        ):
            self.add_error(
                "vehicle",
                "The selected vehicle does not belong to this customer.",
            )

        if (
            isinstance(vehicle, Vehicle)
            and isinstance(arrival_mileage, int)
            and vehicle.current_mileage is not None
            and arrival_mileage < vehicle.current_mileage
        ):
            self.add_error(
                "arrival_mileage",
                (
                    "Arrival mileage cannot be lower than the "
                    f"stored mileage of {vehicle.current_mileage}."
                ),
            )

        return cleaned_data


class InspectionCreateForm(forms.Form):
    """Collect one append-only inspection record."""

    inspection_type = forms.ChoiceField(
        choices=InspectionType.choices,
        initial=InspectionType.INITIAL,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    findings = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": ("Record inspection findings"),
            }
        ),
    )
    safety_observations = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Record safety-related observations"),
            }
        ),
    )
    recommended_action = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Describe the recommended work"),
            }
        ),
    )


class JobNoteCreateForm(forms.Form):
    """Collect one append-only job note."""

    note_type = forms.ChoiceField(
        choices=JobNoteType.choices,
        initial=JobNoteType.GENERAL,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": ("Enter communication or internal notes"),
            }
        ),
    )


class JobCardCancelForm(forms.Form):
    """Collect the reason for cancelling a job card."""

    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": ("Explain why this job is being cancelled"),
            }
        ),
    )
