"""Forms used by the product-catalogue interface."""

from decimal import Decimal
from typing import Any

from django import forms

from apps.product_catalogue.constants import ProductUnit
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.product_catalogue.normalization import (
    normalize_category_code_display,
    normalize_category_code_key,
    normalize_product_sku_display,
    normalize_product_sku_key,
)


def _clean_unique_category_code(value: str) -> str:
    """Normalize a category code and reject duplicates."""

    display_code = normalize_category_code_display(value)
    normalized_code = normalize_category_code_key(display_code)

    if ProductCategory.objects.filter(normalized_code=normalized_code).exists():
        raise forms.ValidationError("A product category with this code already exists.")

    return display_code


def _clean_unique_product_sku(value: str) -> str:
    """Normalize a product SKU and reject duplicates."""

    display_sku = normalize_product_sku_display(value)
    normalized_sku = normalize_product_sku_key(display_sku)

    if Product.objects.filter(normalized_sku=normalized_sku).exists():
        raise forms.ValidationError("A product with this SKU already exists.")

    return display_sku


class ProductCategoryCreateForm(forms.ModelForm):
    """Collect a new product-category definition."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure category fields and widgets."""

        model = ProductCategory
        fields = (
            "code",
            "name",
            "description",
        )
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, FILTERS",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, Filters",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def clean_code(self) -> str:
        """Normalize and validate the category code."""

        return _clean_unique_category_code(self.cleaned_data["code"])


class ProductCreateForm(forms.ModelForm):
    """Collect a product and its initial selling price."""

    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
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
        """Configure product fields and widgets."""

        model = Product
        fields = (
            "category",
            "sku",
            "name",
            "manufacturer",
            "manufacturer_part_number",
            "unit",
            "description",
        )
        widgets = {
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "For example, OIL-FILTER-001",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product name",
                }
            ),
            "manufacturer": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional manufacturer",
                }
            ),
            "manufacturer_part_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional manufacturer part number",
                }
            ),
            "unit": forms.Select(
                choices=ProductUnit.choices,
                attrs={"class": "form-control"},
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Restrict category choices to active categories."""

        super().__init__(*args, **kwargs)

        category_field = self.fields["category"]

        if isinstance(
            category_field,
            forms.ModelChoiceField,
        ):
            category_field.queryset = ProductCategory.objects.filter(
                is_active=True
            ).order_by(
                "name",
                "code",
            )

    def clean_sku(self) -> str:
        """Normalize and validate the product SKU."""

        return _clean_unique_product_sku(self.cleaned_data["sku"])

    def clean_currency(self) -> str:
        """Normalize the three-letter currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency


class ProductPriceChangeForm(forms.Form):
    """Collect a replacement current product price."""

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
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        current_currency: str = "UGX",
        **kwargs: Any,
    ) -> None:
        """Initialize the form with the current currency."""

        super().__init__(*args, **kwargs)

        if not self.is_bound:
            self.initial["currency"] = current_currency

    def clean_currency(self) -> str:
        """Normalize the three-letter currency code."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Enter a three-letter currency code.")

        return currency
