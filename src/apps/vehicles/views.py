"""HTTP views for vehicle-management workflows."""

from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms import Form
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.vehicles.constants import (
    FuelType,
    VehicleCategory,
    VehiclePermissionName,
)
from apps.vehicles.forms import (
    VehicleOwnershipTransferForm,
    VehicleRegistrationForm,
)
from apps.vehicles.models import Vehicle
from apps.vehicles.selectors import (
    get_vehicle_by_id,
    search_vehicles,
)
from apps.vehicles.services.vehicles import (
    RegisterVehicleCommand,
    TransferVehicleOwnershipCommand,
    register_vehicle,
    transfer_vehicle_ownership,
)


def _get_vehicle_or_404(
    *,
    vehicle_id: int,
) -> Vehicle:
    """Return a vehicle or raise an HTTP 404 response."""

    try:
        return get_vehicle_by_id(vehicle_id=vehicle_id)
    except Vehicle.DoesNotExist as exc:
        raise Http404("Vehicle not found.") from exc


def _add_validation_error(
    *,
    form: Form,
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


def _parse_optional_integer(value: str | None) -> int | None:
    """Convert an optional query value to an integer."""

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


@employee_permission_required(VehiclePermissionName.VIEW_VEHICLE.value)
def vehicle_list(request: HttpRequest) -> HttpResponse:
    """Display searchable vehicle records."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"
    owner_id = _parse_optional_integer(request.GET.get("owner"))

    vehicles = search_vehicles(
        query=query,
        include_inactive=include_inactive,
        owner_id=owner_id,
    )

    owner_filter = None

    if owner_id is not None:
        owner_filter = Customer.objects.filter(pk=owner_id).first()

    paginator = Paginator(vehicles, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "vehicles/vehicle_list.html",
        {
            "page": page,
            "query": query,
            "include_inactive": include_inactive,
            "owner_filter": owner_filter,
        },
    )


@employee_permission_required(VehiclePermissionName.ADD_VEHICLE.value)
def vehicle_create(request: HttpRequest) -> HttpResponse:
    """Register a vehicle and its initial ownership record."""

    if request.method == "POST":
        form = VehicleRegistrationForm(request.POST)

        if form.is_valid():
            owner = cast(
                Customer,
                form.cleaned_data["current_owner"],
            )

            try:
                vehicle = register_vehicle(
                    actor=cast(User, request.user),
                    command=RegisterVehicleCommand(
                        owner_id=owner.pk,
                        registration_number=form.cleaned_data["registration_number"],
                        category=VehicleCategory(form.cleaned_data["category"]),
                        make=form.cleaned_data["make"],
                        model=form.cleaned_data["model"],
                        year=form.cleaned_data["year"],
                        color=form.cleaned_data["color"],
                        current_mileage=form.cleaned_data["current_mileage"],
                        fuel_type=(
                            FuelType(form.cleaned_data["fuel_type"])
                            if form.cleaned_data["fuel_type"]
                            else ""
                        ),
                        engine_number=form.cleaned_data["engine_number"],
                        chassis_number=form.cleaned_data["chassis_number"],
                        vin=form.cleaned_data["vin"],
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
                    (f"Vehicle {vehicle.vehicle_number} was registered successfully."),
                )

                return redirect(
                    "vehicles:detail",
                    vehicle_id=vehicle.pk,
                )
    else:
        initial: dict[str, object] = {}
        owner_id = _parse_optional_integer(request.GET.get("owner"))

        if (
            owner_id is not None
            and Customer.objects.filter(
                pk=owner_id,
                is_active=True,
            ).exists()
        ):
            initial["current_owner"] = owner_id

        form = VehicleRegistrationForm(initial=initial)

    return render(
        request,
        "vehicles/vehicle_form.html",
        {"form": form},
    )


@employee_permission_required(VehiclePermissionName.VIEW_VEHICLE.value)
def vehicle_detail(
    request: HttpRequest,
    vehicle_id: int,
) -> HttpResponse:
    """Display a vehicle and its ownership history."""

    vehicle = _get_vehicle_or_404(vehicle_id=vehicle_id)

    return render(
        request,
        "vehicles/vehicle_detail.html",
        {
            "vehicle": vehicle,
            "ownership_history": (vehicle.ownership_history.all()),
        },
    )


@employee_permission_required(VehiclePermissionName.TRANSFER_VEHICLE_OWNER.value)
def vehicle_transfer_owner(
    request: HttpRequest,
    vehicle_id: int,
) -> HttpResponse:
    """Transfer a vehicle to another active customer."""

    vehicle = _get_vehicle_or_404(vehicle_id=vehicle_id)

    if request.method == "POST":
        form = VehicleOwnershipTransferForm(
            request.POST,
            current_owner_id=vehicle.current_owner_id,
        )

        if form.is_valid():
            new_owner = cast(
                Customer,
                form.cleaned_data["new_owner"],
            )

            try:
                transfer_vehicle_ownership(
                    actor=cast(User, request.user),
                    vehicle_id=vehicle_id,
                    command=TransferVehicleOwnershipCommand(
                        new_owner_id=new_owner.pk,
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
                        f"Ownership of "
                        f"{vehicle.registration_number} "
                        "was transferred successfully."
                    ),
                )

                return redirect(
                    "vehicles:detail",
                    vehicle_id=vehicle_id,
                )
    else:
        form = VehicleOwnershipTransferForm(current_owner_id=vehicle.current_owner_id)

    return render(
        request,
        "vehicles/ownership_transfer_form.html",
        {
            "vehicle": vehicle,
            "form": form,
        },
    )
