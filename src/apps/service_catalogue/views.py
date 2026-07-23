"""HTTP views for service-catalogue workflows."""

from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.service_catalogue.constants import (
    ServicePermissionName,
)
from apps.service_catalogue.forms import (
    ServiceCreateForm,
    ServicePriceChangeForm,
)
from apps.service_catalogue.models import Service
from apps.service_catalogue.selectors import (
    get_current_service_price,
    get_service_applicabilities,
    get_service_by_id,
    get_service_price_history,
    search_services,
)
from apps.service_catalogue.services.catalogue import (
    ChangeServicePriceCommand,
    CreateServiceCommand,
    change_service_price,
    create_service,
)
from apps.vehicles.constants import VehicleCategory


def _get_service_or_404(
    *,
    service_id: int,
) -> Service:
    """Return a catalogue service or raise HTTP 404."""

    try:
        return get_service_by_id(service_id=service_id)
    except Service.DoesNotExist as exc:
        raise Http404("Service not found.") from exc


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


def _get_vehicle_category(value: str) -> str:
    """Return a recognized vehicle category or an empty value."""

    valid_categories = {category.value for category in VehicleCategory}

    if value in valid_categories:
        return value

    return ""


@employee_permission_required(ServicePermissionName.VIEW_SERVICE.value)
def service_list(request: HttpRequest) -> HttpResponse:
    """Display searchable catalogue services."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"
    selected_category = _get_vehicle_category(request.GET.get("category", ""))

    services = search_services(
        query=query,
        include_inactive=include_inactive,
        vehicle_category=selected_category,
    )

    paginator = Paginator(services, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "service_catalogue/service_list.html",
        {
            "page": page,
            "query": query,
            "include_inactive": include_inactive,
            "selected_category": selected_category,
            "vehicle_categories": VehicleCategory.choices,
        },
    )


@employee_permission_required(ServicePermissionName.ADD_SERVICE.value)
def service_create(request: HttpRequest) -> HttpResponse:
    """Create a service with categories and an initial price."""

    if request.method == "POST":
        form = ServiceCreateForm(request.POST)

        if form.is_valid():
            categories = tuple(
                VehicleCategory(value)
                for value in form.cleaned_data["applicable_categories"]
            )

            try:
                service = create_service(
                    actor=cast(User, request.user),
                    command=CreateServiceCommand(
                        code=form.cleaned_data["code"],
                        name=form.cleaned_data["name"],
                        description=form.cleaned_data["description"],
                        estimated_duration_minutes=(
                            form.cleaned_data["estimated_duration_minutes"]
                        ),
                        applicable_categories=categories,
                        initial_price=form.cleaned_data["initial_price"],
                        currency=form.cleaned_data["currency"],
                        price_notes=form.cleaned_data["price_notes"],
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
                    (f"Service {service.code} was created successfully."),
                )

                return redirect(
                    "service_catalogue:detail",
                    service_id=service.pk,
                )
    else:
        form = ServiceCreateForm()

    return render(
        request,
        "service_catalogue/service_form.html",
        {"form": form},
    )


@employee_permission_required(ServicePermissionName.VIEW_SERVICE.value)
def service_detail(
    request: HttpRequest,
    service_id: int,
) -> HttpResponse:
    """Display a service and its complete price history."""

    service = _get_service_or_404(service_id=service_id)

    return render(
        request,
        "service_catalogue/service_detail.html",
        {
            "service": service,
            "applicabilities": (get_service_applicabilities(service_id=service_id)),
            "current_price": get_current_service_price(service_id=service_id),
            "price_history": get_service_price_history(service_id=service_id),
        },
    )


@employee_permission_required(ServicePermissionName.CHANGE_SERVICE_PRICE.value)
def service_change_price(
    request: HttpRequest,
    service_id: int,
) -> HttpResponse:
    """Close the current price and create a new price period."""

    service = _get_service_or_404(service_id=service_id)
    current_price = get_current_service_price(service_id=service_id)
    current_currency = current_price.currency if current_price is not None else "UGX"

    if request.method == "POST":
        form = ServicePriceChangeForm(
            request.POST,
            current_currency=current_currency,
        )

        if form.is_valid():
            try:
                new_price = change_service_price(
                    actor=cast(User, request.user),
                    service_id=service_id,
                    command=ChangeServicePriceCommand(
                        amount=form.cleaned_data["amount"],
                        currency=form.cleaned_data["currency"],
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
                        f"The current price for {service.code} "
                        f"is now {new_price.currency} "
                        f"{new_price.amount}."
                    ),
                )

                return redirect(
                    "service_catalogue:detail",
                    service_id=service_id,
                )
    else:
        form = ServicePriceChangeForm(current_currency=current_currency)

    return render(
        request,
        "service_catalogue/price_form.html",
        {
            "service": service,
            "current_price": current_price,
            "form": form,
        },
    )
