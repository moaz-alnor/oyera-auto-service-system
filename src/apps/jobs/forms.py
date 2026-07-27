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


class VehicleReleaseForm(forms.Form):
    """Collect final vehicle-handover information."""

    final_mileage = forms.IntegerField(
        min_value=0,
        label="Final mileage",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 0,
                "placeholder": "Final odometer reading",
            }
        ),
    )
    final_condition = forms.CharField(
        label="Final vehicle condition",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": ("Record the vehicle condition at handover"),
            }
        ),
    )
    received_by_name = forms.CharField(
        max_length=200,
        label="Received by",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Name of the person receiving the vehicle"),
            }
        ),
    )
    received_by_contact = forms.CharField(
        max_length=100,
        required=False,
        label="Receiver contact",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Optional phone number or contact",
            }
        ),
    )
    handover_notes = forms.CharField(
        required=False,
        label="Handover notes",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Record keys, documents, parts, or other items handed over"
                ),
            }
        ),
    )
    payment_override = forms.BooleanField(
        required=False,
        label="Authorise release with outstanding balance",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )
    payment_override_reason = forms.CharField(
        required=False,
        label="Payment override reason",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explain why the vehicle may be released before full payment"
                ),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        minimum_mileage: int,
        allow_payment_override: bool,
        **kwargs: Any,
    ) -> None:
        """Configure mileage and override controls."""

        super().__init__(*args, **kwargs)

        self.minimum_mileage = minimum_mileage
        self.allow_payment_override = allow_payment_override

        mileage_field = self.fields["final_mileage"]
        mileage_field.initial = minimum_mileage
        mileage_field.widget.attrs["min"] = minimum_mileage
        mileage_field.help_text = (
            f"The final mileage must be at least {minimum_mileage}."
        )

        if not allow_payment_override:
            self.fields.pop("payment_override")
            self.fields.pop("payment_override_reason")

    def clean(self) -> dict[str, Any]:
        """Validate mileage and payment-override evidence."""

        cleaned_data = super().clean()

        final_mileage = cleaned_data.get("final_mileage")

        if isinstance(final_mileage, int) and final_mileage < self.minimum_mileage:
            self.add_error(
                "final_mileage",
                (f"Final mileage cannot be lower than {self.minimum_mileage}."),
            )

        if not self.allow_payment_override:
            cleaned_data["payment_override"] = False
            cleaned_data["payment_override_reason"] = ""

            return cleaned_data

        payment_override = bool(cleaned_data.get("payment_override"))
        override_reason = str(
            cleaned_data.get(
                "payment_override_reason",
                "",
            )
        ).strip()

        cleaned_data["payment_override_reason"] = override_reason

        if payment_override and not override_reason:
            self.add_error(
                "payment_override_reason",
                ("Record why release with an outstanding balance is authorised."),
            )

        if not payment_override:
            cleaned_data["payment_override_reason"] = ""

        return cleaned_data
