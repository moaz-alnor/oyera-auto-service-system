"""Forms used by purchasing browser workflows."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django import forms
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.forms import BaseFormSet, formset_factory
from django.utils import timezone

from apps.product_catalogue.models import Product
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
)
from apps.purchasing.models import (
    GoodsReceiptLine,
    PurchaseOrder,
    Supplier,
    SupplierInvoice,
)

_DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class SupplierDetailsForm(forms.ModelForm):
    """Collect supplier information for browser workflows."""

    confirm_duplicate = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput,
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure supplier fields and widgets."""

        model = Supplier
        fields = (
            "code",
            "name",
            "contact_name",
            "phone_number",
            "email",
            "address",
            "tax_identifier",
            "payment_terms_days",
            "preferred_currency",
            "notes",
        )
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": ("For example, AUTO-PARTS-01"),
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "organization",
                    "placeholder": ("Supplier or company name"),
                }
            ),
            "contact_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "name",
                    "placeholder": ("Primary contact person"),
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "tel",
                    "placeholder": ("For example, +256 700 123 456"),
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "email",
                    "placeholder": ("accounts@example.com"),
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": ("Supplier business address"),
                }
            ),
            "tax_identifier": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": ("Tax or registration identifier"),
                }
            ),
            "payment_terms_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                }
            ),
            "preferred_currency": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "3",
                    "placeholder": "UGX",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ("Optional supplier notes"),
                }
            ),
        }

    def clean_preferred_currency(self) -> str:
        """Normalise the three-letter currency code."""

        currency = self.cleaned_data["preferred_currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Currency must use a three-letter code.")

        return currency


class SupplierRegistrationForm(SupplierDetailsForm):
    """Collect information required to register a supplier."""


class SupplierUpdateForm(SupplierDetailsForm):
    """Collect replacement supplier information."""


class ActiveSupplierChoiceField(forms.ModelChoiceField):
    """Display active supplier identity."""

    def label_from_instance(
        self,
        obj: Supplier,
    ) -> str:
        """Return supplier number, code, and name."""

        supplier_number = obj.supplier_number or obj.code

        return f"{supplier_number} - {obj.code} - {obj.name}"


class ActiveProductChoiceField(forms.ModelChoiceField):
    """Display product identity and unit."""

    def label_from_instance(
        self,
        obj: Product,
    ) -> str:
        """Return SKU, product name, and unit."""

        return f"{obj.sku} - {obj.name} - {obj.unit}"


class PurchaseOrderDetailsForm(forms.ModelForm):
    """Collect a purchase-order header."""

    supplier = ActiveSupplierChoiceField(
        queryset=Supplier.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    currency = forms.CharField(
        max_length=3,
        initial="UGX",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "maxlength": "3",
                "placeholder": "UGX",
            }
        ),
    )
    discount_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        initial=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "max": "100",
                "step": "0.01",
            }
        ),
    )
    tax_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        initial=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "max": "100",
                "step": "0.01",
            }
        ),
    )
    delivery_cost = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.00"),
        initial=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }
        ),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Configure purchase-order header fields."""

        model = PurchaseOrder
        fields = (
            "supplier",
            "currency",
            "discount_percentage",
            "tax_percentage",
            "delivery_cost",
            "expected_delivery_date",
            "supplier_reference",
            "notes",
        )
        widgets = {
            "expected_delivery_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "supplier_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": ("Supplier quotation or reference"),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ("Optional purchase-order notes"),
                }
            ),
        }

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load suppliers available for ordering."""

        super().__init__(*args, **kwargs)

        supplier_queryset = Supplier.objects.filter(is_active=True).order_by(
            "name",
            "supplier_number",
        )

        supplier_field = self.fields["supplier"]

        if isinstance(
            supplier_field,
            forms.ModelChoiceField,
        ):
            supplier_field.queryset = supplier_queryset

    def clean_supplier(self) -> Supplier:
        """Require an active supplier."""

        supplier = self.cleaned_data["supplier"]

        if not supplier.is_active:
            raise forms.ValidationError(
                "An inactive supplier cannot receive a purchase order."
            )

        return supplier

    def clean_currency(self) -> str:
        """Normalise the purchase-order currency."""

        currency = self.cleaned_data["currency"].strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise forms.ValidationError("Currency must use a three-letter code.")

        return currency


class PurchaseOrderCreateForm(PurchaseOrderDetailsForm):
    """Collect a new draft purchase order."""


class PurchaseOrderUpdateForm(PurchaseOrderDetailsForm):
    """Collect replacement draft-order details."""


