"""Application services for customer-management operations."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.customers.constants import (
    CustomerPermissionName,
    CustomerType,
)
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle


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


@dataclass(frozen=True, slots=True)
class UpdateCustomerCommand:
    """Contain validated changes to a customer record."""

    customer_type: CustomerType
    name: str
    phone_number: str
    email: str = ""
    address: str = ""
    notes: str = ""


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
def update_customer(
    *,
    actor: User,
    customer_id: int,
    command: UpdateCustomerCommand,
) -> Customer:
    """Update an existing customer record.

    Args:
        actor: Authenticated employee performing the update.
        customer_id: Primary key of the customer being updated.
        command: Validated replacement customer information.

    Returns:
        The updated customer.

    Raises:
        PermissionDenied: If the employee cannot update customers.
        Customer.DoesNotExist: If the customer does not exist.
        ValidationError: If the replacement information is invalid.
    """

    _require_permission(
        actor=actor,
        permission=CustomerPermissionName.CHANGE_CUSTOMER,
    )

    customer = Customer.objects.select_for_update().get(pk=customer_id)

    customer.customer_type = command.customer_type
    customer.name = command.name
    customer.phone_number = command.phone_number
    customer.email = command.email
    customer.address = command.address.strip()
    customer.notes = command.notes.strip()
    customer.updated_by = actor

    customer.full_clean()

    customer.save(
        update_fields=(
            "customer_type",
            "name",
            "phone_number",
            "normalized_phone_number",
            "email",
            "address",
            "notes",
            "updated_by",
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

    active_vehicle_count = (
        Vehicle.objects.select_for_update()
        .filter(
            current_owner_id=customer.pk,
            is_active=True,
        )
        .count()
    )

    if active_vehicle_count:
        raise ValidationError(
            {
                "is_active": (
                    "This customer cannot be deactivated while they "
                    f"own {active_vehicle_count} active vehicle(s). "
                    "Transfer or deactivate those vehicles first."
                )
            }
        )
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
