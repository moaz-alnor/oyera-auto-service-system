"""HTTP views for product-catalogue workflows."""

from typing import cast

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.forms.forms import BaseForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.product_catalogue.constants import (
    ProductPermissionName,
    ProductUnit,
)
from apps.product_catalogue.forms import (
    ProductCategoryCreateForm,
    ProductCreateForm,
    ProductPriceChangeForm,
)
from apps.product_catalogue.models import (
    Product,
    ProductCategory,
)
from apps.product_catalogue.selectors import (
    get_active_product_categories,
    get_current_product_price,
    get_product_by_id,
    get_product_price_history,
    search_product_categories,
    search_products,
)
from apps.product_catalogue.services.catalogue import (
    ChangeProductPriceCommand,
    CreateProductCategoryCommand,
    CreateProductCommand,
    change_product_price,
    create_product,
    create_product_category,
)


def _get_product_or_404(
    *,
    product_id: int,
) -> Product:
    """Return a product or raise HTTP 404."""

    try:
        return get_product_by_id(product_id=product_id)
    except Product.DoesNotExist as exc:
        raise Http404("Product not found.") from exc


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


def _parse_category_id(value: str) -> int | None:
    """Return a positive category ID or no filter."""

    try:
        category_id = int(value)
    except ValueError:
        return None

    if category_id < 1:
        return None

    return category_id


@employee_permission_required(ProductPermissionName.VIEW_PRODUCT_CATEGORY.value)
def product_category_list(
    request: HttpRequest,
) -> HttpResponse:
    """Display searchable product categories."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"

    categories = search_product_categories(
        query=query,
        include_inactive=include_inactive,
    )

    return render(
        request,
        "product_catalogue/category_list.html",
        {
            "categories": categories,
            "query": query,
            "include_inactive": include_inactive,
        },
    )


@employee_permission_required(ProductPermissionName.ADD_PRODUCT_CATEGORY.value)
def product_category_create(
    request: HttpRequest,
) -> HttpResponse:
    """Create a reusable product category."""

    if request.method == "POST":
        form = ProductCategoryCreateForm(request.POST)

        if form.is_valid():
            try:
                category = create_product_category(
                    actor=cast(User, request.user),
                    command=CreateProductCategoryCommand(
                        code=form.cleaned_data["code"],
                        name=form.cleaned_data["name"],
                        description=form.cleaned_data["description"],
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
                    (f"Product category {category.code} was created successfully."),
                )

                return redirect("product_catalogue:category_list")
    else:
        form = ProductCategoryCreateForm()

    return render(
        request,
        "product_catalogue/category_form.html",
        {"form": form},
    )


@employee_permission_required(ProductPermissionName.VIEW_PRODUCT.value)
def product_list(request: HttpRequest) -> HttpResponse:
    """Display searchable catalogue products."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"
    selected_category = request.GET.get(
        "category",
        "",
    )
    category_id = _parse_category_id(selected_category)

    products = search_products(
        query=query,
        category_id=category_id,
        include_inactive=include_inactive,
    )

    paginator = Paginator(products, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "product_catalogue/product_list.html",
        {
            "page": page,
            "query": query,
            "include_inactive": include_inactive,
            "selected_category": selected_category,
            "categories": get_active_product_categories(),
        },
    )


@employee_permission_required(ProductPermissionName.ADD_PRODUCT.value)
def product_create(request: HttpRequest) -> HttpResponse:
    """Create a product with its initial selling price."""

    if request.method == "POST":
        form = ProductCreateForm(request.POST)

        if form.is_valid():
            category = cast(
                ProductCategory,
                form.cleaned_data["category"],
            )

            category_id = cast(int, category.pk)

            try:
                product = create_product(
                    actor=cast(User, request.user),
                    command=CreateProductCommand(
                        category_id=category_id,
                        sku=form.cleaned_data["sku"],
                        name=form.cleaned_data["name"],
                        unit=ProductUnit(form.cleaned_data["unit"]),
                        initial_price=form.cleaned_data["initial_price"],
                        manufacturer=form.cleaned_data["manufacturer"],
                        manufacturer_part_number=(
                            form.cleaned_data["manufacturer_part_number"]
                        ),
                        description=form.cleaned_data["description"],
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
                    (f"Product {product.sku} was created successfully."),
                )

                return redirect(
                    "product_catalogue:detail",
                    product_id=product.pk,
                )
    else:
        form = ProductCreateForm()

    return render(
        request,
        "product_catalogue/product_form.html",
        {"form": form},
    )


@employee_permission_required(ProductPermissionName.VIEW_PRODUCT.value)
def product_detail(
    request: HttpRequest,
    product_id: int,
) -> HttpResponse:
    """Display a product and its complete price history."""

    product = _get_product_or_404(product_id=product_id)

    return render(
        request,
        "product_catalogue/product_detail.html",
        {
            "product": product,
            "current_price": get_current_product_price(product_id=product_id),
            "price_history": get_product_price_history(product_id=product_id),
        },
    )


@employee_permission_required(ProductPermissionName.CHANGE_PRODUCT_PRICE.value)
def product_change_price(
    request: HttpRequest,
    product_id: int,
) -> HttpResponse:
    """Close the current price and create a new period."""

    product = _get_product_or_404(product_id=product_id)
    current_price = get_current_product_price(product_id=product_id)
    current_currency = current_price.currency if current_price is not None else "UGX"

    if request.method == "POST":
        form = ProductPriceChangeForm(
            request.POST,
            current_currency=current_currency,
        )

        if form.is_valid():
            try:
                new_price = change_product_price(
                    actor=cast(User, request.user),
                    product_id=product_id,
                    command=ChangeProductPriceCommand(
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
                        f"The current price for {product.sku} "
                        f"is now {new_price.currency} "
                        f"{new_price.amount}."
                    ),
                )

                return redirect(
                    "product_catalogue:detail",
                    product_id=product_id,
                )
    else:
        form = ProductPriceChangeForm(current_currency=current_currency)

    return render(
        request,
        "product_catalogue/price_form.html",
        {
            "product": product,
            "current_price": current_price,
            "form": form,
        },
    )