class PurchaseOrderLineCreateForm(forms.Form):
    """Collect a product for a draft purchase order."""

    product = ActiveProductChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    quantity_ordered = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    unit_cost = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
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
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": ("Optional purchase description"),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        purchase_order: PurchaseOrder | None = None,
        **kwargs: Any,
    ) -> None:
        """Load active products not already ordered."""

        super().__init__(*args, **kwargs)

        products = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .order_by(
                "name",
                "sku",
            )
        )

        if purchase_order is not None and purchase_order.pk is not None:
            products = products.exclude(
                purchase_order_lines__purchase_order=(purchase_order)
            )

        product_field = self.fields["product"]

        if isinstance(
            product_field,
            forms.ModelChoiceField,
        ):
            product_field.queryset = products.distinct()


class PurchaseOrderLineUpdateForm(forms.Form):
    """Collect replacement values for an order line."""

    quantity_ordered = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }
        ),
    )
    unit_cost = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
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
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )


class PurchaseOrderSubmitForm(forms.Form):
    """Require confirmation before submission."""

    confirmation = forms.BooleanField(
        label=("I confirm that the purchase order is complete and ready for approval."),
    )


class PurchaseOrderApprovalForm(forms.Form):
    """Require confirmation before approval."""

    confirmation = forms.BooleanField(
        label=("I confirm that I reviewed and approve this purchase order."),
    )


class PurchaseOrderCancellationForm(forms.Form):
    """Collect purchase-order cancellation evidence."""

    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why this purchase order is being cancelled"),
            }
        ),
    )


class PurchaseOrderChoiceField(forms.ModelChoiceField):
    """Display useful purchase-order information."""

    def label_from_instance(
        self,
        obj: PurchaseOrder,
    ) -> str:
        """Return purchase order, supplier, and currency."""

        return (
            f"{obj.purchase_order_number} - "
            f"{obj.supplier_name_snapshot} - "
            f"{obj.currency}"
        )


class GoodsReceiptLineChoiceField(forms.ModelChoiceField):
    """Display receipt-line availability."""

    def label_from_instance(
        self,
        obj: GoodsReceiptLine,
    ) -> str:
        """Return receipt, product, and available quantity."""

        available_quantity = getattr(
            obj,
            "available_quantity",
            obj.quantity_received,
        )

        return (
            f"{obj.goods_receipt.goods_receipt_number} - "
            f"{obj.product_sku_snapshot} - "
            f"{obj.product_name_snapshot} - "
            f"available {available_quantity:.3f} "
            f"{obj.unit_snapshot} - "
            f"cost {obj.currency_snapshot} "
            f"{obj.unit_cost_snapshot:.2f}"
        )


def available_receipt_lines_queryset(
    *,
    purchase_order: PurchaseOrder,
):
    """Return receipt lines with uninvoiced quantities."""

    active_invoice_statuses = (
        SupplierInvoiceStatus.DRAFT,
        SupplierInvoiceStatus.POSTED,
        SupplierInvoiceStatus.PARTIALLY_PAID,
        SupplierInvoiceStatus.PAID,
    )

    invoiced_quantity = Coalesce(
        Sum(
            "supplier_invoice_lines__quantity_invoiced",
            filter=Q(
                supplier_invoice_lines__supplier_invoice__status__in=(
                    active_invoice_statuses
                )
            ),
        ),
        Value(Decimal("0.000")),
        output_field=DecimalField(
            max_digits=12,
            decimal_places=3,
        ),
    )

    return (
        GoodsReceiptLine.objects.filter(goods_receipt__purchase_order=(purchase_order))
        .select_related(
            "goods_receipt",
            "purchase_order_line",
            "purchase_order_line__product",
            "inventory_item",
            "inventory_item__location",
        )
        .annotate(
            invoiced_quantity=invoiced_quantity,
        )
        .annotate(
            available_quantity=ExpressionWrapper(
                F("quantity_received") - F("invoiced_quantity"),
                output_field=DecimalField(
                    max_digits=12,
                    decimal_places=3,
                ),
            )
        )
        .filter(available_quantity__gt=Decimal("0.000"))
        .order_by(
            "goods_receipt__received_at",
            "purchase_order_line__position",
            "pk",
        )
    )


