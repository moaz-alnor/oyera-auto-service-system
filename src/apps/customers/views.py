"""HTTP views for customer-management workflows."""

from typing import cast

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import employee_permission_required
from apps.accounts.models import User
from apps.customers.constants import (
    CustomerPermissionName,
    CustomerType,
)
from apps.customers.forms import CustomerRegistrationForm
from apps.customers.models import Customer
from apps.customers.selectors import (
    find_possible_customer_duplicates,
    get_customer_by_id,
    search_customers,
)
from apps.customers.services.customers import (
    RegisterCustomerCommand,
    register_customer,
)


@employee_permission_required(CustomerPermissionName.VIEW_CUSTOMER.value)
def customer_list(request: HttpRequest) -> HttpResponse:
    """Display searchable customer records."""

    query = request.GET.get("q", "").strip()
    include_inactive = request.GET.get("include_inactive") == "1"

    customers = search_customers(
        query=query,
        include_inactive=include_inactive,
    )

    paginator = Paginator(customers, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "customers/customer_list.html",
        {
            "page": page,
            "query": query,
            "include_inactive": include_inactive,
        },
    )


@employee_permission_required(CustomerPermissionName.ADD_CUSTOMER.value)
def customer_create(request: HttpRequest) -> HttpResponse:
    """Register a customer after reviewing possible duplicates."""

    duplicate_confirmation_required = False
    possible_duplicates = Customer.objects.none()

    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)

        if form.is_valid():
            possible_duplicates = find_possible_customer_duplicates(
                name=form.cleaned_data["name"],
                phone_number=form.cleaned_data["phone_number"],
                email=form.cleaned_data["email"],
            )

            duplicate_confirmed = form.cleaned_data["confirm_duplicate"]

            if possible_duplicates.exists() and not duplicate_confirmed:
                duplicate_confirmation_required = True
            else:
                actor = cast(User, request.user)

                customer = register_customer(
                    actor=actor,
                    command=RegisterCustomerCommand(
                        customer_type=CustomerType(form.cleaned_data["customer_type"]),
                        name=form.cleaned_data["name"],
                        phone_number=form.cleaned_data["phone_number"],
                        email=form.cleaned_data["email"],
                        address=form.cleaned_data["address"],
                        notes=form.cleaned_data["notes"],
                    ),
                )

                messages.success(
                    request,
                    (
                        f"Customer {customer.customer_number} "
                        "was registered successfully."
                    ),
                )

                return redirect(
                    "customers:detail",
                    customer_id=customer.pk,
                )
    else:
        form = CustomerRegistrationForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "possible_duplicates": possible_duplicates,
            "duplicate_confirmation_required": (duplicate_confirmation_required),
        },
    )


@employee_permission_required(CustomerPermissionName.VIEW_CUSTOMER.value)
def customer_detail(
    request: HttpRequest,
    customer_id: int,
) -> HttpResponse:
    """Display one customer record."""

    try:
        customer = get_customer_by_id(customer_id=customer_id)
    except Customer.DoesNotExist as exc:
        raise Http404("Customer not found.") from exc

    return render(
        request,
        "customers/customer_detail.html",
        {"customer": customer},
    )
