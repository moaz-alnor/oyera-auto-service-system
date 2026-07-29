# Create your views here.
"""HTTP views for supplier-finance workflows."""

from decimal import Decimal
from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
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
from apps.purchasing.constants import (
    PurchaseOrderStatus,
    PurchasingPermissionName,
    SupplierInvoiceStatus,
    SupplierPaymentMethod,
)
from apps.purchasing.forms import (
    SupplierInvoiceCreateForm,
    SupplierInvoiceLineFormSet,
    SupplierInvoicePostForm,
    SupplierInvoiceVoidForm,
    SupplierPaymentRecordForm,
    SupplierPaymentVoidForm,
)
from apps.purchasing.models import (
    GoodsReceiptLine,
    PurchaseOrder,
    Supplier,
    SupplierInvoice,
    SupplierPayment,
)
from apps.purchasing.selectors import (
    get_supplier_invoice_by_id,
    get_supplier_payment_by_id,
    search_supplier_invoices,
)
from apps.purchasing.services.supplier_invoices import (
    CreateSupplierInvoiceCommand,
    SupplierInvoiceLineCommand,
    VoidSupplierInvoiceCommand,
    create_supplier_invoice,
    post_supplier_invoice,
    void_supplier_invoice,
)
from apps.purchasing.services.supplier_payments import (
    RecordSupplierPaymentCommand,
    VoidSupplierPaymentCommand,
    record_supplier_payment,
    void_supplier_payment,
)


def _add_validation_error(
    *,
    form: BaseForm,
    error: ValidationError,
) -> None:
    """Add a domain validation error to a form."""

    if hasattr(error, "error_dict"):
        for (
            field_name,
            field_errors,
        ) in error.error_dict.items():
            target_field = field_name if field_name in form.fields else None

            for field_error in field_errors:
                form.add_error(
                    target_field,
                    field_error,
                )

        return

    for message in error.messages:
        form.add_error(None, message)


def _get_supplier_invoice_or_404(
    *,
    supplier_invoice_id: int,
) -> SupplierInvoice:
    """Return one supplier invoice or HTTP 404."""

    try:
        return get_supplier_invoice_by_id(supplier_invoice_id=supplier_invoice_id)
    except SupplierInvoice.DoesNotExist as exc:
        raise Http404("Supplier invoice not found.") from exc


def _get_supplier_payment_or_404(
    *,
    payment_id: int,
) -> SupplierPayment:
    """Return one supplier payment or HTTP 404."""

    try:
        return get_supplier_payment_by_id(supplier_payment_id=payment_id)
    except SupplierPayment.DoesNotExist as exc:
        raise Http404("Supplier payment not found.") from exc


def _validated_invoice_status(
    value: str,
) -> str:
    """Return a valid supplier-invoice status."""

    valid_statuses = {choice.value for choice in SupplierInvoiceStatus}

    if value in valid_statuses:
        return value

    return ""


def _integer_filter(
    value: str,
) -> int | None:
    """Convert a numeric query value to an integer."""

    if value.isdecimal():
        return int(value)

    return None


def _selected_purchase_order(
    *,
    value: str,
) -> PurchaseOrder | None:
    """Return a received purchase order from a value."""

    purchase_order_id = _integer_filter(value)

    if purchase_order_id is None:
        return None

    return (
        PurchaseOrder.objects.select_related("supplier")
        .filter(
            pk=purchase_order_id,
            status__in=(
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
                PurchaseOrderStatus.RECEIVED,
            ),
        )
        .first()
    )


