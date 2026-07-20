"""Forms used by the customer-management interface."""

from django import forms

from apps.customers.models import Customer


class CustomerDetailsForm(forms.ModelForm):
    """Collect customer information for create and update workflows."""

    confirm_duplicate = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure editable customer fields and widgets."""

        model = Customer
        fields = (
            "customer_type",
            "name",
            "phone_number",
            "email",
            "address",
            "notes",
        )
        widgets = {
            "customer_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "name",
                    "placeholder": "Customer or company name",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "tel",
                    "placeholder": "For example, 0700 123 456",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "email",
                    "placeholder": "Optional email address",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional address",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional customer notes",
                }
            ),
        }


class CustomerRegistrationForm(CustomerDetailsForm):
    """Collect information required to register a customer."""


class CustomerUpdateForm(CustomerDetailsForm):
    """Collect changes to an existing customer record."""
