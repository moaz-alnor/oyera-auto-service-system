"""HTTP views for invoice and payment workflows."""

from datetime import timedelta
from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.forms import BaseForm
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.decorators import (
    employee_permission_required,
)
from apps.accounts.models import User
from apps.billing.constants import (
    BillingPermissionName,
    InvoiceStatus,
    PaymentMethod,
)
from apps.billing.forms import (
    InvoiceCreateForm,
    InvoiceIssueForm,
    InvoiceVoidForm,
    PaymentRecordForm,
    PaymentVoidForm,
)
from apps.billing.models import (
    Invoice,
    Payment,
)
from apps.billing.selectors import (
    get_invoice_balance,
    get_invoice_detail,
    invoice_is_overdue,
    invoice_list_queryset,
    payment_list_queryset,
)
from apps.billing.services.invoices import (
    CreateInvoiceCommand,
    IssueInvoiceCommand,
    VoidInvoiceCommand,
    create_invoice,
    issue_invoice,
    void_invoice,
)
from apps.billing.services.payments import (
    RecordPaymentCommand,
    VoidPaymentCommand,
)
from apps.billing.services.payments import (
    record_payment as record_invoice_payment,
)
from apps.billing.services.payments import (
    void_payment as void_invoice_payment,
)
from apps.workshop.models import WorkOrder


def _add_validation_error(
    *,
    form: BaseForm,
    error: ValidationError,
) -> None:
    """Add a domain validation error to a Django form."""

    if hasattr(error, "error_dict"):
        for field_name, field_errors in error.error_dict.items():
            target_field = field_name if field_name in form.fields else None

            for field_error in field_errors:
                form.add_error(
                    target_field,
                    field_error,
                )

        return

    for message in error.messages:
        form.add_error(None, message)


def _get_invoice_or_404(
    *,
    invoice_id: int,
) -> Invoice:
    """Return one invoice or raise HTTP 404."""

    try:
        return get_invoice_detail(invoice_id=invoice_id)
    except Invoice.DoesNotExist as exc:
        raise Http404("Invoice not found.") from exc


def _get_payment_or_404(
    *,
    payment_id: int,
) -> Payment:
    """Return one payment or raise HTTP 404."""

    try:
        return Payment.objects.select_related(
            "invoice",
            "received_by",
            "voided_by",
        ).get(pk=payment_id)
    except Payment.DoesNotExist as exc:
        raise Http404("Payment not found.") from exc


def _validated_invoice_status(
    value: str,
) -> str:
    """Return a valid invoice status or an empty value."""

    valid_statuses = {choice.value for choice in InvoiceStatus}

    if value in valid_statuses:
        return value

    return ""


@employee_permission_required(BillingPermissionName.VIEW_INVOICE.value)
def invoice_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable and filterable invoices."""

    query = request.GET.get("q", "").strip()
    selected_status = _validated_invoice_status(request.GET.get("status", "").strip())

    invoices = invoice_list_queryset()

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query)
            | Q(work_order_number_snapshot__icontains=(query))
            | Q(job_number_snapshot__icontains=query)
            | Q(quotation_number_snapshot__icontains=(query))
            | Q(customer_name_snapshot__icontains=query)
            | Q(customer_phone_snapshot__icontains=query)
            | Q(vehicle_registration_snapshot__icontains=(query))
        )

    if selected_status:
        invoices = invoices.filter(status=selected_status)

    paginator = Paginator(
        invoices,
        20,
    )
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "billing/invoice_list.html",
        {
            "page": page,
            "invoices": page.object_list,
            "query": query,
            "selected_status": selected_status,
            "status_choices": InvoiceStatus.choices,
        },
    )


@employee_permission_required(BillingPermissionName.ADD_INVOICE.value)
def invoice_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create a draft invoice from completed workshop work."""

    if request.method == "POST":
        form = InvoiceCreateForm(request.POST)

        if form.is_valid():
            work_order = cast(
                WorkOrder,
                form.cleaned_data["work_order"],
            )

            try:
                invoice = create_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    work_order_id=cast(
                        int,
                        work_order.pk,
                    ),
                    command=CreateInvoiceCommand(
                        notes=form.cleaned_data["notes"],
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (f"Invoice {invoice.invoice_number} was created successfully."),
                )

                return redirect(
                    "billing:detail",
                    invoice_id=invoice.pk,
                )
    else:
        initial: dict[str, int] = {}
        work_order_value = request.GET.get(
            "work_order",
            "",
        )

        if work_order_value.isdecimal():
            initial["work_order"] = int(work_order_value)

        form = InvoiceCreateForm(initial=initial)

    return render(
        request,
        "billing/invoice_form.html",
        {
            "form": form,
        },
    )