class SupplierInvoiceCreateForm(forms.Form):
    """Collect supplier-invoice header information."""

    purchase_order = PurchaseOrderChoiceField(
        queryset=PurchaseOrder.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    supplier_reference = forms.CharField(
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Reference printed on the supplier invoice"),
            }
        ),
    )
    invoice_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )
    due_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )
    tax_amount = forms.DecimalField(
        initial=Decimal("0.00"),
        min_value=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.00",
                "step": "0.01",
            }
        ),
    )
    other_charges = forms.DecimalField(
        initial=Decimal("0.00"),
        min_value=Decimal("0.00"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.00",
                "step": "0.01",
            }
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Optional supplier-invoice notes."),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        purchase_order: PurchaseOrder | None = None,
        **kwargs: Any,
    ) -> None:
        """Load purchase orders containing received goods."""

        super().__init__(*args, **kwargs)

        self.selected_purchase_order = purchase_order

        purchase_order_field = self.fields["purchase_order"]

        if isinstance(
            purchase_order_field,
            forms.ModelChoiceField,
        ):
            purchase_order_field.queryset = (
                PurchaseOrder.objects.filter(
                    status__in=(
                        PurchaseOrderStatus.PARTIALLY_RECEIVED,
                        PurchaseOrderStatus.RECEIVED,
                    ),
                    goods_receipts__lines__isnull=False,
                )
                .select_related("supplier")
                .distinct()
                .order_by(
                    "-approved_at",
                    "-pk",
                )
            )

        if not self.is_bound and purchase_order is not None:
            today = timezone.localdate()

            self.initial["purchase_order"] = purchase_order
            self.initial["invoice_date"] = today
            self.initial["due_date"] = today + timedelta(
                days=(purchase_order.supplier.payment_terms_days)
            )

    def clean_supplier_reference(self) -> str:
        """Normalise the supplier invoice reference."""

        return " ".join(self.cleaned_data["supplier_reference"].strip().split())

    def clean_notes(self) -> str:
        """Normalise optional invoice notes."""

        return self.cleaned_data["notes"].strip()

    def clean(self):
        """Validate dates and duplicate references."""

        cleaned_data = super().clean()

        purchase_order = cleaned_data.get("purchase_order")
        supplier_reference = cleaned_data.get("supplier_reference")
        invoice_date = cleaned_data.get("invoice_date")
        due_date = cleaned_data.get("due_date")

        if (
            invoice_date is not None
            and due_date is not None
            and due_date < invoice_date
        ):
            self.add_error(
                "due_date",
                ("The due date cannot be earlier than the supplier invoice date."),
            )

        if purchase_order is not None and supplier_reference:
            duplicate_exists = SupplierInvoice.objects.filter(
                supplier=purchase_order.supplier,
                normalized_supplier_reference=(supplier_reference.casefold()),
            ).exists()

            if duplicate_exists:
                self.add_error(
                    "supplier_reference",
                    ("This supplier invoice reference has already been recorded."),
                )

        return cleaned_data


