"""HTTP views for quotation and customer-approval workflows."""

from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.jobs.models import JobCard
from apps.product_catalogue.models import Product
from apps.quotations.calculations import (
    calculate_quotation_totals,
)
from apps.quotations.constants import (
    CustomerDecisionMethod,
    QuotationPermissionName,
    QuotationStatus,
)
from apps.quotations.forms import (
    CustomerDecisionForm,
    ProductLineCreateForm,
    QuotationCreateForm,
    ServiceLineCreateForm,
)
from apps.quotations.models import Quotation
from apps.quotations.selectors import (
    get_quotation_by_id,
    get_quotation_history_for_job,
    search_quotations,
)
from apps.quotations.services.quotations import (
    AddProductLineCommand,
    AddServiceLineCommand,
    CreateQuotationCommand,
    RecordCustomerDecisionCommand,
    add_product_line,
    add_service_line,
    approve_quotation,
    create_quotation,
    create_quotation_revision,
    reject_quotation,
    submit_quotation,
)
from apps.service_catalogue.models import Service


def _get_quotation_or_404(
    *,
    quotation_id: int,
) -> Quotation:
    """Return a quotation or raise HTTP 404."""

    try:
        return get_quotation_by_id(quotation_id=quotation_id)
    except Quotation.DoesNotExist as exc:
        raise Http404("Quotation not found.") from exc


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
                form.add_error(target_field, field_error)

        return

    for message in error.messages:
        form.add_error(None, message)


def _add_validation_messages(
    *,
    request: HttpRequest,
    error: ValidationError,
) -> None:
    """Display a domain validation error using Django messages."""

    if hasattr(error, "message_dict"):
        for field_messages in error.message_dict.values():
            for message in field_messages:
                messages.error(request, message)

        return

    for message in error.messages:
        messages.error(request, message)


def _validated_status(value: str) -> str:
    """Return a recognized quotation status or an empty value."""

    allowed_statuses = {choice.value for choice in QuotationStatus}

    if value in allowed_statuses:
        return value

    return ""


@employee_permission_required(QuotationPermissionName.VIEW_QUOTATION.value)
def quotation_list(request: HttpRequest) -> HttpResponse:
    """Display searchable and filterable quotations."""

    query = request.GET.get("q", "").strip()
    selected_status = _validated_status(request.GET.get("status", ""))
    current_only = request.GET.get("current_only", "") == "1"

    quotations = search_quotations(
        query=query,
        status=selected_status,
        current_only=current_only,
    )

    paginator = Paginator(quotations, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "quotations/quotation_list.html",
        {
            "page": page,
            "query": query,
            "selected_status": selected_status,
            "current_only": current_only,
            "status_choices": QuotationStatus.choices,
        },
    )


@employee_permission_required(QuotationPermissionName.ADD_QUOTATION.value)
def quotation_create(request: HttpRequest) -> HttpResponse:
    """Create the first quotation revision for a job card."""

    if request.method == "POST":
        form = QuotationCreateForm(request.POST)

        if form.is_valid():
            job_card = cast(
                JobCard,
                form.cleaned_data["job_card"],
            )

            try:
                quotation = create_quotation(
                    actor=cast(User, request.user),
                    job_card_id=cast(int, job_card.pk),
                    command=CreateQuotationCommand(
                        currency=form.cleaned_data["currency"],
                        discount_percentage=form.cleaned_data["discount_percentage"],
                        tax_percentage=form.cleaned_data["tax_percentage"],
                        valid_until=form.cleaned_data["valid_until"],
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
                        f"Quotation "
                        f"{quotation.quotation_number} "
                        "was created successfully."
                    ),
                )

                return redirect(
                    "quotations:detail",
                    quotation_id=quotation.pk,
                )
    else:
        initial: dict[str, int] = {}
        job_value = request.GET.get("job", "")

        if job_value.isdecimal():
            initial["job_card"] = int(job_value)

        form = QuotationCreateForm(initial=initial)

    return render(
        request,
        "quotations/quotation_form.html",
        {
            "form": form,
        },
    )