@employee_permission_required(BillingPermissionName.VIEW_INVOICE.value)
def invoice_detail(
    request: HttpRequest,
    invoice_id: int,
) -> HttpResponse:
    """Display one invoice and its payment history."""

    invoice = _get_invoice_or_404(invoice_id=invoice_id)
    balance = get_invoice_balance(invoice_id=invoice.pk)
    payments = payment_list_queryset(invoice_id=invoice.pk)

    return render(
        request,
        "billing/invoice_detail.html",
        {
            "invoice": invoice,
            "balance": balance,
            "payments": payments,
            "is_overdue": invoice_is_overdue(invoice=invoice),
        },
    )


@employee_permission_required(BillingPermissionName.ISSUE_INVOICE.value)
def invoice_issue(
    request: HttpRequest,
    invoice_id: int,
) -> HttpResponse:
    """Issue a draft invoice to the customer."""

    invoice = _get_invoice_or_404(invoice_id=invoice_id)

    if request.method == "POST":
        form = InvoiceIssueForm(request.POST)

        if form.is_valid():
            try:
                issued_invoice = issue_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    invoice_id=invoice.pk,
                    command=IssueInvoiceCommand(
                        due_date=(form.cleaned_data["due_date"]),
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (
                        f"Invoice "
                        f"{issued_invoice.invoice_number} "
                        "was issued successfully."
                    ),
                )

                return redirect(
                    "billing:detail",
                    invoice_id=issued_invoice.pk,
                )
    else:
        form = InvoiceIssueForm(
            initial={"due_date": (timezone.localdate() + timedelta(days=14))}
        )

    return render(
        request,
        "billing/invoice_issue_form.html",
        {
            "form": form,
            "invoice": invoice,
        },
    )


@employee_permission_required(BillingPermissionName.VOID_INVOICE.value)
def invoice_void(
    request: HttpRequest,
    invoice_id: int,
) -> HttpResponse:
    """Void an unpaid issued invoice."""

    invoice = _get_invoice_or_404(invoice_id=invoice_id)

    if request.method == "POST":
        form = InvoiceVoidForm(request.POST)

        if form.is_valid():
            try:
                voided_invoice = void_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    invoice_id=invoice.pk,
                    command=VoidInvoiceCommand(
                        reason=form.cleaned_data["reason"],
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (
                        f"Invoice "
                        f"{voided_invoice.invoice_number} "
                        "was voided successfully."
                    ),
                )

                return redirect(
                    "billing:detail",
                    invoice_id=voided_invoice.pk,
                )
    else:
        form = InvoiceVoidForm()

    return render(
        request,
        "billing/invoice_void_form.html",
        {
            "form": form,
            "invoice": invoice,
        },
    )


@employee_permission_required(BillingPermissionName.RECORD_PAYMENT.value)
def payment_record(
    request: HttpRequest,
    invoice_id: int,
) -> HttpResponse:
    """Record a customer payment against an invoice."""

    invoice = _get_invoice_or_404(invoice_id=invoice_id)

    if request.method == "POST":
        form = PaymentRecordForm(
            request.POST,
            invoice=invoice,
        )

        if form.is_valid():
            payment_method = PaymentMethod(form.cleaned_data["payment_method"])

            try:
                payment = record_invoice_payment(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    invoice_id=invoice.pk,
                    command=RecordPaymentCommand(
                        amount=form.cleaned_data["amount"],
                        payment_method=payment_method,
                        external_reference=(form.cleaned_data["external_reference"]),
                        paid_at=form.cleaned_data["paid_at"],
                        notes=form.cleaned_data["notes"],
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (f"Payment {payment.payment_number} was recorded successfully."),
                )

                return redirect(
                    "billing:detail",
                    invoice_id=invoice.pk,
                )
    else:
        form = PaymentRecordForm(invoice=invoice)

    return render(
        request,
        "billing/payment_form.html",
        {
            "form": form,
            "invoice": invoice,
            "balance": get_invoice_balance(invoice_id=invoice.pk),
        },
    )


@employee_permission_required(BillingPermissionName.VOID_PAYMENT.value)
def payment_void(
    request: HttpRequest,
    payment_id: int,
) -> HttpResponse:
    """Void a posted customer payment."""

    payment = _get_payment_or_404(payment_id=payment_id)

    if request.method == "POST":
        form = PaymentVoidForm(request.POST)

        if form.is_valid():
            try:
                voided_payment = void_invoice_payment(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    payment_id=payment.pk,
                    command=VoidPaymentCommand(
                        reason=(form.cleaned_data["reason"]),
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (
                        f"Payment "
                        f"{voided_payment.payment_number} "
                        "was voided successfully."
                    ),
                )

                return redirect(
                    "billing:detail",
                    invoice_id=payment.invoice_id,
                )
    else:
        form = PaymentVoidForm()

    return render(
        request,
        "billing/payment_void_form.html",
        {
            "form": form,
            "payment": payment,
            "invoice": payment.invoice,
        },
    )