@employee_permission_required(PurchasingPermissionName.VIEW_SUPPLIER_INVOICE.value)
def supplier_invoice_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable supplier invoices."""

    query = request.GET.get("q", "").strip()

    selected_status = _validated_invoice_status(
        request.GET.get(
            "status",
            "",
        ).strip()
    )
    selected_supplier_id = _integer_filter(
        request.GET.get(
            "supplier",
            "",
        ).strip()
    )
    selected_purchase_order_id = _integer_filter(
        request.GET.get(
            "purchase_order",
            "",
        ).strip()
    )
    overdue_only = request.GET.get(
        "overdue",
        "",
    ) in {
        "1",
        "true",
        "yes",
    }

    invoices = search_supplier_invoices(
        query=query,
        status=selected_status,
        supplier_id=selected_supplier_id,
        purchase_order_id=(selected_purchase_order_id),
        overdue_only=overdue_only,
    )

    paginator = Paginator(
        invoices,
        20,
    )
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        ("purchasing/supplier_invoice_list.html"),
        {
            "page": page,
            "supplier_invoices": (page.object_list),
            "query": query,
            "selected_status": selected_status,
            "selected_supplier_id": (selected_supplier_id),
            "selected_purchase_order_id": (selected_purchase_order_id),
            "overdue_only": overdue_only,
            "status_choices": (SupplierInvoiceStatus.choices),
            "suppliers": (
                Supplier.objects.order_by(
                    "name",
                    "supplier_number",
                )
            ),
        },
    )


@employee_permission_required(PurchasingPermissionName.ADD_SUPPLIER_INVOICE.value)
def supplier_invoice_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create a draft invoice from received goods."""

    selected_purchase_order: PurchaseOrder | None = None

    if request.method == "POST":
        form = SupplierInvoiceCreateForm(request.POST)
        form_is_valid = form.is_valid()

        if form_is_valid:
            selected_purchase_order = cast(
                PurchaseOrder,
                form.cleaned_data["purchase_order"],
            )

        line_formset = SupplierInvoiceLineFormSet(
            request.POST,
            prefix="lines",
            form_kwargs={"purchase_order": (selected_purchase_order)},
        )
        formset_is_valid = line_formset.is_valid()

        if form_is_valid and formset_is_valid and selected_purchase_order is not None:
            line_commands: list[SupplierInvoiceLineCommand] = []

            for line_form in line_formset:
                cleaned_data = getattr(
                    line_form,
                    "cleaned_data",
                    {},
                )

                if not cleaned_data:
                    continue

                if cleaned_data.get("DELETE"):
                    continue

                receipt_line = cast(
                    GoodsReceiptLine,
                    cleaned_data["goods_receipt_line"],
                )

                line_commands.append(
                    SupplierInvoiceLineCommand(
                        goods_receipt_line_id=cast(
                            int,
                            receipt_line.pk,
                        ),
                        quantity_invoiced=(cleaned_data["quantity_invoiced"]),
                        unit_cost=cleaned_data["unit_cost"],
                    )
                )

            try:
                supplier_invoice = create_supplier_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    command=(
                        CreateSupplierInvoiceCommand(
                            purchase_order_id=cast(
                                int,
                                selected_purchase_order.pk,
                            ),
                            supplier_reference=(
                                form.cleaned_data["supplier_reference"]
                            ),
                            invoice_date=(form.cleaned_data["invoice_date"]),
                            due_date=(form.cleaned_data["due_date"]),
                            lines=tuple(line_commands),
                            tax_amount=(form.cleaned_data["tax_amount"]),
                            other_charges=(form.cleaned_data["other_charges"]),
                            notes=(form.cleaned_data["notes"]),
                        )
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
                        "Supplier invoice "
                        f"{supplier_invoice.supplier_invoice_number} "
                        "was created successfully."
                    ),
                )

                return redirect(
                    ("purchasing:supplier_invoice_detail"),
                    supplier_invoice_id=(supplier_invoice.pk),
                )
    else:
        selected_purchase_order = _selected_purchase_order(
            value=request.GET.get(
                "purchase_order",
                "",
            )
        )

        form = SupplierInvoiceCreateForm(purchase_order=(selected_purchase_order))
        line_formset = SupplierInvoiceLineFormSet(
            prefix="lines",
            form_kwargs={"purchase_order": (selected_purchase_order)},
        )

    return render(
        request,
        "purchasing/supplier_invoice_form.html",
        {
            "form": form,
            "line_formset": line_formset,
            "selected_purchase_order": (selected_purchase_order),
        },
    )


@employee_permission_required(PurchasingPermissionName.VIEW_SUPPLIER_INVOICE.value)
def supplier_invoice_detail(
    request: HttpRequest,
    supplier_invoice_id: int,
) -> HttpResponse:
    """Display one invoice and payment history."""

    supplier_invoice = _get_supplier_invoice_or_404(
        supplier_invoice_id=(supplier_invoice_id)
    )

    paid_amount = getattr(
        supplier_invoice,
        "paid_amount",
        Decimal("0.00"),
    )
    outstanding_amount = getattr(
        supplier_invoice,
        "outstanding_amount",
        supplier_invoice.total,
    )

    is_overdue = (
        supplier_invoice.due_date < timezone.localdate()
        and supplier_invoice.status
        in {
            SupplierInvoiceStatus.POSTED,
            SupplierInvoiceStatus.PARTIALLY_PAID,
        }
    )

    return render(
        request,
        ("purchasing/supplier_invoice_detail.html"),
        {
            "supplier_invoice": (supplier_invoice),
            "invoice_lines": (supplier_invoice.lines.all()),
            "payments": (supplier_invoice.payments.all()),
            "paid_amount": paid_amount,
            "outstanding_amount": (outstanding_amount),
            "is_overdue": is_overdue,
        },
    )


