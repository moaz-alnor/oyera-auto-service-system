"""HTTP views for inventory and stock-ledger workflows."""

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

from apps.accounts.decorators import (
    employee_permission_required,
)
from apps.accounts.models import User
from apps.inventory.constants import (
    InventoryPermissionName,
    StockMovementType,
)
from apps.inventory.forms import (
    AdjustStockForm,
    InventoryItemForm,
    IssueStockForm,
    ReceiveStockForm,
    ReleaseReservationForm,
    ReserveStockForm,
    ReturnStockForm,
    StockLocationForm,
)
from apps.inventory.models import (
    InventoryItem,
    StockLocation,
    StockMovement,
    StockReservation,
)
from apps.inventory.selectors import (
    get_inventory_balance,
    get_inventory_item_by_id,
    get_inventory_item_movements,
    get_inventory_item_reservations,
    search_inventory_balances,
    search_stock_movements,
)
from apps.inventory.services.adjustments import (
    AdjustStockCommand,
    adjust_stock,
)
from apps.inventory.services.issues import (
    IssueStockCommand,
    ReturnStockCommand,
    issue_reserved_stock,
    return_issued_stock,
)
from apps.inventory.services.master_data import (
    CreateInventoryItemCommand,
    CreateStockLocationCommand,
    create_inventory_item,
    create_stock_location,
)
from apps.inventory.services.receipts import (
    ReceiveStockCommand,
    receive_stock,
)
from apps.inventory.services.reservations import (
    ReleaseReservationCommand,
    ReserveStockCommand,
    release_stock_reservation,
    reserve_stock,
)
from apps.product_catalogue.models import Product
from apps.workshop.models import WorkProductRequirement


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


def _parse_positive_integer(
    value: str,
) -> int | None:
    """Return a positive integer or no selected filter."""

    try:
        parsed_value = int(value)
    except ValueError:
        return None

    if parsed_value < 1:
        return None

    return parsed_value


def _get_inventory_item_or_404(
    *,
    inventory_item_id: int,
) -> InventoryItem:
    """Return one inventory item or raise HTTP 404."""

    try:
        return get_inventory_item_by_id(inventory_item_id=inventory_item_id)
    except InventoryItem.DoesNotExist as exc:
        raise Http404("Inventory item not found.") from exc


def _get_requirement_or_404(
    *,
    requirement_id: int,
) -> WorkProductRequirement:
    """Return one workshop product requirement or raise 404."""

    try:
        return WorkProductRequirement.objects.select_related(
            "work_order",
            "source_product_line",
            "source_product_line__product",
        ).get(pk=requirement_id)
    except WorkProductRequirement.DoesNotExist as exc:
        raise Http404("Workshop product requirement not found.") from exc


def _get_reservation_or_404(
    *,
    reservation_id: int,
) -> StockReservation:
    """Return one stock reservation or raise 404."""

    try:
        return StockReservation.objects.select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "work_product_requirement",
            "work_product_requirement__work_order",
        ).get(pk=reservation_id)
    except StockReservation.DoesNotExist as exc:
        raise Http404("Stock reservation not found.") from exc


def _get_issue_movement_or_404(
    *,
    movement_id: int,
) -> StockMovement:
    """Return one stock-issue movement or raise 404."""

    try:
        movement = StockMovement.objects.select_related(
            "inventory_item",
            "inventory_item__product",
            "inventory_item__location",
            "reservation",
            "reservation__work_product_requirement",
            "reservation__work_product_requirement__work_order",
        ).get(pk=movement_id)
    except StockMovement.DoesNotExist as exc:
        raise Http404("Stock issue not found.") from exc

    if movement.movement_type != StockMovementType.ISSUE:
        raise Http404("Stock issue not found.")

    return movement


@employee_permission_required(InventoryPermissionName.VIEW_INVENTORY_ITEM.value)
def inventory_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable inventory balances."""

    query = request.GET.get("q", "").strip()
    location_id = _parse_positive_integer(request.GET.get("location", ""))
    low_stock_only = request.GET.get("low_stock") == "1"

    balances = search_inventory_balances(
        query=query,
        location_id=location_id,
        low_stock_only=low_stock_only,
    )

    paginator = Paginator(
        balances,
        25,
    )
    page = paginator.get_page(request.GET.get("page"))

    locations = StockLocation.objects.filter(is_active=True).order_by(
        "name",
        "code",
    )

    return render(
        request,
        "inventory/inventory_list.html",
        {
            "page": page,
            "balances": page.object_list,
            "locations": locations,
            "query": query,
            "selected_location_id": location_id,
            "low_stock_only": low_stock_only,
        },
    )


@employee_permission_required(InventoryPermissionName.VIEW_INVENTORY_ITEM.value)
def inventory_detail(
    request: HttpRequest,
    inventory_item_id: int,
) -> HttpResponse:
    """Display one inventory item and its stock history."""

    inventory_item = _get_inventory_item_or_404(inventory_item_id=inventory_item_id)

    balance = get_inventory_balance(inventory_item_id=inventory_item.pk)

    reservations = get_inventory_item_reservations(inventory_item_id=inventory_item.pk)[
        :20
    ]

    movements = get_inventory_item_movements(inventory_item_id=inventory_item.pk)[:20]

    return render(
        request,
        "inventory/inventory_detail.html",
        {
            "inventory_item": inventory_item,
            "balance": balance,
            "reservations": reservations,
            "movements": movements,
        },
    )


@employee_permission_required(InventoryPermissionName.VIEW_MOVEMENT.value)
def movement_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable append-only stock movements."""

    query = request.GET.get("q", "").strip()
    movement_type = request.GET.get(
        "movement_type",
        "",
    ).strip()

    valid_movement_types = {choice.value for choice in StockMovementType}

    if movement_type not in valid_movement_types:
        movement_type = ""

    movements = search_stock_movements(
        query=query,
        movement_type=movement_type,
    )

    paginator = Paginator(
        movements,
        50,
    )
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/movement_list.html",
        {
            "page": page,
            "movements": page.object_list,
            "query": query,
            "selected_movement_type": movement_type,
            "movement_types": StockMovementType.choices,
        },
    )


