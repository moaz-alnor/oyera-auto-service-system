"""Forms used by invoice and payment browser workflows."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from django import forms
from django.utils import timezone

from apps.billing.constants import PaymentMethod
from apps.billing.models import Invoice
from apps.billing.selectors import get_invoice_balance
from apps.workshop.constants import WorkOrderStatus
from apps.workshop.models import WorkOrder

_DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class InvoiceCreateForm(forms.Form):
    """Select one completed work order for invoicing."""

    work_order = forms.ModelChoiceField(
        queryset=WorkOrder.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Optional notes to appear on the invoice."),
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Load completed work orders without invoices."""

        super().__init__(*args, **kwargs)

        work_order_field = self.fields["work_order"]

        if isinstance(
            work_order_field,
            forms.ModelChoiceField,
        ):
            work_order_field.queryset = (
                WorkOrder.objects.filter(
                    status=WorkOrderStatus.COMPLETED,
                    invoice__isnull=True,
                )
                .select_related(
                    "job_card",
                    "approved_quotation",
                )
                .order_by(
                    "-completed_at",
                    "-pk",
                )
            )


class InvoiceIssueForm(forms.Form):
    """Collect the payment due date for an invoice."""

    due_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
        help_text=("The date by which the customer should complete payment."),
    )

    def clean_due_date(self):
        """Reject a payment due date in the past."""

        due_date = self.cleaned_data["due_date"]

        if due_date < timezone.localdate():
            raise forms.ValidationError("Payment due date cannot be in the past.")

        return due_date


class InvoiceVoidForm(forms.Form):
    """Collect the reason for voiding an invoice."""

    reason = forms.CharField(
        min_length=3,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why this invoice must be voided."),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalize and require a meaningful reason."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the invoice is being voided.")

        return reason


class PaymentRecordForm(forms.Form):
    """Collect one customer payment against an invoice."""

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
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    external_reference = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": ("Receipt, transfer, or transaction reference"),
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
                "placeholder": "Optional payment notes.",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        invoice: Invoice | None = None,
        **kwargs: Any,
    ) -> None:
        """Configure the form for one invoice balance."""

        super().__init__(*args, **kwargs)

        self.invoice = invoice
        self.outstanding_amount: Decimal | None = None

        if invoice is None or invoice.pk is None:
            return

        balance = get_invoice_balance(invoice_id=invoice.pk)
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
                f"{invoice.currency} "
                f"{balance.outstanding_amount:.2f}"
            )

    def clean_amount(self) -> Decimal:
        """Prevent payment above the current balance."""

        amount = self.cleaned_data["amount"]

        if self.outstanding_amount is not None and amount > self.outstanding_amount:
            raise forms.ValidationError(
                "Payment cannot exceed the outstanding invoice balance."
            )

        return amount

    def clean_external_reference(self) -> str:
        """Normalize the optional external reference."""

        return self.cleaned_data["external_reference"].strip()

    def clean_paid_at(self) -> datetime | None:
        """Reject a payment time in the future."""

        paid_at = self.cleaned_data["paid_at"]

        if paid_at is None:
            return None

        if paid_at > timezone.now():
            raise forms.ValidationError("Payment time cannot be in the future.")

        return paid_at

    def clean_notes(self) -> str:
        """Normalize optional payment notes."""

        return self.cleaned_data["notes"].strip()


class PaymentVoidForm(forms.Form):
    """Collect the reason for voiding a payment."""

    reason = forms.CharField(
        min_length=3,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": ("Explain why this payment entry is incorrect."),
            }
        ),
    )

    def clean_reason(self) -> str:
        """Normalize and require a meaningful reason."""

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError("Record why the payment is being voided.")

        return reason
