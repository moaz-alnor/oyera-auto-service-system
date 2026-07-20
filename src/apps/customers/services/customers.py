"""Application services for customer-management operations."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.customers.constants import (
    CustomerPermissionName,
    CustomerType,
)
from apps.customers.models import Customer


@dataclass(frozen=True, slots=True)
class RegisterCustomerCommand:
    """Contain validated input for customer registration."""

    customer_type: CustomerType
    name: str
    phone_number: str
    email: str = ""
    address: str = ""
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: CustomerPermissionName,
) -> None:
    """Require an employee to hold a customer permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this customer action."
        )


@transaction.atomic
def register_customer(
    *,
    actor: User,
    command: RegisterCustomerCommand,
) -> Customer:
    """Register a customer and generate their customer number.

    Args:
        actor: Authenticated employee performing the registration.
        command: Customer information supplied by the employee.

    Returns:
        The newly registered customer.

    Raises:
        PermissionDenied: If the employee cannot register customers.
        ValidationError: If customer information is invalid.
    """

    _require_permission(
        actor=actor,
        permission=CustomerPermissionName.ADD_CUSTOMER,
    )

    customer = Customer(
        customer_type=command.customer_type,
        name=command.name,
        phone_number=command.phone_number,
        email=command.email,
        address=command.address.strip(),
        notes=command.notes.strip(),
        created_by=actor,
        updated_by=actor,
    )

    customer.full_clean()
    customer.save()

    if customer.pk is None:
        raise RuntimeError("Customer registration completed without a primary key.")

    customer.customer_number = f"CUS-{customer.pk:06d}"
    customer.save(
        update_fields=(
            "customer_number",
            "updated_at",
        )
    )

    return customer


@transaction.atomic
def deactivate_customer(
    *,
    actor: User,
    customer_id: int,
) -> Customer:
    """Deactivate a customer without deleting historical records."""

    _require_permission(
        actor=actor,
        permission=CustomerPermissionName.DEACTIVATE_CUSTOMER,
    )

    customer = Customer.objects.select_for_update().get(pk=customer_id)

    if not customer.is_active:
        return customer

    customer.is_active = False
    customer.updated_by = actor
    customer.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return customer


@transaction.atomic
def reactivate_customer(
    *,
    actor: User,
    customer_id: int,
) -> Customer:
    """Reactivate a previously inactive customer."""

    _require_permission(
        actor=actor,
        permission=CustomerPermissionName.REACTIVATE_CUSTOMER,
    )

    customer = Customer.objects.select_for_update().get(pk=customer_id)

    if customer.is_active:
        return customer

    customer.is_active = True
    customer.updated_by = actor
    customer.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return customer
