"""Forms for quotation and customer-decision workflows."""

from datetime import date
from decimal import Decimal

from django import forms

from apps.product_catalogue.models import Product
from apps.quotations.constants import (
    CustomerDecisionMethod,
)
from apps.quotations.models import Quotation
from apps.quotations.selectors import (
    get_jobs_available_for_quotation,
    get_products_available_for_quotation,
    get_services_available_for_quotation,
)
from apps.service_catalogue.models import Service


class QuotationCreateForm(forms.Form):
    """Collect information for a first quotation revision."""

    job_card = forms.ModelChoiceField(
        queryset=get_jobs_available_for_quotation(),
        label="Job card",
        empty_label="Select a job card",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    currency = forms.CharField(
        max_length=3,
        initial="UGX",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "maxlength": 3,
                "placeholder": "UGX",
            }
        ),
    )
    discount_percentage = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        max_digits=5,
        decimal_places=2,
        initial=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 0,
                "max": 100,
                "step": "0.01",
            }
        ),
    )
    tax_percentage = forms.DecimalField(
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        max_digits=5,
        decimal_places=2,
        initial=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 0,
                "max": 100,
                "step": "0.01",
            }
        ),
    )
    valid_until = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Enter quotation terms or internal notes"),
            }
        ),
    )

    def clean_currency(self) -> str:
        """Normalize and validate the currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency

    def clean_valid_until(self) -> date | None:
        """Prevent creating an already-expired quotation."""

        valid_until = self.cleaned_data.get("valid_until")

        if isinstance(valid_until, date) and valid_until < date.today():
            raise forms.ValidationError("The validity date cannot be in the past.")

        return valid_until


class ServiceLineCreateForm(forms.Form):
    """Collect one service quotation line."""

    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        empty_label="Select a service",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        initial=Decimal("1.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }
        ),
    )
    description_override = forms.CharField(
        required=False,
        label="Quotation description",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Leave blank to use the catalogue description"),
            }
        ),
    )

    def configure_for_quotation(
        self,
        *,
        quotation: Quotation,
    ) -> None:
        """Restrict choices to applicable priced services."""

        service_field = self.fields["service"]

        if isinstance(
            service_field,
            forms.ModelChoiceField,
        ):
            service_field.queryset = get_services_available_for_quotation(
                quotation=quotation
            )


class ProductLineCreateForm(forms.Form):
    """Collect one product quotation line."""

    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        empty_label="Select a product",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.DecimalField(
        min_value=Decimal("0.001"),
        max_digits=10,
        decimal_places=3,
        initial=Decimal("1.000"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    description_override = forms.CharField(
        required=False,
        label="Quotation description",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Leave blank to use the catalogue description"),
            }
        ),
    )

    def configure_for_quotation(
        self,
        *,
        quotation: Quotation,
    ) -> None:
        """Restrict choices to active products with prices."""

        product_field = self.fields["product"]

        if isinstance(
            product_field,
            forms.ModelChoiceField,
        ):
            product_field.queryset = get_products_available_for_quotation(
                quotation=quotation
            )


class CustomerDecisionForm(forms.Form):
    """Collect customer approval or rejection evidence."""

    customer_name = forms.CharField(
        max_length=150,
        label="Customer representative",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Name of the person making the decision"),
            }
        ),
    )
    method = forms.ChoiceField(
        choices=CustomerDecisionMethod.choices,
        label="Decision method",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    notes = forms.CharField(
        required=False,
        label="Decision notes",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": ("Record approval details or rejection reason"),
            }
        ),
    )

    def clean_customer_name(self) -> str:
        """Normalize the customer representative name."""

        customer_name = self.cleaned_data["customer_name"].strip()

        if not customer_name:
            raise forms.ValidationError("Enter the customer representative's name.")

        return customer_name

    def clean_notes(self) -> str:
        """Normalize optional customer-decision notes."""

        return self.cleaned_data["notes"].strip()