@employee_permission_required(InventoryPermissionName.ADD_STOCK_LOCATION.value)
def stock_location_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create a physical inventory storage location."""

    if request.method == "POST":
        form = StockLocationForm(request.POST)

        if form.is_valid():
            try:
                location = create_stock_location(
                    actor=cast(User, request.user),
                    command=CreateStockLocationCommand(
                        code=form.cleaned_data["code"],
                        name=form.cleaned_data["name"],
                        description=(form.cleaned_data["description"]),
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
                    (f"Stock location {location.code} was created successfully."),
                )

                return redirect("inventory:list")
    else:
        form = StockLocationForm()

    return render(
        request,
        "inventory/location_form.html",
        {"form": form},
    )


@employee_permission_required(InventoryPermissionName.ADD_INVENTORY_ITEM.value)
def inventory_item_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create a product-location inventory record."""

    if request.method == "POST":
        form = InventoryItemForm(request.POST)

        if form.is_valid():
            product = cast(
                Product,
                form.cleaned_data["product"],
            )
            location = cast(
                StockLocation,
                form.cleaned_data["location"],
            )

            try:
                inventory_item = create_inventory_item(
                    actor=cast(User, request.user),
                    command=CreateInventoryItemCommand(
                        product_id=cast(int, product.pk),
                        location_id=cast(int, location.pk),
                        reorder_level=(form.cleaned_data["reorder_level"]),
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
                    (f"Inventory item for {product.sku} was created successfully."),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=inventory_item.pk,
                )
    else:
        form = InventoryItemForm()

    return render(
        request,
        "inventory/item_form.html",
        {"form": form},
    )


@employee_permission_required(InventoryPermissionName.RECEIVE_STOCK.value)
def stock_receive(
    request: HttpRequest,
    inventory_item_id: int,
) -> HttpResponse:
    """Receive physical stock into one inventory item."""

    inventory_item = _get_inventory_item_or_404(inventory_item_id=inventory_item_id)

    if request.method == "POST":
        form = ReceiveStockForm(request.POST)

        if form.is_valid():
            try:
                movement = receive_stock(
                    actor=cast(User, request.user),
                    command=ReceiveStockCommand(
                        inventory_item_id=inventory_item_id,
                        quantity=form.cleaned_data["quantity"],
                        unit_cost=form.cleaned_data["unit_cost"],
                        currency=form.cleaned_data["currency"],
                        external_reference=(form.cleaned_data["external_reference"]),
                        occurred_at=(form.cleaned_data["occurred_at"]),
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
                        f"Stock receipt "
                        f"{movement.movement_number} was "
                        f"recorded for "
                        f"{inventory_item.product.sku}."
                    ),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=inventory_item_id,
                )
    else:
        form = ReceiveStockForm()

    return render(
        request,
        "inventory/receipt_form.html",
        {
            "form": form,
            "inventory_item": inventory_item,
            "balance": get_inventory_balance(inventory_item_id=inventory_item_id),
        },
    )


@employee_permission_required(InventoryPermissionName.ADJUST_STOCK.value)
def stock_adjust(
    request: HttpRequest,
    inventory_item_id: int,
) -> HttpResponse:
    """Record an auditable inventory adjustment."""

    inventory_item = _get_inventory_item_or_404(inventory_item_id=inventory_item_id)

    if request.method == "POST":
        form = AdjustStockForm(request.POST)

        if form.is_valid():
            try:
                movement = adjust_stock(
                    actor=cast(User, request.user),
                    command=AdjustStockCommand(
                        inventory_item_id=inventory_item_id,
                        movement_type=(form.cleaned_data["movement_type"]),
                        quantity=form.cleaned_data["quantity"],
                        reason=form.cleaned_data["reason"],
                        external_reference=(form.cleaned_data["external_reference"]),
                        occurred_at=(form.cleaned_data["occurred_at"]),
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
                        f"Stock adjustment "
                        f"{movement.movement_number} was "
                        f"recorded for "
                        f"{inventory_item.product.sku}."
                    ),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=inventory_item_id,
                )
    else:
        form = AdjustStockForm()

    return render(
        request,
        "inventory/adjustment_form.html",
        {
            "form": form,
            "inventory_item": inventory_item,
            "balance": get_inventory_balance(inventory_item_id=inventory_item_id),
        },
    )


@employee_permission_required(InventoryPermissionName.RESERVE_STOCK.value)
def stock_reserve(
    request: HttpRequest,
    requirement_id: int,
) -> HttpResponse:
    """Reserve inventory for one workshop requirement."""

    requirement = _get_requirement_or_404(requirement_id=requirement_id)

    if request.method == "POST":
        form = ReserveStockForm(
            request.POST,
            requirement=requirement,
        )

        if form.is_valid():
            inventory_item = cast(
                InventoryItem,
                form.cleaned_data["inventory_item"],
            )

            try:
                reservation = reserve_stock(
                    actor=cast(User, request.user),
                    command=ReserveStockCommand(
                        inventory_item_id=cast(
                            int,
                            inventory_item.pk,
                        ),
                        work_product_requirement_id=(requirement.pk),
                        quantity=form.cleaned_data["quantity"],
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
                        f"{reservation.quantity_reserved} units "
                        f"of {inventory_item.product.sku} were "
                        "reserved successfully."
                    ),
                )

                return redirect(
                    "workshop:detail",
                    work_order_id=requirement.work_order_id,
                )
    else:
        form = ReserveStockForm(requirement=requirement)

    return render(
        request,
        "inventory/reservation_form.html",
        {
            "form": form,
            "requirement": requirement,
            "work_order": requirement.work_order,
        },
    )


@employee_permission_required(InventoryPermissionName.RELEASE_RESERVATION.value)
def reservation_release(
    request: HttpRequest,
    reservation_id: int,
) -> HttpResponse:
    """Release the remaining quantity from a reservation."""

    reservation = _get_reservation_or_404(reservation_id=reservation_id)

    if request.method == "POST":
        form = ReleaseReservationForm(request.POST)

        if form.is_valid():
            try:
                released_reservation = release_stock_reservation(
                    actor=cast(User, request.user),
                    command=ReleaseReservationCommand(
                        reservation_id=reservation.pk,
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
                    ("The remaining stock reservation was released successfully."),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=(released_reservation.inventory_item_id),
                )
    else:
        form = ReleaseReservationForm()

    return render(
        request,
        "inventory/reservation_release_form.html",
        {
            "form": form,
            "reservation": reservation,
        },
    )


@employee_permission_required(InventoryPermissionName.ISSUE_STOCK.value)
def stock_issue(
    request: HttpRequest,
    reservation_id: int,
) -> HttpResponse:
    """Issue reserved stock to a workshop work order."""

    reservation = _get_reservation_or_404(reservation_id=reservation_id)

    if request.method == "POST":
        form = IssueStockForm(
            request.POST,
            reservation=reservation,
        )

        if form.is_valid():
            try:
                movement = issue_reserved_stock(
                    actor=cast(User, request.user),
                    command=IssueStockCommand(
                        reservation_id=reservation.pk,
                        quantity=form.cleaned_data["quantity"],
                        occurred_at=(form.cleaned_data["occurred_at"]),
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
                        f"Stock issue "
                        f"{movement.movement_number} was "
                        "recorded successfully."
                    ),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=(reservation.inventory_item_id),
                )
    else:
        form = IssueStockForm(reservation=reservation)

    return render(
        request,
        "inventory/issue_form.html",
        {
            "form": form,
            "reservation": reservation,
            "balance": get_inventory_balance(
                inventory_item_id=(reservation.inventory_item_id)
            ),
        },
    )


@employee_permission_required(InventoryPermissionName.RETURN_STOCK.value)
def stock_return(
    request: HttpRequest,
    movement_id: int,
) -> HttpResponse:
    """Return stock from one original workshop issue."""

    source_movement = _get_issue_movement_or_404(movement_id=movement_id)

    if request.method == "POST":
        form = ReturnStockForm(
            request.POST,
            source_movement=source_movement,
        )

        if form.is_valid():
            try:
                returned_movement = return_issued_stock(
                    actor=cast(User, request.user),
                    command=ReturnStockCommand(
                        source_movement_id=(source_movement.pk),
                        quantity=form.cleaned_data["quantity"],
                        occurred_at=(form.cleaned_data["occurred_at"]),
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
                        f"Stock return "
                        f"{returned_movement.movement_number} "
                        "was recorded successfully."
                    ),
                )

                return redirect(
                    "inventory:detail",
                    inventory_item_id=(source_movement.inventory_item_id),
                )
    else:
        form = ReturnStockForm(source_movement=source_movement)

    return render(
        request,
        "inventory/return_form.html",
        {
            "form": form,
            "source_movement": source_movement,
            "reservation": source_movement.reservation,
        },
    )