@employee_permission_required(PurchasingPermissionName.POST_SUPPLIER_INVOICE.value)
def supplier_invoice_post(
    request: HttpRequest,
    supplier_invoice_id: int,
) -> HttpResponse:
    """Post a matched draft supplier invoice."""

    supplier_invoice = _get_supplier_invoice_or_404(
        supplier_invoice_id=(supplier_invoice_id)
    )

    if request.method == "POST":
        form = SupplierInvoicePostForm(request.POST)

        if form.is_valid():
            try:
                posted_invoice = post_supplier_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    supplier_invoice_id=(supplier_invoice.pk),
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
                        "Supplier invoice "
                        f"{posted_invoice.supplier_invoice_number} "
                        "was posted successfully."
                    ),
                )

                return redirect(
                    ("purchasing:supplier_invoice_detail"),
                    supplier_invoice_id=(posted_invoice.pk),
                )
    else:
        form = SupplierInvoicePostForm()

    return render(
        request,
        ("purchasing/supplier_invoice_post_form.html"),
        {
            "form": form,
            "supplier_invoice": (supplier_invoice),
        },
    )


@employee_permission_required(PurchasingPermissionName.VOID_SUPPLIER_INVOICE.value)
def supplier_invoice_void(
    request: HttpRequest,
    supplier_invoice_id: int,
) -> HttpResponse:
    """Void an unpaid posted supplier invoice."""

    supplier_invoice = _get_supplier_invoice_or_404(
        supplier_invoice_id=(supplier_invoice_id)
    )

    if request.method == "POST":
        form = SupplierInvoiceVoidForm(request.POST)

        if form.is_valid():
            try:
                voided_invoice = void_supplier_invoice(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    supplier_invoice_id=(supplier_invoice.pk),
                    command=(
                        VoidSupplierInvoiceCommand(reason=(form.cleaned_data["reason"]))
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
                        "Supplier invoice "
                        f"{voided_invoice.supplier_invoice_number} "
                        "was voided successfully."
                    ),
                )

                return redirect(
                    ("purchasing:supplier_invoice_detail"),
                    supplier_invoice_id=(voided_invoice.pk),
                )
    else:
        form = SupplierInvoiceVoidForm()

    return render(
        request,
        ("purchasing/supplier_invoice_void_form.html"),
        {
            "form": form,
            "supplier_invoice": (supplier_invoice),
        },
    )


@employee_permission_required(PurchasingPermissionName.RECORD_SUPPLIER_PAYMENT.value)
def supplier_payment_record(
    request: HttpRequest,
    supplier_invoice_id: int,
) -> HttpResponse:
    """Record a payment against a supplier invoice."""

    supplier_invoice = _get_supplier_invoice_or_404(
        supplier_invoice_id=(supplier_invoice_id)
    )

    if request.method == "POST":
        form = SupplierPaymentRecordForm(
            request.POST,
            supplier_invoice=(supplier_invoice),
        )

        if form.is_valid():
            method = SupplierPaymentMethod(form.cleaned_data["method"])

            try:
                payment = record_supplier_payment(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    supplier_invoice_id=(supplier_invoice.pk),
                    command=(
                        RecordSupplierPaymentCommand(
                            amount=(form.cleaned_data["amount"]),
                            method=method,
                            external_reference=(
                                form.cleaned_data["external_reference"]
                            ),
                            paid_at=(form.cleaned_data["paid_at"]),
                            notes=(form.cleaned_data["notes"]),
                        )
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
                        "Supplier payment "
                        f"{payment.payment_number} "
                        "was recorded successfully."
                    ),
                )

                return redirect(
                    ("purchasing:supplier_invoice_detail"),
                    supplier_invoice_id=(supplier_invoice.pk),
                )
    else:
        form = SupplierPaymentRecordForm(supplier_invoice=supplier_invoice)

    return render(
        request,
        "purchasing/supplier_payment_form.html",
        {
            "form": form,
            "supplier_invoice": (supplier_invoice),
            "balance": (supplier_invoice.balance),
        },
    )


@employee_permission_required(PurchasingPermissionName.VOID_SUPPLIER_PAYMENT.value)
def supplier_payment_void(
    request: HttpRequest,
    payment_id: int,
) -> HttpResponse:
    """Void a posted supplier payment."""

    payment = _get_supplier_payment_or_404(payment_id=payment_id)
    supplier_invoice = payment.supplier_invoice

    if request.method == "POST":
        form = SupplierPaymentVoidForm(request.POST)

        if form.is_valid():
            try:
                voided_payment = void_supplier_payment(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    payment_id=payment.pk,
                    command=(
                        VoidSupplierPaymentCommand(reason=(form.cleaned_data["reason"]))
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
                        "Supplier payment "
                        f"{voided_payment.payment_number} "
                        "was voided successfully."
                    ),
                )

                return redirect(
                    ("purchasing:supplier_invoice_detail"),
                    supplier_invoice_id=(supplier_invoice.pk),
                )
    else:
        form = SupplierPaymentVoidForm()

    return render(
        request,
        ("purchasing/supplier_payment_void_form.html"),
        {
            "form": form,
            "payment": payment,
            "supplier_invoice": (supplier_invoice),
        },
    )