class SupplierInvoiceLineForm(forms.Form):
    """Collect one matched supplier-invoice line."""

    goods_receipt_line = GoodsReceiptLineChoiceField(
        queryset=GoodsReceiptLine.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    quantity_invoiced = forms.DecimalField(
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
        min_value=Decimal("0.01"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        purchase_order: PurchaseOrder | None = None,
        **kwargs: Any,
    ) -> None:
        """Load uninvoiced receipt lines for one order."""

        super().__init__(*args, **kwargs)

        self.purchase_order = purchase_order

        receipt_line_field = self.fields["goods_receipt_line"]

        if not isinstance(
            receipt_line_field,
            forms.ModelChoiceField,
        ):
            return

        if purchase_order is None:
            receipt_line_field.queryset = GoodsReceiptLine.objects.none()
            return

        receipt_line_field.queryset = available_receipt_lines_queryset(
            purchase_order=purchase_order
        )

    def clean(self):
        """Validate quantity and three-way cost matching."""

        cleaned_data = super().clean()

        receipt_line = cleaned_data.get("goods_receipt_line")
        quantity_invoiced = cleaned_data.get("quantity_invoiced")
        unit_cost = cleaned_data.get("unit_cost")

        if receipt_line is None:
            return cleaned_data

        if (
            self.purchase_order is not None
            and receipt_line.goods_receipt.purchase_order_id != self.purchase_order.pk
        ):
            self.add_error(
                "goods_receipt_line",
                ("The goods receipt belongs to a different purchase order."),
            )

        available_quantity = getattr(
            receipt_line,
            "available_quantity",
            receipt_line.quantity_received,
        )

        if quantity_invoiced is not None and quantity_invoiced > available_quantity:
            self.add_error(
                "quantity_invoiced",
                ("Invoiced quantity cannot exceed the remaining received quantity."),
            )

        if unit_cost is not None and unit_cost != receipt_line.unit_cost_snapshot:
            self.add_error(
                "unit_cost",
                ("Supplier-invoice unit cost must match the received unit cost."),
            )

        return cleaned_data


class BaseSupplierInvoiceLineFormSet(BaseFormSet):
    """Validate the complete supplier-invoice line set."""

    def clean(self) -> None:
        """Require unique received-product lines."""

        super().clean()

        if any(self.errors):
            return

        receipt_line_ids: set[int] = set()
        active_line_count = 0

        for form in self.forms:
            cleaned_data = getattr(
                form,
                "cleaned_data",
                {},
            )

            if not cleaned_data:
                continue

            if cleaned_data.get("DELETE"):
                continue

            receipt_line = cleaned_data.get("goods_receipt_line")

            if receipt_line is None:
                continue

            active_line_count += 1

            if receipt_line.pk in receipt_line_ids:
                raise forms.ValidationError(
                    "A goods-receipt line cannot appear more than once."
                )

            receipt_line_ids.add(receipt_line.pk)

        if active_line_count == 0:
            raise forms.ValidationError(
                "Add at least one received product to the supplier invoice."
            )


SupplierInvoiceLineFormSet = formset_factory(
    SupplierInvoiceLineForm,
    formset=BaseSupplierInvoiceLineFormSet,
    extra=1,
    can_delete=True,
    max_num=50,
    validate_max=True,
)


class SupplierInvoicePostForm(forms.Form):
    """Confirm that a supplier invoice may be posted."""

    confirmation = forms.BooleanField(
        label=(
            "I confirm that the invoice matches the purchase order and received goods."
        ),
        required=True,
    )


class SupplierInvoiceVoidForm(forms.Form):
    """Collect a supplier-invoice void reason."""

    reason = forms.CharField(
        min_length=3,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why this supplier invoice must be voided."),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalise the invoice void reason."""

        return self.cleaned_data["reason"].strip()


class SupplierPaymentRecordForm(forms.Form):
    """Collect one payment against a supplier invoice."""

    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }
        ),
    )
    method = forms.ChoiceField(
        choices=SupplierPaymentMethod.choices,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    external_reference = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Bank, cheque, or transaction reference"),
            }
        ),
    )
    paid_at = forms.DateTimeField(
        required=False,
        input_formats=(_DATETIME_LOCAL_FORMAT,),
        widget=forms.DateTimeInput(
            format=_DATETIME_LOCAL_FORMAT,
            attrs={
                "class": "form-control",
                "type": "datetime-local",
            },
        ),
        help_text=("Leave blank to use the current date and time."),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Optional supplier-payment notes."),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        supplier_invoice: SupplierInvoice | None = None,
        **kwargs: Any,
    ) -> None:
        """Configure the payment against one balance."""

        super().__init__(*args, **kwargs)

        self.supplier_invoice = supplier_invoice
        self.outstanding_amount: Decimal | None = None

        if supplier_invoice is None or supplier_invoice.pk is None:
            return

        balance = supplier_invoice.balance
        self.outstanding_amount = balance.outstanding_amount

        amount_field = self.fields["amount"]

        if isinstance(
            amount_field,
            forms.DecimalField,
        ):
            amount_field.widget.attrs["max"] = format(
                balance.outstanding_amount,
                ".2f",
            )
            amount_field.help_text = (
                f"Outstanding balance: "
                f"{supplier_invoice.currency} "
                f"{balance.outstanding_amount:.2f}"
            )

    def clean_amount(self) -> Decimal:
        """Prevent payment above the current balance."""

        amount = self.cleaned_data["amount"]

        if self.outstanding_amount is not None and amount > self.outstanding_amount:
            raise forms.ValidationError(
                "Supplier payment cannot exceed the outstanding invoice balance."
            )

        return amount

    def clean_external_reference(self) -> str:
        """Normalise the external payment reference."""

        return self.cleaned_data["external_reference"].strip()

    def clean_paid_at(self) -> datetime | None:
        """Reject a payment time in the future."""

        paid_at = self.cleaned_data["paid_at"]

        if paid_at is None:
            return None

        if paid_at > timezone.now():
            raise forms.ValidationError(
                "Supplier-payment time cannot be in the future."
            )

        return paid_at

    def clean_notes(self) -> str:
        """Normalise optional payment notes."""

        return self.cleaned_data["notes"].strip()


class SupplierPaymentVoidForm(forms.Form):
    """Collect a supplier-payment void reason."""

    reason = forms.CharField(
        min_length=3,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why this supplier payment must be voided."),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalise the payment void reason."""

        return self.cleaned_data["reason"].strip()
