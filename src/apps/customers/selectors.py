"""Read-only database queries for customer information."""

from django.db.models import Q, QuerySet

from apps.customers.models import Customer
from apps.customers.normalization import (
    normalize_customer_name,
    normalize_email_address,
    normalize_phone_number,
    normalize_phone_search,
)


def search_customers(
    *,
    query: str = "",
    include_inactive: bool = False,
) -> QuerySet[Customer]:
    """Return customers matching a general search value.

    Customers can be found using their customer number, name, phone
    number, or email address.

    Args:
        query: Full or partial customer search value.
        include_inactive: Whether inactive customers should be included.

    Returns:
        A lazily evaluated customer queryset.
    """

    customers = Customer.objects.select_related(
        "created_by",
        "updated_by",
    )

    if not include_inactive:
        customers = customers.filter(is_active=True)

    search_value = query.strip()

    if not search_value:
        return customers

    phone_digits = normalize_phone_search(search_value)

    search_filter = (
        Q(customer_number__icontains=search_value)
        | Q(name__icontains=search_value)
        | Q(email__icontains=search_value)
    )

    if phone_digits:
        search_filter |= Q(normalized_phone_number__icontains=phone_digits)

    return customers.filter(search_filter).distinct()


def find_possible_customer_duplicates(
    *,
    name: str,
    phone_number: str,
    email: str = "",
    exclude_customer_id: int | None = None,
) -> QuerySet[Customer]:
    """Return existing records that may represent the same customer.

    Args:
        name: Proposed customer or company name.
        phone_number: Proposed customer phone number.
        email: Optional proposed email address.
        exclude_customer_id: Customer that should not be compared with
            itself during an update.

    Returns:
        Active and inactive possible duplicate customers.
    """

    normalized_name = normalize_customer_name(name)
    normalized_phone = normalize_phone_number(phone_number)
    normalized_email = normalize_email_address(email)

    duplicate_filter = Q(normalized_phone_number=normalized_phone) | Q(
        name__iexact=normalized_name
    )

    if normalized_email:
        duplicate_filter |= Q(email__iexact=normalized_email)

    customers = Customer.objects.filter(duplicate_filter)

    if exclude_customer_id is not None:
        customers = customers.exclude(pk=exclude_customer_id)

    return (
        customers.select_related(
            "created_by",
            "updated_by",
        )
        .order_by(
            "-is_active",
            "name",
            "customer_number",
        )
        .distinct()
    )


def get_customer_by_id(
    *,
    customer_id: int,
) -> Customer:
    """Return one customer with related employee information.

    Args:
        customer_id: Primary key of the requested customer.

    Returns:
        The matching customer.

    Raises:
        Customer.DoesNotExist: If the customer does not exist.
    """

    return Customer.objects.select_related(
        "created_by",
        "updated_by",
    ).get(pk=customer_id)