@employee_permission_required(QuotationPermissionName.VIEW_QUOTATION.value)
def quotation_detail(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Display one quotation revision and its totals."""

    quotation = _get_quotation_or_404(quotation_id=quotation_id)
    totals = calculate_quotation_totals(quotation)

    return render(
        request,
        "quotations/quotation_detail.html",
        {
            "quotation": quotation,
            "totals": totals,
            "quotation_history": (
                get_quotation_history_for_job(job_card_id=quotation.job_card_id)
            ),
        },
    )


@employee_permission_required(QuotationPermissionName.CHANGE_QUOTATION.value)
def service_line_create(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Add a service snapshot line to a draft quotation."""

    quotation = _get_quotation_or_404(quotation_id=quotation_id)

    if request.method == "POST":
        form = ServiceLineCreateForm(request.POST)
    else:
        form = ServiceLineCreateForm()

    form.configure_for_quotation(quotation=quotation)

    if request.method == "POST" and form.is_valid():
        service = cast(
            Service,
            form.cleaned_data["service"],
        )

        try:
            add_service_line(
                actor=cast(User, request.user),
                quotation_id=quotation_id,
                command=AddServiceLineCommand(
                    service_id=cast(int, service.pk),
                    quantity=form.cleaned_data["quantity"],
                    description_override=form.cleaned_data["description_override"],
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
                "The service was added to the quotation.",
            )

            return redirect(
                "quotations:detail",
                quotation_id=quotation_id,
            )

    return render(
        request,
        "quotations/service_line_form.html",
        {
            "quotation": quotation,
            "form": form,
        },
    )


@employee_permission_required(QuotationPermissionName.CHANGE_QUOTATION.value)
def product_line_create(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Add a product snapshot line to a draft quotation."""

    quotation = _get_quotation_or_404(quotation_id=quotation_id)

    if request.method == "POST":
        form = ProductLineCreateForm(request.POST)
    else:
        form = ProductLineCreateForm()

    form.configure_for_quotation(quotation=quotation)

    if request.method == "POST" and form.is_valid():
        product = cast(
            Product,
            form.cleaned_data["product"],
        )

        try:
            add_product_line(
                actor=cast(User, request.user),
                quotation_id=quotation_id,
                command=AddProductLineCommand(
                    product_id=cast(int, product.pk),
                    quantity=form.cleaned_data["quantity"],
                    description_override=form.cleaned_data["description_override"],
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
                "The product was added to the quotation.",
            )

            return redirect(
                "quotations:detail",
                quotation_id=quotation_id,
            )

    return render(
        request,
        "quotations/product_line_form.html",
        {
            "quotation": quotation,
            "form": form,
        },
    )


@require_POST
@employee_permission_required(QuotationPermissionName.SUBMIT_QUOTATION.value)
def quotation_submit(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Submit a complete draft quotation to the customer."""

    try:
        quotation = submit_quotation(
            actor=cast(User, request.user),
            quotation_id=quotation_id,
        )
    except Quotation.DoesNotExist as exc:
        raise Http404("Quotation not found.") from exc
    except ValidationError as error:
        _add_validation_messages(
            request=request,
            error=error,
        )
    else:
        messages.success(
            request,
            (f"Quotation {quotation.quotation_number} was submitted to the customer."),
        )

    return redirect(
        "quotations:detail",
        quotation_id=quotation_id,
    )


@employee_permission_required(QuotationPermissionName.APPROVE_QUOTATION.value)
def quotation_approve(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Record customer approval of a submitted quotation."""

    quotation = _get_quotation_or_404(quotation_id=quotation_id)

    if request.method == "POST":
        form = CustomerDecisionForm(request.POST)

        if form.is_valid():
            try:
                approved_quotation = approve_quotation(
                    actor=cast(User, request.user),
                    quotation_id=quotation_id,
                    command=RecordCustomerDecisionCommand(
                        customer_name=form.cleaned_data["customer_name"],
                        method=CustomerDecisionMethod(form.cleaned_data["method"]),
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
                    (f"Quotation {approved_quotation.quotation_number} was approved."),
                )

                return redirect(
                    "quotations:detail",
                    quotation_id=quotation_id,
                )
    else:
        form = CustomerDecisionForm(
            initial={"customer_name": (quotation.job_card.customer_name_snapshot)}
        )

    return render(
        request,
        "quotations/decision_form.html",
        {
            "quotation": quotation,
            "form": form,
            "decision_action": "approve",
        },
    )


@employee_permission_required(QuotationPermissionName.REJECT_QUOTATION.value)
def quotation_reject(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Record customer rejection of a submitted quotation."""

    quotation = _get_quotation_or_404(quotation_id=quotation_id)

    if request.method == "POST":
        form = CustomerDecisionForm(request.POST)

        if form.is_valid():
            try:
                rejected_quotation = reject_quotation(
                    actor=cast(User, request.user),
                    quotation_id=quotation_id,
                    command=RecordCustomerDecisionCommand(
                        customer_name=form.cleaned_data["customer_name"],
                        method=CustomerDecisionMethod(form.cleaned_data["method"]),
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
                    (f"Quotation {rejected_quotation.quotation_number} was rejected."),
                )

                return redirect(
                    "quotations:detail",
                    quotation_id=quotation_id,
                )
    else:
        form = CustomerDecisionForm(
            initial={"customer_name": (quotation.job_card.customer_name_snapshot)}
        )

    return render(
        request,
        "quotations/decision_form.html",
        {
            "quotation": quotation,
            "form": form,
            "decision_action": "reject",
        },
    )


@require_POST
@employee_permission_required(QuotationPermissionName.REVISE_QUOTATION.value)
def quotation_revise(
    request: HttpRequest,
    quotation_id: int,
) -> HttpResponse:
    """Create a new draft revision from a current quotation."""

    try:
        revision = create_quotation_revision(
            actor=cast(User, request.user),
            quotation_id=quotation_id,
        )
    except Quotation.DoesNotExist as exc:
        raise Http404("Quotation not found.") from exc
    except ValidationError as error:
        _add_validation_messages(
            request=request,
            error=error,
        )

        return redirect(
            "quotations:detail",
            quotation_id=quotation_id,
        )

    messages.success(
        request,
        (f"Quotation revision {revision.quotation_number} was created."),
    )

    return redirect(
        "quotations:detail",
        quotation_id=revision.pk,
    )
