"""HTTP views for purchasing workflows."""

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
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

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
    GoodsReceiptHeaderForm,
    GoodsReceiptLineFormSet,
    PurchaseOrderApprovalForm,
    PurchaseOrderCancellationForm,
    PurchaseOrderCreateForm,
    PurchaseOrderLineCreateForm,
    PurchaseOrderLineUpdateForm,
    PurchaseOrderSubmitForm,
    PurchaseOrderUpdateForm,
    SupplierInvoiceCreateForm,
    SupplierInvoiceLineFormSet,
    SupplierInvoicePostForm,
    SupplierInvoiceVoidForm,
    SupplierPaymentRecordForm,
    SupplierPaymentVoidForm,
    SupplierRegistrationForm,
    SupplierUpdateForm,
)
from apps.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    SupplierInvoice,
    SupplierPayment,
)
from apps.purchasing.selectors import (
    find_possible_supplier_duplicates,
    get_goods_receipt_by_id,
    get_goods_receipt_movements,
    get_goods_receipts_for_purchase_order,
    get_purchase_order_by_id,
    get_purchase_order_line_by_id,
    get_purchase_orders_for_supplier,
    get_supplier_by_id,
    get_supplier_invoice_by_id,
    get_supplier_invoices_for_supplier,
    get_supplier_payment_by_id,
    search_goods_receipts,
    search_purchase_orders,
    search_supplier_invoices,
    search_suppliers,
)
from apps.purchasing.services.purchase_orders import (
    AddPurchaseOrderLineCommand,
    CancelPurchaseOrderCommand,
    CreatePurchaseOrderCommand,
    UpdatePurchaseOrderCommand,
    UpdatePurchaseOrderLineCommand,
    add_purchase_order_line,
    approve_purchase_order,
    cancel_purchase_order,
    create_purchase_order,
    remove_purchase_order_line,
    submit_purchase_order,
    update_purchase_order,
    update_purchase_order_line,
)
from apps.purchasing.services.receipts import (
    GoodsReceiptLineCommand,
    ReceivePurchaseOrderCommand,
    receive_purchase_order,
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
from apps.purchasing.services.suppliers import (
    RegisterSupplierCommand,
    UpdateSupplierCommand,
    deactivate_supplier,
    reactivate_supplier,
    register_supplier,
    update_supplier,
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


def _get_supplier_or_404(
    *,
    supplier_id: int,
) -> Supplier:
    """Return one supplier or raise HTTP 404."""

    try:
        return get_supplier_by_id(supplier_id=supplier_id)
    except Supplier.DoesNotExist as exc:
        raise Http404("Supplier not found.") from exc


@employee_permission_required(PurchasingPermissionName.VIEW_SUPPLIER.value)
def supplier_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable supplier records."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"

    suppliers = search_suppliers(
        query=query,
        include_inactive=include_inactive,
    )

    paginator = Paginator(suppliers, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "purchasing/supplier_list.html",
        {
            "page": page,
            "suppliers": page.object_list,
            "query": query,
            "include_inactive": include_inactive,
        },
    )


@employee_permission_required(PurchasingPermissionName.ADD_SUPPLIER.value)
def supplier_create(
    request: HttpRequest,
) -> HttpResponse:
    """Register a supplier after duplicate review."""

    duplicate_confirmation_required = False
    possible_duplicates = Supplier.objects.none()

    if request.method == "POST":
        form = SupplierRegistrationForm(request.POST)

        if form.is_valid():
            possible_duplicates = find_possible_supplier_duplicates(
                code=form.cleaned_data["code"],
                name=form.cleaned_data["name"],
                phone_number=(form.cleaned_data["phone_number"]),
                email=form.cleaned_data["email"],
                tax_identifier=(form.cleaned_data["tax_identifier"]),
            )

            duplicate_confirmed = form.cleaned_data["confirm_duplicate"]

            if possible_duplicates.exists() and not duplicate_confirmed:
                duplicate_confirmation_required = True
            else:
                try:
                    supplier = register_supplier(
                        actor=cast(
                            User,
                            request.user,
                        ),
                        command=RegisterSupplierCommand(
                            code=form.cleaned_data["code"],
                            name=form.cleaned_data["name"],
                            contact_name=(form.cleaned_data["contact_name"]),
                            phone_number=(form.cleaned_data["phone_number"]),
                            email=form.cleaned_data["email"],
                            address=form.cleaned_data["address"],
                            tax_identifier=(form.cleaned_data["tax_identifier"]),
                            payment_terms_days=(
                                form.cleaned_data["payment_terms_days"]
                            ),
                            preferred_currency=(
                                form.cleaned_data["preferred_currency"]
                            ),
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
                        (
                            "Supplier "
                            f"{supplier.supplier_number} "
                            "was registered successfully."
                        ),
                    )

                    return redirect(
                        ("purchasing:supplier_detail"),
                        supplier_id=supplier.pk,
                    )
    else:
        form = SupplierRegistrationForm()

    return render(
        request,
        "purchasing/supplier_form.html",
        {
            "form": form,
            "page_title": "Register supplier",
            "page_description": (
                "Review possible duplicate records before registering a supplier."
            ),
            "submit_label": "Register supplier",
            "cancel_url": reverse("purchasing:supplier_list"),
            "possible_duplicates": (possible_duplicates),
            "duplicate_confirmation_required": (duplicate_confirmation_required),
        },
    )


@employee_permission_required(PurchasingPermissionName.VIEW_SUPPLIER.value)
def supplier_detail(
    request: HttpRequest,
    supplier_id: int,
) -> HttpResponse:
    """Display one supplier and related records."""

    supplier = _get_supplier_or_404(supplier_id=supplier_id)

    return render(
        request,
        "purchasing/supplier_detail.html",
        {
            "supplier": supplier,
            "purchase_orders": (
                get_purchase_orders_for_supplier(supplier_id=supplier_id)[:10]
            ),
            "supplier_invoices": (
                get_supplier_invoices_for_supplier(supplier_id=supplier_id)[:10]
            ),
        },
    )


@employee_permission_required(PurchasingPermissionName.CHANGE_SUPPLIER.value)
def supplier_update(
    request: HttpRequest,
    supplier_id: int,
) -> HttpResponse:
    """Update supplier information after duplicate review."""

    supplier = _get_supplier_or_404(supplier_id=supplier_id)
    duplicate_confirmation_required = False
    possible_duplicates = Supplier.objects.none()

    if request.method == "POST":
        form = SupplierUpdateForm(
            request.POST,
            instance=supplier,
        )

        if form.is_valid():
            possible_duplicates = find_possible_supplier_duplicates(
                code=form.cleaned_data["code"],
                name=form.cleaned_data["name"],
                phone_number=(form.cleaned_data["phone_number"]),
                email=form.cleaned_data["email"],
                tax_identifier=(form.cleaned_data["tax_identifier"]),
                exclude_supplier_id=supplier_id,
            )

            duplicate_confirmed = form.cleaned_data["confirm_duplicate"]

            if possible_duplicates.exists() and not duplicate_confirmed:
                duplicate_confirmation_required = True
            else:
                try:
                    updated_supplier = update_supplier(
                        actor=cast(
                            User,
                            request.user,
                        ),
                        supplier_id=supplier_id,
                        command=UpdateSupplierCommand(
                            code=form.cleaned_data["code"],
                            name=form.cleaned_data["name"],
                            contact_name=(form.cleaned_data["contact_name"]),
                            phone_number=(form.cleaned_data["phone_number"]),
                            email=form.cleaned_data["email"],
                            address=form.cleaned_data["address"],
                            tax_identifier=(form.cleaned_data["tax_identifier"]),
                            payment_terms_days=(
                                form.cleaned_data["payment_terms_days"]
                            ),
                            preferred_currency=(
                                form.cleaned_data["preferred_currency"]
                            ),
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
                        (
                            "Supplier "
                            f"{updated_supplier.supplier_number} "
                            "was updated successfully."
                        ),
                    )

                    return redirect(
                        ("purchasing:supplier_detail"),
                        supplier_id=supplier_id,
                    )
    else:
        form = SupplierUpdateForm(instance=supplier)

    return render(
        request,
        "purchasing/supplier_form.html",
        {
            "form": form,
            "supplier": supplier,
            "page_title": "Edit supplier",
            "page_description": (
                "Update the supplier's contact, payment and business information."
            ),
            "submit_label": "Save changes",
            "cancel_url": reverse(
                "purchasing:supplier_detail",
                args=(supplier_id,),
            ),
            "possible_duplicates": (possible_duplicates),
            "duplicate_confirmation_required": (duplicate_confirmation_required),
        },
    )


@employee_permission_required(PurchasingPermissionName.DEACTIVATE_SUPPLIER.value)
@require_POST
def supplier_deactivate(
    request: HttpRequest,
    supplier_id: int,
) -> HttpResponse:
    """Deactivate a supplier while preserving history."""

    _get_supplier_or_404(supplier_id=supplier_id)

    try:
        supplier = deactivate_supplier(
            actor=cast(
                User,
                request.user,
            ),
            supplier_id=supplier_id,
        )
    except ValidationError as error:
        messages.error(
            request,
            " ".join(error.messages),
        )
    else:
        messages.success(
            request,
            (f"Supplier {supplier.supplier_number} was deactivated."),
        )

    return redirect(
        "purchasing:supplier_detail",
        supplier_id=supplier_id,
    )


@employee_permission_required(PurchasingPermissionName.REACTIVATE_SUPPLIER.value)
@require_POST
def supplier_reactivate(
    request: HttpRequest,
    supplier_id: int,
) -> HttpResponse:
    """Reactivate an inactive supplier."""

    _get_supplier_or_404(supplier_id=supplier_id)

    supplier = reactivate_supplier(
        actor=cast(
            User,
            request.user,
        ),
        supplier_id=supplier_id,
    )

    messages.success(
        request,
        (f"Supplier {supplier.supplier_number} was reactivated."),
    )

    return redirect(
        "purchasing:supplier_detail",
        supplier_id=supplier_id,
    )


def _get_purchase_order_or_404(
    *,
    purchase_order_id: int,
) -> PurchaseOrder:
    """Return one purchase order or raise HTTP 404."""

    try:
        return get_purchase_order_by_id(purchase_order_id=purchase_order_id)
    except PurchaseOrder.DoesNotExist as exc:
        raise Http404("Purchase order not found.") from exc


def _validated_purchase_order_status(
    value: str,
) -> str:
    """Return a recognised purchase-order status."""

    valid_statuses = {choice.value for choice in PurchaseOrderStatus}

    if value in valid_statuses:
        return value

    return ""


@employee_permission_required(PurchasingPermissionName.VIEW_PURCHASE_ORDER.value)
def purchase_order_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable purchase-order records."""

    query = request.GET.get("q", "").strip()
    selected_status = _validated_purchase_order_status(request.GET.get("status", ""))
    selected_supplier_id = _integer_filter(request.GET.get("supplier", ""))

    purchase_orders = search_purchase_orders(
        query=query,
        status=selected_status,
        supplier_id=selected_supplier_id,
    )

    paginator = Paginator(
        purchase_orders,
        20,
    )
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "purchasing/purchase_order_list.html",
        {
            "page": page,
            "purchase_orders": page.object_list,
            "query": query,
            "selected_status": selected_status,
            "selected_supplier_id": (selected_supplier_id),
            "status_choices": (PurchaseOrderStatus.choices),
            "suppliers": search_suppliers(include_inactive=True),
        },
    )


@employee_permission_required(PurchasingPermissionName.ADD_PURCHASE_ORDER.value)
def purchase_order_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create one draft purchase order."""

    if request.method == "POST":
        form = PurchaseOrderCreateForm(request.POST)

        if form.is_valid():
            supplier = form.cleaned_data["supplier"]

            try:
                purchase_order = create_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    command=(
                        CreatePurchaseOrderCommand(
                            supplier_id=supplier.pk,
                            currency=(form.cleaned_data["currency"]),
                            discount_percentage=(
                                form.cleaned_data["discount_percentage"]
                            ),
                            tax_percentage=(form.cleaned_data["tax_percentage"]),
                            delivery_cost=(form.cleaned_data["delivery_cost"]),
                            expected_delivery_date=(
                                form.cleaned_data["expected_delivery_date"]
                            ),
                            supplier_reference=(
                                form.cleaned_data["supplier_reference"]
                            ),
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
                        "Purchase order "
                        f"{purchase_order.purchase_order_number} "
                        "was created successfully."
                    ),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order.pk),
                )
    else:
        initial: dict[str, object] = {}

        selected_supplier_id = _integer_filter(request.GET.get("supplier", ""))

        if selected_supplier_id is not None:
            try:
                selected_supplier = get_supplier_by_id(
                    supplier_id=(selected_supplier_id)
                )
            except Supplier.DoesNotExist:
                selected_supplier = None

            if selected_supplier is not None and selected_supplier.is_active:
                initial["supplier"] = selected_supplier
                initial["currency"] = selected_supplier.preferred_currency

        form = PurchaseOrderCreateForm(initial=initial)

    return render(
        request,
        "purchasing/purchase_order_form.html",
        {
            "form": form,
            "page_title": ("Create purchase order"),
            "page_description": (
                "Create a draft purchase order before adding products."
            ),
            "submit_label": ("Create purchase order"),
            "cancel_url": reverse("purchasing:purchase_order_list"),
        },
    )


@employee_permission_required(PurchasingPermissionName.VIEW_PURCHASE_ORDER.value)
def purchase_order_detail(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Display one purchase order and its lines."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=(purchase_order_id))

    return render(
        request,
        "purchasing/purchase_order_detail.html",
        {
            "purchase_order": purchase_order,
            "purchase_order_lines": (purchase_order.lines.all()),
            "goods_receipts": (
                get_goods_receipts_for_purchase_order(
                    purchase_order_id=(purchase_order_id)
                )
            ),
            "totals": purchase_order.totals,
        },
    )


@employee_permission_required(PurchasingPermissionName.CHANGE_PURCHASE_ORDER.value)
def purchase_order_update(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Update one draft purchase-order header."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=(purchase_order_id))

    if request.method == "POST":
        form = PurchaseOrderUpdateForm(
            request.POST,
            instance=purchase_order,
        )

        if form.is_valid():
            supplier = form.cleaned_data["supplier"]

            try:
                updated_purchase_order = update_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_id=(purchase_order_id),
                    command=(
                        UpdatePurchaseOrderCommand(
                            supplier_id=supplier.pk,
                            currency=(form.cleaned_data["currency"]),
                            discount_percentage=(
                                form.cleaned_data["discount_percentage"]
                            ),
                            tax_percentage=(form.cleaned_data["tax_percentage"]),
                            delivery_cost=(form.cleaned_data["delivery_cost"]),
                            expected_delivery_date=(
                                form.cleaned_data["expected_delivery_date"]
                            ),
                            supplier_reference=(
                                form.cleaned_data["supplier_reference"]
                            ),
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
                        "Purchase order "
                        f"{updated_purchase_order.purchase_order_number} "
                        "was updated successfully."
                    ),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order_id),
                )
    else:
        form = PurchaseOrderUpdateForm(instance=purchase_order)

    return render(
        request,
        "purchasing/purchase_order_form.html",
        {
            "form": form,
            "purchase_order": purchase_order,
            "page_title": ("Edit purchase order"),
            "page_description": (
                "Update the supplier, pricing, delivery and reference details."
            ),
            "submit_label": "Save changes",
            "cancel_url": reverse(
                "purchasing:purchase_order_detail",
                args=(purchase_order_id,),
            ),
        },
    )


def _get_purchase_order_line_or_404(
    *,
    purchase_order_line_id: int,
) -> PurchaseOrderLine:
    """Return one purchase-order line or HTTP 404."""

    try:
        return get_purchase_order_line_by_id(
            purchase_order_line_id=(purchase_order_line_id)
        )
    except PurchaseOrderLine.DoesNotExist as exc:
        raise Http404("Purchase-order line not found.") from exc


@employee_permission_required(PurchasingPermissionName.CHANGE_PURCHASE_ORDER.value)
def purchase_order_line_add(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Add one product to a draft purchase order."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=purchase_order_id)

    if request.method == "POST":
        form = PurchaseOrderLineCreateForm(
            request.POST,
            purchase_order=purchase_order,
        )

        if form.is_valid():
            product = form.cleaned_data["product"]

            try:
                line = add_purchase_order_line(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_id=(purchase_order_id),
                    command=(
                        AddPurchaseOrderLineCommand(
                            product_id=product.pk,
                            quantity_ordered=(form.cleaned_data["quantity_ordered"]),
                            unit_cost=(form.cleaned_data["unit_cost"]),
                            description_override=(
                                form.cleaned_data["description_override"]
                            ),
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
                    (f"{line.product_name_snapshot} was added to the purchase order."),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order_id),
                )
    else:
        form = PurchaseOrderLineCreateForm(purchase_order=purchase_order)

    return render(
        request,
        ("purchasing/purchase_order_line_form.html"),
        {
            "form": form,
            "purchase_order": purchase_order,
            "page_title": "Add product",
            "page_description": (
                "Select a product and record the supplier quantity and unit cost."
            ),
            "submit_label": "Add product",
            "cancel_url": reverse(
                "purchasing:purchase_order_detail",
                args=(purchase_order_id,),
            ),
        },
    )


@employee_permission_required(PurchasingPermissionName.CHANGE_PURCHASE_ORDER.value)
def purchase_order_line_update(
    request: HttpRequest,
    purchase_order_line_id: int,
) -> HttpResponse:
    """Update quantity, cost and description."""

    line = _get_purchase_order_line_or_404(
        purchase_order_line_id=(purchase_order_line_id)
    )
    purchase_order = line.purchase_order

    if request.method == "POST":
        form = PurchaseOrderLineUpdateForm(request.POST)

        if form.is_valid():
            try:
                updated_line = update_purchase_order_line(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_line_id=(purchase_order_line_id),
                    command=(
                        UpdatePurchaseOrderLineCommand(
                            quantity_ordered=(form.cleaned_data["quantity_ordered"]),
                            unit_cost=(form.cleaned_data["unit_cost"]),
                            description_override=(
                                form.cleaned_data["description_override"]
                            ),
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
                    (f"{updated_line.product_name_snapshot} was updated successfully."),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order.pk),
                )
    else:
        form = PurchaseOrderLineUpdateForm(
            initial={
                "quantity_ordered": (line.quantity_ordered),
                "unit_cost": line.unit_cost,
                "description_override": (line.description_snapshot),
            }
        )

    return render(
        request,
        ("purchasing/purchase_order_line_form.html"),
        {
            "form": form,
            "purchase_order": purchase_order,
            "purchase_order_line": line,
            "page_title": "Edit product line",
            "page_description": (
                "Update the supplier quantity, unit cost or description."
            ),
            "submit_label": "Save line changes",
            "cancel_url": reverse(
                "purchasing:purchase_order_detail",
                args=(purchase_order.pk,),
            ),
        },
    )


@employee_permission_required(PurchasingPermissionName.CHANGE_PURCHASE_ORDER.value)
def purchase_order_line_remove(
    request: HttpRequest,
    purchase_order_line_id: int,
) -> HttpResponse:
    """Remove one product from a draft order."""

    line = _get_purchase_order_line_or_404(
        purchase_order_line_id=(purchase_order_line_id)
    )
    purchase_order = line.purchase_order

    if request.method == "POST":
        product_name = line.product_name_snapshot

        try:
            remove_purchase_order_line(
                actor=cast(
                    User,
                    request.user,
                ),
                purchase_order_line_id=(purchase_order_line_id),
            )
        except ValidationError as error:
            messages.error(
                request,
                " ".join(error.messages),
            )
        else:
            messages.success(
                request,
                (f"{product_name} was removed from the purchase order."),
            )

        return redirect(
            "purchasing:purchase_order_detail",
            purchase_order_id=(purchase_order.pk),
        )

    return render(
        request,
        ("purchasing/purchase_order_line_remove_form.html"),
        {
            "purchase_order": purchase_order,
            "purchase_order_line": line,
        },
    )


@employee_permission_required(PurchasingPermissionName.SUBMIT_PURCHASE_ORDER.value)
def purchase_order_submit(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Submit a completed draft for approval."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=purchase_order_id)

    if request.method == "POST":
        form = PurchaseOrderSubmitForm(request.POST)

        if form.is_valid():
            try:
                submitted_purchase_order = submit_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_id=(purchase_order_id),
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
                        "Purchase order "
                        f"{submitted_purchase_order.purchase_order_number} "
                        "was submitted for approval."
                    ),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order_id),
                )
    else:
        form = PurchaseOrderSubmitForm()

    return render(
        request,
        ("purchasing/purchase_order_submit_form.html"),
        {
            "form": form,
            "purchase_order": purchase_order,
            "totals": purchase_order.totals,
        },
    )


@employee_permission_required(PurchasingPermissionName.APPROVE_PURCHASE_ORDER.value)
def purchase_order_approve(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Approve one submitted purchase order."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=purchase_order_id)

    if request.method == "POST":
        form = PurchaseOrderApprovalForm(request.POST)

        if form.is_valid():
            try:
                approved_purchase_order = approve_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_id=(purchase_order_id),
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
                        "Purchase order "
                        f"{approved_purchase_order.purchase_order_number} "
                        "was approved successfully."
                    ),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order_id),
                )
    else:
        form = PurchaseOrderApprovalForm()

    return render(
        request,
        ("purchasing/purchase_order_approval_form.html"),
        {
            "form": form,
            "purchase_order": purchase_order,
            "totals": purchase_order.totals,
        },
    )


@employee_permission_required(PurchasingPermissionName.CANCEL_PURCHASE_ORDER.value)
def purchase_order_cancel(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Cancel an unreceived purchase order."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=purchase_order_id)

    if request.method == "POST":
        form = PurchaseOrderCancellationForm(request.POST)

        if form.is_valid():
            try:
                cancelled_purchase_order = cancel_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    purchase_order_id=(purchase_order_id),
                    command=(
                        CancelPurchaseOrderCommand(
                            reason=(form.cleaned_data["reason"]),
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
                        "Purchase order "
                        f"{cancelled_purchase_order.purchase_order_number} "
                        "was cancelled."
                    ),
                )

                return redirect(
                    "purchasing:purchase_order_detail",
                    purchase_order_id=(purchase_order_id),
                )
    else:
        form = PurchaseOrderCancellationForm()

    return render(
        request,
        ("purchasing/purchase_order_cancellation_form.html"),
        {
            "form": form,
            "purchase_order": purchase_order,
            "totals": purchase_order.totals,
        },
    )


def _get_goods_receipt_or_404(
    *,
    goods_receipt_id: int,
) -> GoodsReceipt:
    """Return one goods receipt or HTTP 404."""

    try:
        return get_goods_receipt_by_id(goods_receipt_id=(goods_receipt_id))
    except GoodsReceipt.DoesNotExist as exc:
        raise Http404("Goods receipt not found.") from exc


@employee_permission_required(PurchasingPermissionName.VIEW_GOODS_RECEIPT.value)
def goods_receipt_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable goods-receipt records."""

    query = request.GET.get("q", "").strip()
    selected_purchase_order_id = _integer_filter(
        request.GET.get(
            "purchase_order",
            "",
        )
    )
    selected_supplier_id = _integer_filter(request.GET.get("supplier", ""))

    goods_receipts = search_goods_receipts(
        query=query,
        purchase_order_id=(selected_purchase_order_id),
        supplier_id=selected_supplier_id,
    )

    paginator = Paginator(
        goods_receipts,
        20,
    )
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        ("purchasing/goods_receipt_list.html"),
        {
            "page": page,
            "goods_receipts": page.object_list,
            "query": query,
            "selected_purchase_order_id": (selected_purchase_order_id),
            "selected_supplier_id": (selected_supplier_id),
            "purchase_orders": (search_purchase_orders()),
            "suppliers": search_suppliers(include_inactive=True),
        },
    )


@employee_permission_required(PurchasingPermissionName.RECEIVE_PURCHASE_ORDER.value)
def goods_receipt_create(
    request: HttpRequest,
    purchase_order_id: int,
) -> HttpResponse:
    """Record one supplier delivery into Inventory."""

    purchase_order = _get_purchase_order_or_404(purchase_order_id=(purchase_order_id))

    if request.method == "POST":
        header_form = GoodsReceiptHeaderForm(request.POST)
        line_formset = GoodsReceiptLineFormSet(
            request.POST,
            purchase_order=purchase_order,
            prefix="lines",
        )

        if header_form.is_valid() and line_formset.is_valid():
            receipt_line_commands: list[GoodsReceiptLineCommand] = []

            for line_form in line_formset.forms:
                line_data = getattr(
                    line_form,
                    "cleaned_data",
                    {},
                )

                if not line_data.get("receive"):
                    continue

                purchase_order_line_id = line_data.get("purchase_order_line_id")
                inventory_item = line_data.get("inventory_item")
                quantity_received = line_data.get("quantity_received")

                if (
                    purchase_order_line_id is None
                    or inventory_item is None
                    or quantity_received is None
                ):
                    continue

                receipt_line_commands.append(
                    GoodsReceiptLineCommand(
                        purchase_order_line_id=(purchase_order_line_id),
                        inventory_item_id=(inventory_item.pk),
                        quantity_received=(quantity_received),
                    )
                )

            try:
                goods_receipt = receive_purchase_order(
                    actor=cast(
                        User,
                        request.user,
                    ),
                    command=(
                        ReceivePurchaseOrderCommand(
                            purchase_order_id=(purchase_order_id),
                            lines=tuple(receipt_line_commands),
                            supplier_delivery_reference=(
                                header_form.cleaned_data["supplier_delivery_reference"]
                            ),
                            received_at=(header_form.cleaned_data["received_at"]),
                            notes=(header_form.cleaned_data["notes"]),
                        )
                    ),
                )
            except ValidationError as error:
                _add_validation_error(
                    form=header_form,
                    error=error,
                )
            else:
                messages.success(
                    request,
                    (
                        "Goods receipt "
                        f"{goods_receipt.goods_receipt_number} "
                        "was posted to Inventory."
                    ),
                )

                return redirect(
                    "purchasing:goods_receipt_detail",
                    goods_receipt_id=(goods_receipt.pk),
                )
    else:
        header_form = GoodsReceiptHeaderForm()
        line_formset = GoodsReceiptLineFormSet(
            purchase_order=purchase_order,
            prefix="lines",
        )

    return render(
        request,
        ("purchasing/goods_receipt_form.html"),
        {
            "header_form": header_form,
            "line_formset": line_formset,
            "purchase_order": purchase_order,
            "totals": purchase_order.totals,
        },
    )


@employee_permission_required(PurchasingPermissionName.VIEW_GOODS_RECEIPT.value)
def goods_receipt_detail(
    request: HttpRequest,
    goods_receipt_id: int,
) -> HttpResponse:
    """Display one receipt and its inventory audit."""

    goods_receipt = _get_goods_receipt_or_404(goods_receipt_id=(goods_receipt_id))

    return render(
        request,
        ("purchasing/goods_receipt_detail.html"),
        {
            "goods_receipt": goods_receipt,
            "goods_receipt_lines": (goods_receipt.lines.all()),
            "stock_movements": (
                get_goods_receipt_movements(goods_receipt_id=(goods_receipt_id))
            ),
        },
    )


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
